#!/bin/bash
# CloudQuant: Automated EC2 Provisioning Script for Amazon Linux 2023
set -euo pipefail

echo "==> Updating package manager and installing Python 3.11/git..."
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git

APP_DIR="/home/ec2-user/cloudquant"
echo "==> Setting up application directory at $APP_DIR..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"

echo "==> Creating virtual environment..."
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Initializing SQLite database schema..."
python -c "import database; database.init_db()"

echo "==> Installing and starting systemd service..."
sudo cp deploy/cloudquant.service /etc/systemd/system/cloudquant.service
sudo systemctl daemon-reload
sudo systemctl enable cloudquant.service
sudo systemctl restart cloudquant.service

echo "==> Service Status:"
sudo systemctl status cloudquant.service --no-pager

echo "==> CloudQuant is live on port 8501!"
