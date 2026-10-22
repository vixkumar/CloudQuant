# Cloud Security & IAM Posture — CloudQuant

## 1. Principle of Least Privilege
- **No Hardcoded Credentials:** The application contains zero AWS access keys, database passwords, or secret tokens.
- **IAM Policies:** Deployment requires only EC2 instance launch permissions. No administrator or root access is used by the application code.
- **Paper Trading Isolation:** The platform executes solely virtual transactions; no broker API keys or banking credentials are requested or stored.

## 2. Network Security
- **Strict Inbound Ports:** Only port 8501 (Streamlit web dashboard) is accessible.
- **SSH Protection:** SSH (port 22) is never open to `0.0.0.0/0`. It is either bound strictly to the administrator's current public IP (`/32`) or accessed via AWS Systems Manager / EC2 Instance Connect.
- **Zero Exposed Management Consoles:** SQLite database files are stored locally on the encrypted EBS volume and are never exposed via HTTP.

## 3. Academic Limitations & Production Roadmap
- **HTTP vs HTTPS:** For the minimal-cost demonstration, traffic is served over plain HTTP on port 8501. In a production environment, this would be routed through a reverse proxy (Nginx or Caddy) with Let's Encrypt SSL/TLS certificates or an AWS Certificate Manager (ACM) fronted by CloudFront.
- **Authentication:** The prototype is single-tenant for live presentation. Multi-user authentication would require AWS Cognito or OAuth2 session handling.
