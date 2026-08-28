"""
Unit tests for ShopifyClient transport, retry backoff, leaky-bucket rate limiting, and error handling.
"""

import httpx
import pytest

from shopify_headless.client import ShopifyClient
from shopify_headless.config import ShopifyConfig
from shopify_headless.errors import (
    ShopifyAuthError,
    ShopifyGraphQLError,
    ShopifyRateLimitError,
    ShopifyUserError,
)
from .conftest import MockGraphQLTransport


@pytest.mark.asyncio
async def test_storefront_execution_success(mock_config):
    resp_data = {"data": {"shop": {"name": "Lauburu Mesh Store"}}}
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json=resp_data)])
    client = ShopifyClient(config=mock_config, transport=transport)

    result = await client.execute_storefront("query { shop { name } }")
    assert result == {"shop": {"name": "Lauburu Mesh Store"}}
    assert len(transport.requests) == 1
    req = transport.requests[0]
    assert req.headers.get("X-Shopify-Storefront-Access-Token") == mock_config.storefront_access_token
    assert str(req.url) == mock_config.storefront_endpoint


@pytest.mark.asyncio
async def test_admin_execution_with_cost_extensions(mock_config):
    resp_data = {
        "data": {"shop": {"id": "gid://shopify/Shop/1"}},
        "extensions": {
            "cost": {
                "requestedQueryCost": 10,
                "actualQueryCost": 10,
                "throttleStatus": {
                    "maximumAvailable": 1000.0,
                    "currentlyAvailable": 990.0,
                    "restoreRate": 50.0,
                },
            }
        },
    }
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json=resp_data)])
    client = ShopifyClient(config=mock_config, transport=transport)

    result = await client.execute_admin("query { shop { id } }")
    assert result == {"shop": {"id": "gid://shopify/Shop/1"}}
    assert client._available_cost == 990.0
    assert client._restore_rate == 50.0
    assert len(transport.requests) == 1
    assert transport.requests[0].headers.get("X-Shopify-Access-Token") == mock_config.admin_access_token


@pytest.mark.asyncio
async def test_customer_account_execution(mock_config):
    resp_data = {"data": {"customer": {"id": "gid://shopify/Customer/123"}}}
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json=resp_data)])
    client = ShopifyClient(config=mock_config, transport=transport)

    result = await client.execute_customer_account("query { customer { id } }", customer_token="cust_token_abc")
    assert result == {"customer": {"id": "gid://shopify/Customer/123"}}
    assert transport.requests[0].headers.get("Authorization") == "Bearer cust_token_abc"


def test_dev_token_recognition(mock_config):
    client = ShopifyClient(config=mock_config)
    assert client.is_dev_token("tok_dev_123456") is True
    assert client.is_dev_token("shpat_dev_999") is True
    assert client.is_dev_token("dev_aaron_tester") is True
    assert client.is_dev_token("test_token_offline") is True
    assert client.is_dev_token("real_prod_token_live_123456789") is False
    assert client.is_dev_token("") is False
    assert client.is_dev_token(None) is False


@pytest.mark.asyncio
async def test_http_429_retry_and_success(mock_config):
    rate_limit_resp = httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "Too Many Requests"})
    success_resp = httpx.Response(200, json={"data": {"status": "ok"}})

    transport = MockGraphQLTransport(responses=[rate_limit_resp, success_resp])
    client = ShopifyClient(config=mock_config, transport=transport)

    result = await client.execute_storefront("query { status }")
    assert result == {"status": "ok"}
    assert len(transport.requests) == 2


@pytest.mark.asyncio
async def test_http_429_exhaustion_raises_rate_limit_error(mock_config):
    rate_limit_resp1 = httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "Throttled"})
    rate_limit_resp2 = httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "Throttled"})
    rate_limit_resp3 = httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "Throttled"})

    transport = MockGraphQLTransport(responses=[rate_limit_resp1, rate_limit_resp2, rate_limit_resp3])
    client = ShopifyClient(config=mock_config, transport=transport)

    with pytest.raises(ShopifyRateLimitError) as exc_info:
        await client.execute_storefront("query { status }")
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_graphql_throttled_error_retry(mock_config):
    throttled_graphql_resp = httpx.Response(
        200,
        json={
            "errors": [
                {
                    "message": "Throttled",
                    "extensions": {"code": "THROTTLED"},
                }
            ]
        },
    )
    success_resp = httpx.Response(200, json={"data": {"success": True}})

    transport = MockGraphQLTransport(responses=[throttled_graphql_resp, success_resp])
    client = ShopifyClient(config=mock_config, transport=transport)

    result = await client.execute_storefront("query { test }")
    assert result == {"success": True}
    assert len(transport.requests) == 2


@pytest.mark.asyncio
async def test_graphql_top_level_error_raises_graphql_error(mock_config):
    error_resp = httpx.Response(
        200,
        json={
            "errors": [
                {
                    "message": "Field 'invalidField' does not exist on type 'Query'",
                    "locations": [{"line": 1, "column": 9}],
                    "extensions": {"code": "GRAPHQL_VALIDATION_FAILED"},
                }
            ]
        },
    )
    transport = MockGraphQLTransport(responses=[error_resp])
    client = ShopifyClient(config=mock_config, transport=transport)

    with pytest.raises(ShopifyGraphQLError) as exc_info:
        await client.execute_storefront("query { invalidField }")
    assert "Field 'invalidField' does not exist" in str(exc_info.value)
    assert exc_info.value.errors[0]["extensions"]["code"] == "GRAPHQL_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_auth_error_401_raises_shopify_auth_error(mock_config):
    unauth_resp = httpx.Response(401, text="Invalid API key or access token")
    transport = MockGraphQLTransport(responses=[unauth_resp])
    client = ShopifyClient(config=mock_config, transport=transport)

    with pytest.raises(ShopifyAuthError) as exc_info:
        await client.execute_admin("query { test }")
    assert exc_info.value.code == "401"


def test_validate_user_errors_raises_user_error():
    payload = {
        "cartCreate": {
            "cart": None,
            "userErrors": [
                {
                    "field": ["input", "lines", "0", "sellingPlanId"],
                    "message": "Selling plan does not exist",
                    "code": "INVALID",
                }
            ],
        }
    }
    with pytest.raises(ShopifyUserError) as exc_info:
        ShopifyClient.validate_user_errors(payload, "cartCreate")
    assert exc_info.value.message == "Selling plan does not exist"
    assert exc_info.value.code == "INVALID"
    assert exc_info.value.field == "input.lines.0.sellingPlanId"
