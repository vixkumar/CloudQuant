#!/bin/bash
set -euo pipefail

REGION="ap-south-1"
PROFILE="vixk"

echo "==> [1/4] Detecting your current public IP for restricted access..."
MY_IP=$(curl -s https://checkip.amazonaws.com || echo "0.0.0.0")
CIDR="${MY_IP}/32"
echo "Restricting access to: $CIDR"

echo "==> [2/4] Locating VPC..."
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" --profile "$PROFILE" --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)

echo "==> [3/4] Configuring restricted Security Group..."
SG_ID=$(aws ec2 describe-security-groups --region "$REGION" --profile "$PROFILE" --filters "Name=group-name,Values=cloudquant-sg" "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)
if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
  SG_ID=$(aws ec2 create-security-group --region "$REGION" --profile "$PROFILE" --group-name cloudquant-sg --description "CloudQuant App" --vpc-id "$VPC_ID" --query "GroupId" --output text)
  aws ec2 authorize-security-group-ingress --region "$REGION" --profile "$PROFILE" --group-id "$SG_ID" --protocol tcp --port 8501 --cidr "$CIDR"
  aws ec2 authorize-security-group-ingress --region "$REGION" --profile "$PROFILE" --group-id "$SG_ID" --protocol tcp --port 22 --cidr "$CIDR"
fi

echo "==> [4/4] Provisioning EC2 t3.micro with automated setup..."
AMI_ID=$(aws ssm get-parameter --region "$REGION" --profile "$PROFILE" --name "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64" --query "Parameter.Value" --output text)

INSTANCE_ID=$(aws ec2 run-instances \
  --region "$REGION" \
  --profile "$PROFILE" \
  --image-id "$AMI_ID" \
  --instance-type "t3.micro" \
  --security-group-ids "$SG_ID" \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":8,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cloudquant-prod}]' \
  --user-data file://deploy/ec2_user_data.sh \
  --query "Instances[0].InstanceId" \
  --output text)

echo "Launched Instance: $INSTANCE_ID"
echo "Waiting for public IPv4 assignment..."
aws ec2 wait instance-running --region "$REGION" --profile "$PROFILE" --instance-ids "$INSTANCE_ID"

PUBLIC_IP=$(aws ec2 describe-instances --region "$REGION" --profile "$PROFILE" --instance-ids "$INSTANCE_ID" --query "Reservations[0].Instances[0].PublicIpAddress" --output text)

echo "Instance ID : $INSTANCE_ID"
echo "Public IPv4 : $PUBLIC_IP"
echo "App URL     : http://${PUBLIC_IP}:8501"
