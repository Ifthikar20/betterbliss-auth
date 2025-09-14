# add_video_columns.py
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('.env.production')

async def add_video_columns():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    try:
        print("Adding video streaming columns to content table...")
        
        # Add all the video streaming columns
        video_columns = [
            "ALTER TABLE content ADD COLUMN IF NOT EXISTS s3_key_video_720p TEXT",
            "ALTER TABLE content ADD COLUMN IF NOT EXISTS s3_key_video_1080p TEXT",
            "ALTER TABLE content ADD COLUMN IF NOT EXISTS s3_key_thumbnail TEXT",
            "ALTER TABLE content ADD COLUMN IF NOT EXISTS s3_key_poster TEXT",
            "ALTER TABLE content ADD COLUMN IF NOT EXISTS video_duration_seconds INTEGER",
            "ALTER TABLE content ADD COLUMN IF NOT EXISTS video_format VARCHAR(10) DEFAULT 'mp4'",
            "ALTER TABLE content ADD COLUMN IF NOT EXISTS has_video BOOLEAN DEFAULT false"
        ]
        
        for column_sql in video_columns:
            await conn.execute(column_sql)
            print(f"  ✓ Added column")
        
        # Create video analytics table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS video_analytics (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                content_id UUID REFERENCES content(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                session_id VARCHAR(100) NOT NULL,
                event_type VARCHAR(20) NOT NULL,
                timestamp_seconds DECIMAL(10,2),
                watch_duration_seconds INTEGER,
                quality_level VARCHAR(10),
                device_type VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add video streaming indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_content_has_video ON content(has_video) WHERE has_video = true",
            "CREATE INDEX IF NOT EXISTS idx_video_analytics_content ON video_analytics(content_id, created_at)"
        ]
        
        for index_sql in indexes:
            await conn.execute(index_sql)
        
        # Update a few sample content items with video data for testing
        sample_content = [
            ("understanding-anxiety-clinical", "videos/720p/anxiety-720p.mp4", "thumbnails/anxiety-thumb.jpg"),
            ("basic-mindfulness-meditation", "videos/720p/mindfulness-720p.mp4", "thumbnails/mindfulness-thumb.jpg")
        ]
        
        for slug, video_key, thumb_key in sample_content:
            result = await conn.execute('''
                UPDATE content 
                SET s3_key_video_720p = $1, 
                    s3_key_thumbnail = $2, 
                    has_video = true,
                    video_duration_seconds = duration_seconds
                WHERE slug = $3
            ''', video_key, thumb_key, slug)
            
            if result == "UPDATE 1":
                print(f"  ✓ Updated {slug} with video streaming data")
        
        print("\n✅ Video streaming columns and sample data added successfully!")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_video_columns())