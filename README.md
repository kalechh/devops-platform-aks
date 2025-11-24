# 🚀 Production-Grade DevOps Platform on Azure Kubernetes Service (AKS)

This project is a **complete, production-grade DevOps platform** designed, implemented, and deployed end-to-end on **Azure Kubernetes Service (AKS)**.

It integrates:

- 🔹 **Terraform IaC (modular architecture)**
- 🔹 **Jenkins CI/CD pipelines**
- 🔹 **ArgoCD GitOps continuous delivery**
- 🔹 **Azure Container Registry (ACR)**
- 🔹 **Ingress + SSL + DNS**
- 🔹 **Prometheus & Grafana monitoring**
- 🔹 **Velero backups**
- 🔹 **Calico network policies (Zero-Trust Architecture)**
- 🔹 **AI-powered anomaly detection microservice**
- 🔹 **Java backend + Angular frontend deployed on Kubernetes**

This repository represents the full platform I built during my DevOps internship project, following **enterprise-level standards**.

---

## 📌 1. **High-Level Architecture**

The platform includes:

- **Infrastructure Layer (Terraform)**
  - AKS cluster
  - Virtual Network + Subnets  
  - ACR registry  
  - DNS + SSL  
  - Ingress controller  
  - Monitoring stack  
  - Velero backup system  
  - ArgoCD GitOps system  
  - MySQL database  

- **Application Layer**
  - Angular frontend  
  - Java Spring Boot backend  
  - MySQL database  
  - AI anomaly detection microservice (FastAPI + Isolation Forest)

- **CI/CD Layer**
  - Jenkins pipelines for build, test, security scan, Docker build, and deployment  
  - GitHub Actions for optional workflows  
  - ArgoCD for GitOps deployment to AKS  

---

## 🧱 2. **Repository Structure**
devops-platform-aks/
│
├── architecture/
├── terraform/
│ ├── modules/
│ └── environments/
│
├── ci-cd/
│ ├── jenkins/
│ └── github-actions/
│
├── kubernetes/
│ ├── deployments/
│ ├── services/
│ ├── ingress/
│ ├── network-policies/
│ └── monitoring/
│
├── ai-models/
│ ├── anomaly-detection/
│ └── predictive-autoscaling/ (future)
│
├── app/
│ ├── frontend-angular/
│ └── backend-java/
│
└── docs/

