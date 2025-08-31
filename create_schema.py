import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('.env.production')

async def create_schema():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Create extension for UUID
    await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create all tables
    tables_sql = '''
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            cognito_sub VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            display_name VARCHAR(100),
            avatar_url TEXT,
            subscription_tier VARCHAR(20) DEFAULT 'free',
            role VARCHAR(20) DEFAULT 'user',
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- User preferences
        CREATE TABLE IF NOT EXISTS user_preferences (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            preferred_categories TEXT[],
            preferred_content_types TEXT[],
            wellness_goals TEXT[],
            dark_mode BOOLEAN DEFAULT false,
            autoplay_videos BOOLEAN DEFAULT true,
            email_notifications BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        );
        
        -- Experts
        CREATE TABLE IF NOT EXISTS experts (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            title VARCHAR(200),
            bio TEXT,
            avatar_url TEXT,
            specialties TEXT[],
            verified BOOLEAN DEFAULT false,
            featured BOOLEAN DEFAULT false,
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Categories
        CREATE TABLE IF NOT EXISTS categories (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            icon VARCHAR(50),
            color VARCHAR(7),
            sort_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Content series
        CREATE TABLE IF NOT EXISTS content_series (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            title VARCHAR(200) NOT NULL,
            slug VARCHAR(200) UNIQUE NOT NULL,
            description TEXT,
            expert_id UUID REFERENCES experts(id),
            category_id UUID REFERENCES categories(id),
            thumbnail_url TEXT,
            total_episodes INTEGER DEFAULT 0,
            access_tier VARCHAR(20) DEFAULT 'free',
            first_episode_free BOOLEAN DEFAULT true,
            featured BOOLEAN DEFAULT false,
            status VARCHAR(20) DEFAULT 'published',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Content
        CREATE TABLE IF NOT EXISTS content (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            title VARCHAR(200) NOT NULL,
            slug VARCHAR(200) UNIQUE NOT NULL,
            description TEXT,
            content_type VARCHAR(20) DEFAULT 'video',
            expert_id UUID REFERENCES experts(id),
            category_id UUID REFERENCES categories(id),
            series_id UUID REFERENCES content_series(id),
            episode_number INTEGER,
            video_url TEXT,
            thumbnail_url TEXT,
            duration_seconds INTEGER,
            access_tier VARCHAR(20) DEFAULT 'free',
            is_first_episode BOOLEAN DEFAULT false,
            featured BOOLEAN DEFAULT false,
            trending BOOLEAN DEFAULT false,
            is_new BOOLEAN DEFAULT false,
            status VARCHAR(20) DEFAULT 'published',
            view_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Hero content
        CREATE TABLE IF NOT EXISTS hero_content (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            title VARCHAR(200) NOT NULL,
            subtitle TEXT,
            description TEXT,
            background_image_url TEXT,
            cta_text VARCHAR(100) DEFAULT 'Get Started',
            is_active BOOLEAN DEFAULT true,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Content likes
        CREATE TABLE IF NOT EXISTS content_likes (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            content_id UUID REFERENCES content(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, content_id)
        );
        
        -- Essential indexes
        CREATE INDEX IF NOT EXISTS idx_users_cognito_sub ON users(cognito_sub);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_content_slug ON content(slug);
        CREATE INDEX IF NOT EXISTS idx_content_featured ON content(featured);
    '''
    
    await conn.execute(tables_sql)
    print("Created all database tables")
    
    # Insert sample data
    await conn.execute('''
        INSERT INTO categories (name, slug, description, icon, color, sort_order) VALUES
        ('Mental Health', 'mental-health', 'Professional mental health guidance', 'brain', '#8B5CF6', 1),
        ('Mindfulness', 'mindfulness', 'Meditation and mindfulness practices', 'leaf', '#10B981', 2),
        ('Relationships', 'relationships', 'Building healthy connections', 'heart', '#F59E0B', 3),
        ('Personal Growth', 'personal-growth', 'Self-improvement and development', 'star', '#F97316', 4)
        ON CONFLICT (slug) DO NOTHING
    ''')
    
    await conn.execute('''
        INSERT INTO experts (name, slug, title, bio, specialties, verified, featured) VALUES
        ('Dr. Sarah Johnson', 'dr-sarah-johnson', 'Clinical Psychologist, PhD', 
         'Leading expert in anxiety and depression treatment with over 15 years of experience.',
         ARRAY['anxiety', 'depression', 'cbt'], true, true)
        ON CONFLICT (slug) DO NOTHING
    ''')
    
    await conn.execute('''
        INSERT INTO hero_content (title, subtitle, description, cta_text, is_active, sort_order) VALUES
        ('Transform Your Mental Health Journey', 
         'Expert-guided wellness content for lasting change',
         'Discover evidence-based techniques from leading mental health professionals',
         'Start Your Journey', true, 1)
    ''')
    
    await conn.close()
    return True

if __name__ == "__main__":
    success = asyncio.run(create_schema())
    print("✅ Schema creation completed!" if success else "❌ Schema creation failed!")
