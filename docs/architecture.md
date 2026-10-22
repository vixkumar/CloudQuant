# System Architecture — CloudQuant

## Overview

CloudQuant is architected to satisfy college coursework criteria (FT-III Cloud Computing) with maximum reliability and absolute minimal cost ($0.00 spend on AWS).

## High-Level Architecture Diagram

```mermaid
graph TD
    Client["User / Evaluator Browser (HTTP)"]
    
    subgraph AWS_Cloud ["AWS Cloud (Region: ap-south-1 / us-east-1)"]
        subgraph VPC ["Default VPC (IPv4 CIDR 172.31.0.0/16)"]
            SG["Security Group (cloudquant-sg)<br/>Inbound: TCP 8501 (Streamlit)<br/>Inbound: TCP 22 (SSH restricted)"]
            
            subgraph EC2_Instance ["Amazon EC2 Instance (t2.micro / t3.micro)"]
                OS["Amazon Linux 2023 / Ubuntu LTS"]
                Systemd["systemd service (cloudquant.service)"]
                App["Streamlit Web Server (:8501)"]
                Engine["Trading Engine & Risk Validator"]
                Strat["Strategy Evaluator (SMA + RSI)"]
                SQLite[("SQLite Embedded Database<br/>cloudquant.db")]
                
                Systemd --> App
                App --> Engine
                App --> Strat
                Engine --> SQLite
            end
            
            SG --> EC2_Instance
        end
    end
    
    ExternalAPI["yfinance API (Yahoo Finance)"]
    
    Client -->|Port 8501| SG
    App -.->|Fetch daily prices| ExternalAPI
    App -.->|Fallback if offline| App
```

## Architectural Design Decisions

1. **Monolithic Compute vs Container Orchestration:** 
   - A single EC2 micro instance hosting Streamlit and SQLite avoids the overhead and steep costs of Amazon EKS, ECS, or Application Load Balancers ($18–$40/mo).
2. **Local Embedded SQLite vs Amazon RDS:**
   - SQLite satisfies ACID properties for a single-user simulation without incurring managed database charges ($15+/mo for db.t3.micro).
3. **Stateless Fallback (Offline Mode):**
   - External dependencies (yfinance) can rate-limit or fail during an academic viva. A deterministic mathematical generator provides instant fallback with zero external calls.
