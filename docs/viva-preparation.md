# Viva Preparation & Model Answers — CloudQuant

Tailored for **FT-III Cloud Computing Coursework Evaluation**.

---

### Q1: Why did you choose an Amazon EC2 instance rather than AWS Lambda or ECS/EKS?
**Model Answer:**  
Streamlit maintains interactive WebSocket connections and stateful sessions with the browser. AWS Lambda is fundamentally stateless and request-driven with a 15-minute maximum execution timeout, making it unsuitable for persistent Streamlit dashboards without heavy workarounds. Container orchestration systems like Amazon ECS or EKS introduce control plane costs (EKS costs $0.10/hr = $73/month) and unnecessary architectural complexity for an MVP. A single EC2 `t2.micro` or `t3.micro` falls entirely under the 750-hour AWS Free Tier ($0.00 cost) and runs Streamlit natively.

---

### Q2: Why did you choose SQLite over Amazon RDS (PostgreSQL/MySQL)?
**Model Answer:**  
Cloud architecture emphasizes matching storage to the workload's requirements. CloudQuant is a single-tenant paper trading simulator where all data access occurs on the application server. SQLite is serverless, zero-configuration, and has ACID-compliant transactions directly on the local EBS volume. Amazon RDS would introduce network latency between compute and database, increase complexity (VPC subnets, DB parameter groups), and introduce billing risk ($15–$30/month if left running outside Free Tier).

---

### Q3: How did you handle cloud networking and security?
**Model Answer:**  
We implemented the Principle of Least Privilege:
1. **Security Group:** Inbound traffic is strictly restricted. Only TCP Port 8501 (the Streamlit port) is open to HTTP client traffic.
2. **SSH Hardening:** Port 22 is never exposed to `0.0.0.0/0`. We restrict SSH to the administrator's specific IP or use AWS EC2 Instance Connect.
3. **No Secrets in Code:** The application uses no hardcoded API keys or credentials.
4. **Isolated Simulation:** The app is strictly an educational paper trading platform, preventing any real-world financial liability.

---

### Q4: How does your application ensure high availability during a demonstration?
**Model Answer:**  
External financial APIs (like Yahoo Finance) are prone to rate limiting, network interruptions, or market holidays. To ensure zero-downtime during evaluation, CloudQuant implements an automated fallback mechanism: if the external API returns an error or empty data, the system automatically falls back to an internal deterministic synthetic data generator. The evaluator can also toggle "Force Sample-Data Mode" in the sidebar for offline testing.

---

### Q5: How do you manage service reliability and persistence across EC2 reboots?
**Model Answer:**  
We configured a Linux `systemd` daemon unit file (`cloudquant.service`). It registers CloudQuant as a background service with `Restart=always` and `RestartSec=5`. If the EC2 instance is rebooted or if the Streamlit process encounters an uncaught exception, systemd automatically relaunches the application without manual intervention. Because the SQLite database resides on the persistent EBS root volume, all virtual balances, holdings, and order history persist across restarts.

---

### Q6: What steps did you take to ensure this project runs at $0.00 cost?
**Model Answer:**  
1. Utilized 1 single EC2 micro instance within the 750-hour monthly allowance.
2. Kept the EBS storage at 8 GB (Free Tier allows up to 30 GB gp3).
3. Used the auto-assigned dynamic public IPv4 address covered under the 750 free hours introduced by AWS in 2024.
4. Avoided billable auxiliary resources: No NAT Gateways, no Application Load Balancers, no unattached Elastic IPs, and no AWS Marketplace AMIs.
5. Preserved 100% of the $100 promotional credits as a financial reserve.
