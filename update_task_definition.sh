#!/bin/bash

# Script to update task definition with actual values
set -e

echo "🔧 Updating ECS Task Definition with actual configuration values"

# Load database configuration
source .env.production

# Load Cognito configuration  
source cognito-config.env

# Get database endpoint from AWS
DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier betterbliss-db-1756657116 \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

echo "Retrieved database endpoint: $DB_ENDPOINT"

# Create the complete task definition
cat > task-definition-complete.json << EOF
{
  "family": "betterbliss-auth-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::817977750104:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "betterbliss-auth",
      "image": "817977750104.dkr.ecr.us-east-1.amazonaws.com/betterbliss-auth:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/betterbliss-auth",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {"name": "AWS_REGION", "value": "us-east-1"},
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "COGNITO_USER_POOL_ID", "value": "$COGNITO_USER_POOL_ID"},
        {"name": "COGNITO_CLIENT_ID", "value": "$COGNITO_CLIENT_ID"},
        {"name": "COGNITO_CLIENT_SECRET", "value": "$COGNITO_CLIENT_SECRET"},
        {"name": "COGNITO_DOMAIN", "value": "$COGNITO_DOMAIN"},
        {"name": "COOKIE_DOMAIN", "value": "$COOKIE_DOMAIN"},
        {"name": "FRONTEND_URL", "value": "http://betterbliss-alb-1566345575.us-east-1.elb.amazonaws.com"},
        {"name": "BACKEND_URL", "value": "http://betterbliss-alb-1566345575.us-east-1.elb.amazonaws.com"},
        {"name": "JWT_SECRET_KEY", "value": "production-secret-key-change-this"},
        {"name": "DATABASE_URL", "value": "postgresql://$DB_USERNAME:$DB_PASSWORD@$DB_ENDPOINT:$DB_PORT/$DB_NAME"},
        {"name": "DB_HOST", "value": "$DB_ENDPOINT"},
        {"name": "DB_PORT", "value": "$DB_PORT"},
        {"name": "DB_NAME", "value": "$DB_NAME"},
        {"name": "DB_USERNAME", "value": "$DB_USERNAME"},
        {"name": "DB_PASSWORD", "value": "$DB_PASSWORD"},
        {"name": "DB_SSL_MODE", "value": "$DB_SSL_MODE"}
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

echo "✅ Complete task definition created: task-definition-complete.json"
echo ""
echo "📋 Environment variables that will be set:"
echo "   COGNITO_USER_POOL_ID: $COGNITO_USER_POOL_ID"
echo "   COGNITO_CLIENT_ID: $COGNITO_CLIENT_ID"
echo "   COGNITO_DOMAIN: $COGNITO_DOMAIN"
echo "   DATABASE_URL: postgresql://$DB_USERNAME:****@$DB_ENDPOINT:$DB_PORT/$DB_NAME"
echo "   DB_HOST: $DB_ENDPOINT"
echo ""
echo "🚀 To deploy:"
echo "   aws ecs register-task-definition --cli-input-json file://task-definition-complete.json"
echo "   aws ecs update-service --cluster betterbliss-cluster --service betterbliss-auth-service --task-definition betterbliss-auth-task"