# test_auth.py
import httpx
import json
from datetime import datetime
import asyncio

BASE_URL = "http://localhost:8000"

TEST_USER = {
    "email": f"test_{int(datetime.now().timestamp())}@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
}

async def test_health():
    """Test health endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print("✅ Health Check:", response.json())
        return response.status_code == 200

async def test_register():
    """Test user registration"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json=TEST_USER
        )
        if response.status_code == 200:
            print("✅ Registration successful!")
            print(f"   User: {TEST_USER['email']}")
            return dict(response.cookies)
        else:
            print(f"❌ Registration failed: {response.text}")
            return None

async def test_login():
    """Test user login"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        if response.status_code == 200:
            print("✅ Login successful!")
            return dict(response.cookies)
        else:
            print(f"❌ Login failed: {response.text}")
            return None

async def test_get_user(cookies):
    """Test getting current user"""
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get(f"{BASE_URL}/auth/me")
        if response.status_code == 200:
            user_data = response.json()
            print("✅ Get user successful!")
            print(f"   Email: {user_data['email']}")
            print(f"   Name: {user_data['name']}")
            print(f"   Role: {user_data['role']}")
        else:
            print(f"❌ Get user failed: {response.text}")

async def test_logout(cookies):
    """Test logout"""
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.post(f"{BASE_URL}/auth/logout")
        if response.status_code == 200:
            print("✅ Logout successful!")
        else:
            print(f"❌ Logout failed: {response.text}")

async def run_all_tests():
    """Run all authentication tests"""
    print("\n" + "="*50)
    print("🚀 Starting Authentication Tests")
    print("="*50 + "\n")
    
    # Test health
    if not await test_health():
        print("❌ Server is not running! Start it with: uvicorn app.main:app --reload")
        return
    
    print("\n" + "-"*50 + "\n")
    
    # Test registration
    cookies = await test_register()
    
    if not cookies:
        print("Trying login with existing user...")
        cookies = await test_login()
    
    if not cookies:
        print("\n❌ Authentication failed! Check your Cognito configuration.")
        return
    
    print("\n" + "-"*50 + "\n")
    
    # Test get user
    await test_get_user(cookies)
    
    print("\n" + "-"*50 + "\n")
    
    # Test logout
    await test_logout(cookies)
    
    print("\n" + "="*50)
    print("✅ All tests completed!")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_all_tests())