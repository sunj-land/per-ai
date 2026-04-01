import httpx
import asyncio

async def test_redirect():
    async with httpx.AsyncClient() as client:
        # We test the raw backend endpoint without auth to see the redirect
        # If redirect happens, it will return 307
        response = await client.get("http://localhost:8000/api/v1/plans", follow_redirects=False)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 307:
            print(f"Redirect Location: {response.headers.get('location')}")

asyncio.run(test_redirect())
