#!/bin/bash

# Quick AWS Infrastructure Setup
# Run this after your Docker container works locally

set -e

echo "🚀 Quick AWS Infrastructure Setup for BetterBliss Auth Service"

# Configuration
REPO_NAME="betterbliss-auth"
CLUSTER_NAME="betterbliss-cluster"
SERVICE_NAME="betterbliss-auth-service"
REGION="us-east-1"

# Step 1: Create ECR Repository
echo "📦 Creating ECR Repository..."
REPO_URI=$(aws ecr create-repository \
    --repository-name $REPO_NAME \
    --region $REGION \
    --query 'repository.repositoryUri' --output text 2>/dev/null || \
    aws ecr describe-repositories \
    --repository-names $REPO_NAME \
    --region $REGION \
    --query 'repositories[0].repositoryUri' --output text)

echo "✅ Repository URI: $REPO_URI"

# Step 2: Login to ECR and Push Image
echo "🔐 Logging into ECR and pushing image..."
aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin $REPO_URI

# Tag and push the image
docker tag betterbliss-auth-local:latest $REPO_URI:latest
docker push $REPO_URI:latest

echo "✅ Image pushed to ECR"

# Step 3: Create basic VPC (simplified)
echo "🌐 Setting up networking..."

# Get default VPC (simpler approach)
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=is-default,Values=true" \
    --query 'Vpcs[0].VpcId' --output text)

# Get default subnets
SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[0:2].SubnetId' --output text)

SUBNET1_ID=$(echo $SUBNETS | cut -d' ' -f1)
SUBNET2_ID=$(echo $SUBNETS | cut -d' ' -f2)

echo "✅ Using default VPC: $VPC_ID"
echo "✅ Subnets: $SUBNET1_ID, $SUBNET2_ID"

# Step 4: Create Security Groups
echo "🔒 Creating security groups..."

# ALB Security Group
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name betterbliss-alb-sg \
    --description "Security group for ALB" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=betterbliss-alb-sg" \
    --query 'SecurityGroups[0].GroupId' --output text)

# Allow HTTP/HTTPS to ALB
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 2>/dev/null || true

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 2>/dev/null || true

# ECS Security Group
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name betterbliss-ecs-sg \
    --description "Security group for ECS tasks" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=betterbliss-ecs-sg" \
    --query 'SecurityGroups[0].GroupId' --output text)

# Allow traffic from ALB to ECS
aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8000 \
    --source-group $ALB_SG_ID 2>/dev/null || true

echo "✅ Security groups created"

# Step 5: Create Load Balancer
echo "⚖️ Creating Application Load Balancer..."

ALB_ARN=$(aws elbv2 create-load-balancer \
    --name betterbliss-alb \
    --subnets $SUBNET1_ID $SUBNET2_ID \
    --security-groups $ALB_SG_ID \
    --scheme internet-facing \
    --type application \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || \
    aws elbv2 describe-load-balancers \
    --names betterbliss-alb \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text)

ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --query 'LoadBalancers[0].DNSName' --output text)

# Create Target Group
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name betterbliss-targets \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null || \
    aws elbv2 describe-target-groups \
    --names betterbliss-targets \
    --query 'TargetGroups[0].TargetGroupArn' --output text)

# Create Listener
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN 2>/dev/null || true

echo "✅ Load balancer created: $ALB_DNS"

# Step 6: Create ECS Cluster
echo "📦 Creating ECS Cluster..."

aws ecs create-cluster \
    --cluster-name $CLUSTER_NAME \
    --capacity-providers FARGATE 2>/dev/null || true

# Step 7: Create IAM Roles
echo "🔑 Creating IAM roles..."

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# ECS Task Execution Role
aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }' 2>/dev/null || true

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Step 8: Create Task Definition
echo "📋 Creating Task Definition..."

aws logs create-log-group \
    --log-group-name /ecs/betterbliss-auth 2>/dev/null || true

cat > task-definition.json << EOF
{
  "family": "betterbliss-auth-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "betterbliss-auth",
      "image": "${REPO_URI}:latest",
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
          "awslogs-region": "${REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {"name": "AWS_REGION", "value": "${REGION}"},
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "FRONTEND_URL", "value": "http://${ALB_DNS}"},
        {"name": "BACKEND_URL", "value": "http://${ALB_DNS}"},
        {"name": "JWT_SECRET_KEY", "value": "temporary-secret-key-change-later"}
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

aws ecs register-task-definition \
    --cli-input-json file://task-definition.json > /dev/null

# Step 9: Create ECS Service
echo "🚀 Creating ECS Service..."

aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name $SERVICE_NAME \
    --task-definition betterbliss-auth-task \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1_ID,$SUBNET2_ID],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=betterbliss-auth,containerPort=8000" \
    --health-check-grace-period-seconds 120 > /dev/null 2>&1 || true

# Save configuration
cat > aws-config.env << EOF
REPO_URI=$REPO_URI
VPC_ID=$VPC_ID
SUBNET1_ID=$SUBNET1_ID
SUBNET2_ID=$SUBNET2_ID
ALB_SG_ID=$ALB_SG_ID
ECS_SG_ID=$ECS_SG_ID
ALB_ARN=$ALB_ARN
ALB_DNS=$ALB_DNS
TARGET_GROUP_ARN=$TARGET_GROUP_ARN
CLUSTER_NAME=$CLUSTER_NAME
SERVICE_NAME=$SERVICE_NAME
REGION=$REGION
ACCOUNT_ID=$ACCOUNT_ID
EOF

echo ""
echo "🎉 AWS Infrastructure Setup Complete!"
echo "📄 Configuration saved to aws-config.env"
echo ""
echo "🌐 Your API will be available at: http://$ALB_DNS"
echo "⏳ Wait 3-5 minutes for the service to start, then test:"
echo "   curl http://$ALB_DNS/health"
echo ""
echo "📊 Monitor deployment:"
echo "   aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME"