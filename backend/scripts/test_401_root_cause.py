import httpx
import asyncio

async def test_api_redirect_auth_drop():
    url_without_slash = "http://localhost:8000/api/v1/plans"
    
    print(f"Testing URL: {url_without_slash}")
    print("-" * 50)
    
    async with httpx.AsyncClient() as client:
        # Step 1: Simulate the request without following redirects to see if 307 occurs
        response = await client.get(url_without_slash, follow_redirects=False)
        print(f"[Direct Request] Status Code: {response.status_code}")
        
        if response.status_code == 307:
            redirect_url = response.headers.get('location')
            print(f"[Redirect Triggered] FastAPI is redirecting to: {redirect_url}")
            print(f"   => The port changes from frontend (3000) to backend ({redirect_url}), triggering Cross-Origin.")
            print(f"   => Browser drops the 'Authorization' header when following this cross-origin redirect.")
        elif response.status_code == 401:
            print("[No Redirect] Endpoint reached directly, but auth is missing (Expected behavior).")
            print("   => The issue is FIXED. The 307 redirect no longer occurs.")
        else:
            print(f"Unexpected status: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_api_redirect_auth_drop())
