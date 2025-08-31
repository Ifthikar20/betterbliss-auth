#!/bin/bash

# Continue Database Setup for Better & Bliss
# Run this to complete the remaining steps for your existing database

set -e

echo "🚀 Continuing Database Setup for Better & Bliss"
echo "This will complete the remaining steps:"
echo "  3. Get database connection info"
echo "  4. Test connection"
echo "  5. Create database schema"
echo "  6. Insert sample data"
echo ""

# ===============================
# CONFIGURATION (for existing database)
# ===============================

# Use your existing database from the previous run
DB_INSTANCE_ID="betterbliss-db-1756657116"
DB_USERNAME="betterbliss_user"
DB_PASSWORD="SecureBB1756657116!"
DB_NAME="betterbliss"
DB_SG_ID="sg-0f47cd94776455946"  # Your security group
REGION="us-east-1"

echo "Using existing database:"
echo "- Instance ID: $DB_INSTANCE_ID"
echo "- Database: $DB_NAME"
echo "- Username: $DB_USERNAME"
echo ""

# ===============================
# STEP 3: GET CONNECTION INFO
# ===============================

echo "Step 3/6: Getting database connection information..."

DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_ID \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

DB_PORT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_ID \
    --query 'DBInstances[0].Endpoint.Port' \
    --output text)

echo "Database endpoint: $DB_ENDPOINT"
echo "Database port: $DB_PORT"

# Create environment configuration
cat > .env.production << EOL
# Production Database Configuration
DATABASE_URL=postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:$DB_PORT/$DB_NAME
DB_HOST=$DB_ENDPOINT
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USERNAME=$DB_USERNAME
DB_PASSWORD=$DB_PASSWORD
DB_SSL_MODE=require

# AWS Resources (for cleanup later)
DB_INSTANCE_ID=$DB_INSTANCE_ID
DB_SECURITY_GROUP_ID=$DB_SG_ID
EOL

echo "✅ Step 3 complete - Configuration saved"

# ===============================
# STEP 4: INSTALL DEPENDENCIES & TEST CONNECTION
# ===============================

echo "Step 4/6: Installing dependencies and testing connection..."

# Install Python dependencies for testing
pip install asyncpg python-dotenv 2>/dev/null || {
    echo "Installing pip dependencies..."
    python -m pip install asyncpg python-dotenv
}

# Create enhanced connection test with debugging
cat > quick_test.py << 'EOF'
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
EOF

# Test the connection
python quick_test.py

if [ $? -eq 0 ]; then
    echo "✅ Step 4 complete - Database connection successful!"
else
    echo "❌ Database connection failed. Check the troubleshooting section."
    exit 1
fi

# ===============================
# STEP 5: CREATE DATABASE SCHEMA
# ===============================

echo "Step 5/6: Creating database schema..."

cat > create_schema.py << 'EOF'
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
EOF

python create_schema.py

echo "✅ Step 5 complete - Database schema created!"

# ===============================
# STEP 6: FINAL TEST AND SUMMARY
# ===============================

echo "Step 6/6: Final testing and summary..."

# Test that everything works
python quick_test.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SETUP COMPLETE! 🎉"
    echo "=========================="
    echo ""
    echo "Your database is ready:"
    echo "- Endpoint: $DB_ENDPOINT"
    echo "- Database: $DB_NAME"
    echo "- Username: $DB_USERNAME"
    echo "- Password: $DB_PASSWORD"
    echo "- Cost: FREE for 12 months!"
    echo ""
    echo "Configuration saved in: .env.production"
    echo ""
    echo "Next steps to integrate with your backend:"
    echo "1. Add database dependencies to requirements.txt:"
    echo "   asyncpg==0.29.0"
    echo "   sqlalchemy[asyncio]==2.0.23"
    echo ""
    echo "2. Update your ECS task definition with these environment variables:"
    echo "   DATABASE_URL=postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:$DB_PORT/$DB_NAME"
    echo "   DB_HOST=$DB_ENDPOINT"
    echo "   DB_PORT=$DB_PORT"
    echo "   DB_NAME=$DB_NAME"
    echo "   DB_USERNAME=$DB_USERNAME"
    echo "   DB_PASSWORD=$DB_PASSWORD"
    echo ""
    echo "3. Redeploy your ECS service"
    echo ""
    echo "Manual connection test:"
    echo "psql postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:$DB_PORT/$DB_NAME"
    
    # ===============================
    # CLEANUP INSTRUCTIONS
    # ===============================
    echo ""
    echo "💡 CLEANUP INSTRUCTIONS (save for later):"
    echo "To delete everything and stop charges:"
    echo "aws rds delete-db-instance --db-instance-identifier $DB_INSTANCE_ID --skip-final-snapshot"
    echo "aws ec2 delete-security-group --group-id $DB_SG_ID"
    echo "aws rds delete-db-subnet-group --db-subnet-group-name betterbliss-subnet-group"
    
else
    echo "❌ Final test failed. Check configuration."
    exit 1
fi

# ===============================
# TROUBLESHOOTING SECTION
# ===============================

cat > troubleshooting.md << 'EOF'
# Database Setup Troubleshooting

## Common Issues

### 1. AWS CLI Not Configured
```bash
aws configure
# Enter your Access Key, Secret Key, Region (us-east-1), and format (json)
```

### 2. Missing Permissions
Ensure your AWS user has these policies:
- AmazonRDSFullAccess
- AmazonEC2FullAccess
- AmazonVPCFullAccess

### 3. Subnet Group Already Exists
```bash
aws rds delete-db-subnet-group --db-subnet-group-name betterbliss-subnet-group
```

### 4. Connection Issues
- Check security group rules
- Verify VPC configuration
- Ensure database is in "available" state

### 5. Clean Up Resources
```bash
# Delete database
aws rds delete-db-instance --db-instance-identifier YOUR_DB_ID --skip-final-snapshot

# Delete security group (after DB is deleted)
aws ec2 delete-security-group --group-id YOUR_SG_ID

# Delete subnet group
aws rds delete-db-subnet-group --db-subnet-group-name betterbliss-subnet-group
```

## Check Status
```bash
# Check RDS instance status
aws rds describe-db-instances --db-instance-identifier YOUR_DB_ID

# List security groups
aws ec2 describe-security-groups --filters "Name=group-name,Values=betterbliss-*"
```
EOF

echo ""
echo "📋 Troubleshooting guide created: troubleshooting.md"