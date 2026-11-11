# ShopLite

> A production-style cloud-native e-commerce platform built to demonstrate modern DevOps, Platform Engineering, SRE, and Cloud Operations practices on AWS.

## Overview

ShopLite is a small e-commerce backend designed around a realistic startup scenario where a single DevOps Engineer is responsible for the entire platform lifecycle, from infrastructure provisioning and application deployment to observability, security, CI/CD, incident response, and production troubleshooting.

The platform allows users to place orders, processes them asynchronously, and exposes comprehensive operational visibility through metrics, logs, traces, dashboards, and alerts.

This project serves as a hands-on implementation of:

- AWS Infrastructure as Code (Terraform)
- Linux Administration & Security Hardening
- Docker & Containerization
- Kubernetes Operations
- GitOps with ArgoCD
- CI/CD with GitHub Actions
- Monitoring, Logging, and Distributed Tracing
- Incident Management and Root Cause Analysis (RCA)

---

## Architecture

### Infrastructure

- AWS VPC spanning two Availability Zones
- Two public subnets
- Two private subnets
- Application Load Balancer (ALB)
- Kubernetes cluster
  - 1 Control Plane Node
  - 2 Worker Nodes
- Amazon ECR for container image storage

### Platform Services

- GitHub Actions for CI/CD
- ArgoCD for GitOps deployments
- Prometheus for metrics collection
- Loki for log aggregation
- Tempo for distributed tracing
- Grafana for observability dashboards
- Alertmanager for operational alerting

---

## Application Components

### Web Frontend

Provides the customer-facing interface for placing and tracking orders.

### Catalog API

Responsible for:

- Product catalog operations
- Order creation
- PostgreSQL persistence
- Redis queue publishing

### Order Worker

Background worker responsible for:

- Consuming order jobs from Redis
- Processing orders asynchronously
- Updating order status in PostgreSQL

---

## Application Flow

```text
User
  │
  ▼
Application Load Balancer
  │
  ▼
Web Frontend
  │
  ▼
Catalog API
  │
  ├── PostgreSQL
  │
  └── Redis Queue
          │
          ▼
      Order Worker
          │
          ▼
      PostgreSQL

Metrics + Logs + Traces
          │
          ▼
       Grafana