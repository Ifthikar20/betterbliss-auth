#!/bin/bash

set -e

echo "🔐 Setting up AWS Cognito User Pool"

USER_POOL_NAME="betterbliss-user-pool"
CLIENT_NAME="betterbliss-web-client"
DOMAIN_PREFIX="betterbliss-auth-$(date +%s)"

# Step 1: Use existing User Pool or create new one
USER_POOL_ID="us-east-1_oFSwJ0XCM"
echo "✅ Using User Pool: $USER_POOL_ID"

# Step 2: Create User Pool Client
echo "📱 Creating User Pool Client..."

CLIENT_ID=$(aws cognito-idp create-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-name $CLIENT_NAME \
    --generate-secret \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH \
    --supported-identity-providers COGNITO \
    --callback-urls "http://localhost:3000/auth/callback" \
    --logout-urls "http://localhost:3000" \
    --allowed-o-auth-flows code \
    --allowed-o-auth-scopes openid email profile \
    --allowed-o-auth-flows-user-pool-client \
    --query 'UserPoolClient.ClientId' --output text)

echo "✅ Client created: $CLIENT_ID"

# Step 3: Get Client Secret
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-id $CLIENT_ID \
    --query 'UserPoolClient.ClientSecret' --output text)

# Step 4: Create Domain
aws cognito-idp create-user-pool-domain \
    --domain $DOMAIN_PREFIX \
    --user-pool-id $USER_POOL_ID

COGNITO_DOMAIN="https://${DOMAIN_PREFIX}.auth.us-east-1.amazoncognito.com"

# Step 5: Save Configuration
cat > cognito-config.env << EOL
COGNITO_USER_POOL_ID=$USER_POOL_ID
COGNITO_CLIENT_ID=$CLIENT_ID
COGNITO_CLIENT_SECRET=$CLIENT_SECRET
COGNITO_DOMAIN=$COGNITO_DOMAIN
COOKIE_DOMAIN=betterbliss-alb-1566345575.us-east-1.elb.amazonaws.com
EOL

echo ""
echo "🎉 Cognito Setup Complete!"
echo "📄 Configuration saved to cognito-config.env"
echo ""
cat cognito-config.env
