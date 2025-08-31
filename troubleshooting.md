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
