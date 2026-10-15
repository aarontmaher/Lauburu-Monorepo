import asyncio
import httpx

async def test_integration():
    print("Testing Lens Scripting Automation API...")
    async with httpx.AsyncClient() as client:
        res = await client.post("http://127.0.0.1:4006/api/automation/run", json={"script": "test_gboard_macro"})
        print("API Response:", res.status_code, res.json())
        assert res.status_code == 200

if __name__ == "__main__":
    asyncio.run(test_integration())
