# Cost Analysis & Free Tier Verification — CloudQuant

## Cost Philosophy: Verified $0.00 Running Cost

CloudQuant was explicitly engineered to prevent unintentional cloud spending while demonstrating a full AWS cloud deployment.

## Resource Cost Breakdown

| AWS Resource | Allocated Tier / Specification | Free Tier Allowance | Our Monthly Usage | Incurred Cost |
| :--- | :--- | :--- | :--- | :--- |
| **EC2 Compute** | `t2.micro` or `t3.micro` | 750 hrs/month | 1 instance (720 hrs) | **$0.00** |
| **Public IPv4 Address** | Auto-assigned Public IP | 750 hrs/month (EC2 Free Tier) | 1 IP (720 hrs) | **$0.00** |
| **EBS Storage** | 8 GB gp3 General Purpose SSD | 30 GB/month | 8 GB (27% of cap) | **$0.00** |
| **Internet Data Transfer Out** | Standard outbound egress | 100 GB/month | < 1 GB/month | **$0.00** |
| **Database** | Embedded SQLite on EBS | N/A (Included with disk) | Local file IO | **$0.00** |
| **Total Cloud Expense** | | | | **$0.00 / month** |

## Critical Cloud Cost Mitigations

1. **Elimination of Managed Relational Database (RDS):**
   - An AWS RDS `db.t3.micro` instance incurs charges once outside Free Tier and has complex backup costs. Embedded SQLite runs on the existing free EBS volume at zero marginal cost.
2. **Avoidance of Application Load Balancers (ALBs):**
   - An AWS ALB incurs an hourly base charge (~$16.20/mo) plus LCU fees. CloudQuant binds directly to port 8501 on the EC2 host.
3. **Avoidance of NAT Gateways:**
   - A single NAT Gateway costs ~$32.40/month plus data processing. All outbound traffic flows via the default Internet Gateway at $0.00.
4. **Elastic IP Charge Avoidance:**
   - Unattached or multiple Elastic IPs incur $0.005/hour. We utilize the free dynamic public IPv4 provided automatically to the EC2 instance.
5. **Credit Preservation:**
   - The user's $100 promotional credits remain 100% intact as a financial cushion.
