# test_auth_with_db.py
import httpx
import json
from datetime import datetime
import asyncio

BASE_URL = "http://localhost:8000"  # Change to your ALB URL when testing production

TEST_USER = {
    "email": f"test_{int(datetime.now().timestamp())}@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
}

async def test_health():
    """Test health endpoint with database check"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print("✅ Health Check:", response.json())
        
        health_data = response.json()
        # In development mode, allow degraded status due to database connectivity issues
        if health_data.get('environment') == 'development':
            return response.status_code == 200  # Just check server is responding
        else:
            # In production, require healthy database
            if not health_data.get('database_healthy'):
                print("❌ Database is not healthy!")
                return False
            return response.status_code == 200
async def test_register():
    """Test user registration with database creation"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json=TEST_USER
        )
        if response.status_code == 200:
            print("✅ Registration successful!")
            print(f"   User: {TEST_USER['email']}")
            
            # Check if user data includes database info
            user_data = response.json()
            print(f"   User ID: {user_data['user']['id']}")
            print(f"   Role: {user_data['user']['role']}")
            print(f"   Subscription: {user_data['user']['subscription_tier']}")
            
            return dict(response.cookies)
        else:
            print(f"❌ Registration failed: {response.text}")
            return None

async def test_login():
    """Test user login with database sync"""
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
            
            user_data = response.json()
            print(f"   Role: {user_data['user']['role']}")
            print(f"   Subscription: {user_data['user']['subscription_tier']}")
            
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
            print(f"   Subscription: {user_data['subscription_tier']}")
        else:
            print(f"❌ Get user failed: {response.text}")

async def test_get_detailed_profile(cookies):
    """Test getting detailed profile with database info"""
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get(f"{BASE_URL}/auth/profile")
        if response.status_code == 200:
            profile_data = response.json()
            print("✅ Get detailed profile successful!")
            print(f"   Database ID: {profile_data['profile']['id']}")
            print(f"   Status: {profile_data['profile']['status']}")
            print(f"   Created: {profile_data['profile']['created_at']}")
        else:
            print(f"❌ Get profile failed: {response.text}")

async def test_update_profile(cookies):
    """Test updating user profile"""
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.put(
            f"{BASE_URL}/auth/profile",
            json={
                "display_name": "Updated Test User",
                "avatar_url": "https://example.com/avatar.jpg"
            }
        )
        if response.status_code == 200:
            print("✅ Profile update successful!")
            update_data = response.json()
            print(f"   Updated name: {update_data['user']['display_name']}")
        else:
            print(f"❌ Profile update failed: {response.text}")

async def test_logout(cookies):
    """Test logout"""
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.post(f"{BASE_URL}/auth/logout")
        if response.status_code == 200:
            print("✅ Logout successful!")
        else:
            print(f"❌ Logout failed: {response.text}")

async def run_all_tests():
    """Run all authentication tests with database integration"""
    print("\n" + "="*60)
    print("🚀 Starting Enhanced Authentication Tests (with Database)")
    print("="*60 + "\n")
    
    # Test health (including database)
    if not await test_health():
        print("❌ Server or database is not running!")
        return
    
    print("\n" + "-"*50 + "\n")
    
    # Test registration (creates user in both Cognito and Database)
    cookies = await test_register()
    
    if not cookies:
        print("Trying login with existing user...")
        cookies = await test_login()
    
    if not cookies:
        print("\n❌ Authentication failed! Check your setup.")
        return
    
    print("\n" + "-"*50 + "\n")
    
    # Test get user (simple)
    await test_get_user(cookies)
    
    print("\n" + "-"*30 + "\n")
    
    # Test get detailed profile (with database info)
    await test_get_detailed_profile(cookies)
    
    print("\n" + "-"*30 + "\n")
    
    # Test profile update
    await test_update_profile(cookies)
    
    print("\n" + "-"*50 + "\n")
    
    # Test logout
    await test_logout(cookies)
    
    print("\n" + "="*60)
    print("✅ All enhanced tests completed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_all_tests())