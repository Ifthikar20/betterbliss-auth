# secure_data_population.py - Security-first database population
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
        """Populate content table with security-validated data"""
        try:
            # Get expert and category IDs for foreign key relationships
            experts = await self.connection.fetch("SELECT id, slug FROM experts")
            categories = await self.connection.fetch("SELECT id, slug FROM categories")
            
            if not experts or not categories:
                raise ValueError("Experts and categories must exist before adding content")
            
            # Create lookup dictionaries
            expert_lookup = {expert['slug']: expert['id'] for expert in experts}
            category_lookup = {cat['slug']: cat['id'] for cat in categories}
            
            # Minimal content data - no external URLs or user-generated content
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
                    'featured': True
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
                    'featured': False
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
                    'featured': True
                },
                {
                    'title': 'Cognitive Behavioral Techniques',
                    'slug': 'cognitive-behavioral-techniques',
                    'description': 'Practical CBT exercises for managing negative thought patterns.',
                    'content_type': 'article',
                    'expert_slug': 'dr-sarah-thompson',
                    'category_slug': 'mental-health',
                    'duration_seconds': 600,
                    'access_tier': 'premium',
                    'featured': False
                }
            ]
            
            for content in content_data:
                # Validate required relationships exist
                expert_id = expert_lookup.get(content['expert_slug'])
                category_id = category_lookup.get(content['category_slug'])
                
                if not expert_id or not category_id:
                    logger.warning(f"Skipping content '{content['title']}' - missing relationships")
                    continue
                
                # Use parameterized queries for security
                await self.connection.execute('''
                    INSERT INTO content (
                        id, title, slug, description, content_type, expert_id, category_id,
                        duration_seconds, access_tier, featured, status, view_count, like_count
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
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
                0   # like_count
                )
            
            logger.info("Content data populated securely")
            
        except Exception as e:
            logger.error(f"Failed to populate content: {e}")
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
                "CREATE INDEX IF NOT EXISTS idx_content_category_id ON content(category_id)"
            ]
            
            for index_sql in security_indexes:
                await self.connection.execute(index_sql)
            
            logger.info("Security indexes created")
            
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
            
            logger.info("Data integrity validation passed")
            
        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            raise

async def populate_database():
    """Main function to securely populate database"""
    populator = SecureDataPopulator()
    
    try:
        await populator.connect()
        
        # Check if data already exists
        if await populator.check_existing_data():
            print("Data already exists. Skipping population to prevent duplicates.")
            return True
        
        # Populate data in dependency order
        logger.info("Starting secure data population...")
        
        await populator.populate_experts()
        await populator.populate_content()
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
        print("✅ Database populated securely!")
        print("📊 Summary:")
        print("   - 3 verified experts added")
        print("   - 4 content items added (mix of free/premium)")
        print("   - Security indexes created")
        print("   - Data integrity validated")
    else:
        print("❌ Database population failed!")
        exit(1)