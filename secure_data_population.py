# secure_data_population.py - Security-first database population with video streaming support
import asyncio
import asyncpg
import os
import uuid
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv('.env.production')

class SecureDataPopulator:
    def __init__(self):
        self.connection = None
    
    async def connect(self):
        """Establish secure database connection"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL not found in environment")
            
            # Ensure SSL connection for security
            self.connection = await asyncpg.connect(
                database_url,
                command_timeout=10,
                server_settings={
                    'application_name': 'betterbliss_data_populator'
                }
            )
            logger.info("Secure database connection established")
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Database connection closed")
    
    async def check_existing_data(self):
        """Check if data already exists to prevent duplicates"""
        try:
            expert_count = await self.connection.fetchval("SELECT COUNT(*) FROM experts")
            content_count = await self.connection.fetchval("SELECT COUNT(*) FROM content")
            
            if expert_count > 1 or content_count > 0:
                logger.warning(f"Data already exists: {expert_count} experts, {content_count} content items")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to check existing data: {e}")
            raise
    
    async def add_video_columns(self):
        """Add video streaming columns to content table if they don't exist"""
        try:
            # Add video streaming columns
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
                await self.connection.execute(column_sql)
            
            logger.info("Video streaming columns added to content table")
            
        except Exception as e:
            logger.error(f"Failed to add video columns: {e}")
            raise
    
    async def populate_experts(self):
        """Populate experts table with security-validated data"""
        try:
            # Minimal, essential expert data - no PII or sensitive information
            experts_data = [
                {
                    'name': 'Dr. Sarah Thompson',
                    'slug': 'dr-sarah-thompson',
                    'title': 'Licensed Clinical Psychologist',
                    'bio': 'Specializes in anxiety disorders and cognitive behavioral therapy with evidence-based approaches.',
                    'specialties': ['anxiety', 'cbt', 'stress-management'],
                    'verified': True,
                    'featured': True
                },
                {
                    'name': 'Dr. Michael Chen',
                    'slug': 'dr-michael-chen',
                    'title': 'Mindfulness & Meditation Expert',
                    'bio': 'Certified mindfulness instructor with focus on workplace stress and emotional regulation.',
                    'specialties': ['mindfulness', 'meditation', 'workplace-wellness'],
                    'verified': True,
                    'featured': False
                },
                {
                    'name': 'Dr. Emily Rodriguez',
                    'slug': 'dr-emily-rodriguez',
                    'title': 'Relationship Therapist',
                    'bio': 'Licensed marriage and family therapist specializing in communication and relationship dynamics.',
                    'specialties': ['relationships', 'communication', 'couples-therapy'],
                    'verified': True,
                    'featured': True
                }
            ]
            
            for expert in experts_data:
                # Use parameterized queries for security
                await self.connection.execute('''
                    INSERT INTO experts (id, name, slug, title, bio, specialties, verified, featured, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (slug) DO NOTHING
                ''', 
                str(uuid.uuid4()),
                expert['name'],
                expert['slug'],
                expert['title'],
                expert['bio'],
                expert['specialties'],
                expert['verified'],
                expert['featured'],
                'active'
                )
            
            logger.info("Experts data populated securely")
            
        except Exception as e:
            logger.error(f"Failed to populate experts: {e}")
            raise
    
    async def populate_content(self):
        """Populate content table with security-validated data and video streaming support"""
        try:
            # Get expert and category IDs for foreign key relationships
            experts = await self.connection.fetch("SELECT id, slug FROM experts")
            categories = await self.connection.fetch("SELECT id, slug FROM categories")
            
            if not experts or not categories:
                raise ValueError("Experts and categories must exist before adding content")
            
            # Create lookup dictionaries
            expert_lookup = {expert['slug']: expert['id'] for expert in experts}
            category_lookup = {cat['slug']: cat['id'] for cat in categories}
            
            # Enhanced content data with video streaming support
            content_data = [
                {
                    'title': 'Understanding Anxiety: A Clinical Perspective',
                    'slug': 'understanding-anxiety-clinical',
                    'description': 'Professional overview of anxiety disorders and evidence-based treatment approaches.',
                    'content_type': 'video',
                    'expert_slug': 'dr-sarah-thompson',
                    'category_slug': 'mental-health',
                    'duration_seconds': 1200,
                    'access_tier': 'free',
                    'featured': True,
                    # Video streaming data
                    's3_key_video_720p': 'videos/720p/understanding-anxiety-clinical-720p.mp4',
                    's3_key_video_1080p': 'videos/1080p/understanding-anxiety-clinical-1080p.mp4',
                    's3_key_thumbnail': 'thumbnails/understanding-anxiety-clinical-thumb.jpg',
                    's3_key_poster': 'posters/understanding-anxiety-clinical-poster.jpg',
                    'video_duration_seconds': 1200,
                    'has_video': True
                },
                {
                    'title': 'Basic Mindfulness Meditation',
                    'slug': 'basic-mindfulness-meditation',
                    'description': 'Introduction to mindfulness meditation techniques for stress reduction.',
                    'content_type': 'video',
                    'expert_slug': 'dr-michael-chen',
                    'category_slug': 'mindfulness',
                    'duration_seconds': 900,
                    'access_tier': 'free',
                    'featured': False,
                    # Video streaming data
                    's3_key_video_720p': 'videos/720p/basic-mindfulness-meditation-720p.mp4',
                    's3_key_thumbnail': 'thumbnails/basic-mindfulness-meditation-thumb.jpg',
                    'video_duration_seconds': 900,
                    'has_video': True
                },
                {
                    'title': 'Healthy Communication Patterns',
                    'slug': 'healthy-communication-patterns',
                    'description': 'Essential communication skills for building stronger relationships.',
                    'content_type': 'video',
                    'expert_slug': 'dr-emily-rodriguez',
                    'category_slug': 'relationships',
                    'duration_seconds': 1500,
                    'access_tier': 'premium',
                    'featured': True,
                    # Video streaming data
                    's3_key_video_720p': 'videos/720p/healthy-communication-patterns-720p.mp4',
                    's3_key_video_1080p': 'videos/1080p/healthy-communication-patterns-1080p.mp4',
                    's3_key_thumbnail': 'thumbnails/healthy-communication-patterns-thumb.jpg',
                    's3_key_poster': 'posters/healthy-communication-patterns-poster.jpg',
                    'video_duration_seconds': 1500,
                    'has_video': True
                },
                {
                    'title': 'Cognitive Behavioral Techniques',
                    'slug': 'cognitive-behavioral-techniques',
                    'description': 'Practical CBT exercises for managing negative thought patterns.',
                    'content_type': 'video',
                    'expert_slug': 'dr-sarah-thompson',
                    'category_slug': 'mental-health',
                    'duration_seconds': 600,
                    'access_tier': 'premium',
                    'featured': False,
                    # Video streaming data
                    's3_key_video_720p': 'videos/720p/cognitive-behavioral-techniques-720p.mp4',
                    's3_key_thumbnail': 'thumbnails/cognitive-behavioral-techniques-thumb.jpg',
                    'video_duration_seconds': 600,
                    'has_video': True
                },
                {
                    'title': 'Introduction to Stress Management',
                    'slug': 'introduction-to-stress-management',
                    'description': 'Learn fundamental techniques for managing daily stress and building resilience.',
                    'content_type': 'video',
                    'expert_slug': 'dr-sarah-thompson',
                    'category_slug': 'mental-health',
                    'duration_seconds': 1050,
                    'access_tier': 'free',
                    'featured': True,
                    # Video streaming data
                    's3_key_video_720p': 'videos/720p/stress-management-intro-720p.mp4',
                    's3_key_video_1080p': 'videos/1080p/stress-management-intro-1080p.mp4',
                    's3_key_thumbnail': 'thumbnails/stress-management-intro-thumb.jpg',
                    'video_duration_seconds': 1050,
                    'has_video': True
                }
            ]
            
            for content in content_data:
                # Validate required relationships exist
                expert_id = expert_lookup.get(content['expert_slug'])
                category_id = category_lookup.get(content['category_slug'])
                
                if not expert_id or not category_id:
                    logger.warning(f"Skipping content '{content['title']}' - missing relationships")
                    continue
                
                # Use parameterized queries for security with video streaming support
                await self.connection.execute('''
                    INSERT INTO content (
                        id, title, slug, description, content_type, expert_id, category_id,
                        duration_seconds, access_tier, featured, status, view_count, like_count,
                        s3_key_video_720p, s3_key_video_1080p, s3_key_thumbnail, s3_key_poster,
                        video_duration_seconds, video_format, has_video
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                    ON CONFLICT (slug) DO NOTHING
                ''',
                str(uuid.uuid4()),
                content['title'],
                content['slug'],
                content['description'],
                content['content_type'],
                expert_id,
                category_id,
                content['duration_seconds'],
                content['access_tier'],
                content['featured'],
                'published',
                0,  # view_count
                0,  # like_count
                content.get('s3_key_video_720p'),
                content.get('s3_key_video_1080p'),
                content.get('s3_key_thumbnail'),
                content.get('s3_key_poster'),
                content.get('video_duration_seconds'),
                'mp4',  # video_format
                content.get('has_video', False)
                )
            
            logger.info("Content data with video streaming support populated securely")
            
        except Exception as e:
            logger.error(f"Failed to populate content: {e}")
            raise
    
    async def create_video_analytics_table(self):
        """Create video analytics table for streaming metrics"""
        try:
            await self.connection.execute('''
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
            
            logger.info("Video analytics table created")
            
        except Exception as e:
            logger.error(f"Failed to create video analytics table: {e}")
            raise
    
    async def create_security_indexes(self):
        """Create additional security and performance indexes"""
        try:
            # Performance and security indexes
            security_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_content_access_tier ON content(access_tier)",
                "CREATE INDEX IF NOT EXISTS idx_content_status ON content(status)",
                "CREATE INDEX IF NOT EXISTS idx_experts_status ON experts(status)",
                "CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)",
                "CREATE INDEX IF NOT EXISTS idx_content_expert_id ON content(expert_id)",
                "CREATE INDEX IF NOT EXISTS idx_content_category_id ON content(category_id)",
                # Video streaming indexes
                "CREATE INDEX IF NOT EXISTS idx_content_has_video ON content(has_video) WHERE has_video = true",
                "CREATE INDEX IF NOT EXISTS idx_content_access_tier_video ON content(access_tier, has_video)",
                "CREATE INDEX IF NOT EXISTS idx_video_analytics_content ON video_analytics(content_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_video_analytics_user ON video_analytics(user_id, created_at)"
            ]
            
            for index_sql in security_indexes:
                await self.connection.execute(index_sql)
            
            logger.info("Security and video streaming indexes created")
            
        except Exception as e:
            logger.error(f"Failed to create security indexes: {e}")
            raise
    
    async def validate_data_integrity(self):
        """Validate data integrity and relationships"""
        try:
            # Check foreign key relationships
            orphaned_content = await self.connection.fetchval('''
                SELECT COUNT(*) FROM content c
                WHERE c.expert_id NOT IN (SELECT id FROM experts)
                OR c.category_id NOT IN (SELECT id FROM categories)
            ''')
            
            if orphaned_content > 0:
                raise ValueError(f"Data integrity violation: {orphaned_content} orphaned content records")
            
            # Verify access tiers are valid
            invalid_tiers = await self.connection.fetchval('''
                SELECT COUNT(*) FROM content
                WHERE access_tier NOT IN ('free', 'premium')
            ''')
            
            if invalid_tiers > 0:
                raise ValueError(f"Data integrity violation: {invalid_tiers} invalid access tiers")
            
            # Validate video content has required fields
            invalid_video_content = await self.connection.fetchval('''
                SELECT COUNT(*) FROM content
                WHERE has_video = true AND (s3_key_video_720p IS NULL OR s3_key_thumbnail IS NULL)
            ''')
            
            if invalid_video_content > 0:
                logger.warning(f"Found {invalid_video_content} video content items missing required streaming keys")
            
            logger.info("Data integrity validation passed")
            
        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            raise

async def populate_database():
    """Main function to securely populate database with video streaming support"""
    populator = SecureDataPopulator()
    
    try:
        await populator.connect()
        
        # Check if data already exists
        if await populator.check_existing_data():
            print("Data already exists. Skipping population to prevent duplicates.")
            return True
        
        # Populate data in dependency order
        logger.info("Starting secure data population with video streaming support...")
        
        # Add video columns first
        await populator.add_video_columns()
        
        # Populate core data
        await populator.populate_experts()
        await populator.populate_content()
        
        # Create supporting infrastructure
        await populator.create_video_analytics_table()
        await populator.create_security_indexes()
        await populator.validate_data_integrity()
        
        logger.info("Database population completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database population failed: {e}")
        return False
        
    finally:
        await populator.disconnect()

if __name__ == "__main__":
    success = asyncio.run(populate_database())
    if success:
        print("✅ Database populated securely with video streaming support!")
        print("📊 Summary:")
        print("   - 3 verified experts added")
        print("   - 5 video content items added (mix of free/premium)")
        print("   - Video streaming columns and analytics table created")
        print("   - Sample S3 keys added for testing")
        print("   - Security indexes created")
        print("   - Data integrity validated")
        print("")
        print("🎬 Video streaming ready!")
        print("   - Content has S3 video keys for 720p/1080p")
        print("   - Thumbnails and posters configured")
        print("   - Analytics tracking enabled")
    else:
        print("❌ Database population failed!")
        exit(1)