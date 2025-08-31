import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import traceback

load_dotenv('.env.production')

async def test():
    try:
        url = os.getenv('DATABASE_URL')
        print(f"Connecting to: {url.replace(os.getenv('DB_PASSWORD'), '****')}")
        
        # Try connection with timeout
        conn = await asyncio.wait_for(
            asyncpg.connect(url, command_timeout=10), 
            timeout=15
        )
        
        version = await conn.fetchval('SELECT version()')
        await conn.close()
        print(f"✅ Connection successful!")
        print(f"PostgreSQL: {version.split(',')[0]}")
        return True
        
    except asyncio.TimeoutError:
        print(f"❌ Connection timeout - likely security group issue")
        print("Fix: Add your IP to security group or make DB publicly accessible")
        return False
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Suggest fixes based on error type
        if "timeout" in str(e).lower():
            print("Fix: Add your IP to the database security group")
        elif "auth" in str(e).lower():
            print("Fix: Check username/password")
        elif "ssl" in str(e).lower():
            print("Fix: Try without SSL requirement")
            
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    exit(0 if success else 1)
