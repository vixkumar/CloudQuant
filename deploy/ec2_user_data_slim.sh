#!/bin/bash
set -euo pipefail
exec > /var/log/cloudquant-install.log 2>&1

BUCKET="cloudquant-deploy-790870650991"
APP_DIR="/home/ec2-user/cloudquant"

echo "==> Installing dependencies..."
dnf update -y
dnf install -y python3.11 python3.11-pip

echo "==> Creating app directory..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"

echo "==> Downloading app source from S3..."
aws s3 cp "s3://${BUCKET}/requirements.txt" ./requirements.txt --region ap-south-1
aws s3 cp "s3://${BUCKET}/app.py" ./app.py --region ap-south-1
aws s3 cp "s3://${BUCKET}/database.py" ./database.py --region ap-south-1
aws s3 cp "s3://${BUCKET}/market_data.py" ./market_data.py --region ap-south-1
aws s3 cp "s3://${BUCKET}/strategy.py" ./strategy.py --region ap-south-1
aws s3 cp "s3://${BUCKET}/trading_engine.py" ./trading_engine.py --region ap-south-1

echo "==> Installing Python packages..."
python3.11 -m pip install --upgrade pip
python3.11 -m pip install -r requirements.txt

echo "==> Creating systemd service..."
cat > /etc/systemd/system/cloudquant.service << 'EOF'
[Unit]
Description=CloudQuant Streamlit Paper Trading Application
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/cloudquant
ExecStart=/usr/local/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

chown -R ec2-user:ec2-user "$APP_DIR"
systemctl daemon-reload
systemctl enable cloudquant
systemctl start cloudquant

echo "==> CloudQuant deployment complete!"

