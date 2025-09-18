# add_newsletter_tables.py
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('.env.production')

async def add_newsletter_tables():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    try:
        print("Adding newsletter tables...")
        
        # Newsletter subscribers table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(100),
                source VARCHAR(50) NOT NULL DEFAULT 'website',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                metadata JSONB,
                client_ip INET,
                request_id VARCHAR(100),
                confirmed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Newsletter subscribers table created")
        
        # Rate limiting table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS rate_limits (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                identifier VARCHAR(255) NOT NULL,
                endpoint VARCHAR(100) NOT NULL,
                requests_count INTEGER DEFAULT 1,
                window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Rate limits table created")
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_newsletter_email ON newsletter_subscribers(email)",
            "CREATE INDEX IF NOT EXISTS idx_newsletter_status ON newsletter_subscribers(status)",
            "CREATE INDEX IF NOT EXISTS idx_newsletter_created ON newsletter_subscribers(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_rate_limits_lookup ON rate_limits(identifier, endpoint, window_start)",
            "CREATE INDEX IF NOT EXISTS idx_rate_limits_cleanup ON rate_limits(window_start)"
        ]
        
        for index_sql in indexes:
            await conn.execute(index_sql)
        print("✓ All indexes created")
        
        print("\n✅ Newsletter tables and indexes added successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_newsletter_tables())