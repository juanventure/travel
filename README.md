# Horizon Voyages - Headless AI Deployment Guide

This guide details the steps to deploy the Headless AI FastAPI Backend and the existing static Frontend to AWS.

## Architecture Overview

- **Frontend**: Hosted on AWS S3 (with CloudFront for CDN caching).
- **Backend**: Containerized FastAPI application running on AWS ECS (Elastic Container Service) with Fargate.
- **Load Balancer**: AWS Application Load Balancer (ALB) routes traffic securely from the public internet to the ECS tasks.
- **Database**: Amazon RDS for PostgreSQL.
- **Cache/State**: Amazon ElastiCache for Redis.

---

## 1. Local Development
To run the full stack locally:
```bash
docker-compose up --build
```
- Frontend: `http://localhost:80`
- Backend API: `http://localhost:8000`

---

## 2. Pushing the Docker Image to ECR

1. Authenticate your Docker client to the Amazon ECR registry.
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com
   ```
2. Create an ECR repository:
   ```bash
   aws ecr create-repository --repository-name horizon-ai-backend --region us-east-1
   ```
3. Build and tag the image:
   ```bash
   cd backend
   docker build -t horizon-ai-backend .
   docker tag horizon-ai-backend:latest <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/horizon-ai-backend:latest
   ```
4. Push the image:
   ```bash
   docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/horizon-ai-backend:latest
   ```

---

## 3. Provisioning the Databases

1. **PostgreSQL**: Create an RDS PostgreSQL instance in a private subnet. Ensure the security group allows inbound traffic on port 5432 from the ECS security group.
2. **Redis**: Create an ElastiCache Redis cluster in a private subnet. Ensure it allows inbound traffic on port 6379 from the ECS security group.

---

## 4. Deploying to ECS Fargate

### 1. Create a Task Definition
Create a new Task Definition in ECS using Fargate.
- **Network Mode**: `awsvpc`
- **Container Definition**:
  - Image: `<aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/horizon-ai-backend:latest`
  - Port Mappings: `8000`
  - Environment Variables:
    - `DATABASE_URL`: `postgresql://<rds-user>:<rds-pass>@<rds-endpoint>:5432/<db_name>`
    - `REDIS_URL`: `redis://<elasticache-endpoint>:6379/0`
    - `API_KEY`: (Store securely in AWS Secrets Manager and reference it here).

### 2. Create the Application Load Balancer (ALB)
- Create a public-facing ALB in your VPC.
- Configure listeners for HTTP (80) and HTTPS (443).
- Create a Target Group pointing to IP addresses (for Fargate) on port 8000.
- Attach an SSL/TLS Certificate (from ACM) to the HTTPS listener.

### 3. Create the ECS Service
- Create an ECS Service using the Task Definition.
- **Launch type**: FARGATE.
- **Network Configuration**: Select private subnets. Assign a Security Group that allows inbound traffic on port 8000 ONLY from the ALB's Security Group.
- **Load Balancing**: Attach the service to the Target Group created earlier.

---

## 5. Security Hardening & CORS

1. **ALB Security**: The ALB sits in a public subnet, but the ECS tasks sit in a private subnet. Only the ALB can reach the ECS tasks.
2. **CORS Restrictions**: In `backend/app/main.py`, update the `allow_origins` array to ONLY include the production frontend domain (e.g., `https://www.horizonvoyages.com`).
3. **API Key Rotation**: The frontend `CruiseChatClient.js` must inject the API key. Keep this key rotated and monitor logs for abuse. For a truly public consumer-facing widget without user-auth, implement rate-limiting via Redis and consider recaptcha validation on the `/execute-booking` endpoint.
