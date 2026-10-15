import 'dart:convert';
import 'package:http/http.dart' as http;

class ShopifyService {
  final String shopDomain;
  final String storefrontAccessToken;
  final String apiVersion;

  ShopifyService({
    this.shopDomain = 'lauburu-eco.myshopify.com', 
    this.storefrontAccessToken = 'REPLACE_WITH_STOREFRONT_TOKEN',
    this.apiVersion = '2024-01',
  });

  String get endpoint => 'https://$shopDomain/api/$apiVersion/graphql.json';

  Future<String?> login(String email, String password) async {
    const String mutation = r'''
      mutation customerAccessTokenCreate($input: CustomerAccessTokenCreateInput!) {
        customerAccessTokenCreate(input: $input) {
          customerAccessToken {
            accessToken
          }
          customerUserErrors {
            message
          }
        }
      }
    ''';

    final response = await http.post(
      Uri.parse(endpoint),
      headers: {
        'Content-Type': 'application/json',
        'X-Shopify-Storefront-Access-Token': storefrontAccessToken,
      },
      body: jsonEncode({
        'query': mutation,
        'variables': {
          'input': {
            'email': email,
            'password': password,
          }
        }
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final errors = data['data']?['customerAccessTokenCreate']?['customerUserErrors'] as List?;
      if (errors != null && errors.isNotEmpty) {
        throw Exception(errors.first['message']);
      }
      return data['data']?['customerAccessTokenCreate']?['customerAccessToken']?['accessToken'];
    } else {
      throw Exception('Failed to connect to Shopify');
    }
  }

  Future<List<String>> getCustomerTags(String accessToken) async {
    const String query = r'''
      query getCustomerTags($customerAccessToken: String!) {
        customer(customerAccessToken: $customerAccessToken) {
          tags
        }
      }
    ''';

    final response = await http.post(
      Uri.parse(endpoint),
      headers: {
        'Content-Type': 'application/json',
        'X-Shopify-Storefront-Access-Token': storefrontAccessToken,
      },
      body: jsonEncode({
        'query': query,
        'variables': {
          'customerAccessToken': accessToken,
        }
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final customer = data['data']?['customer'];
      if (customer == null) {
        throw Exception('Invalid access token');
      }
      final tags = customer['tags'] as List?;
      return tags?.map((e) => e.toString()).toList() ?? [];
    } else {
      throw Exception('Failed to fetch customer data');
    }
  }
}
