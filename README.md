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
├── README.md
│
├── architecture/
│   ├── devops-architecture.png
│   ├── aks-cluster-diagram.png
│   ├── ai-integration-diagram.png
│   └── network-policies-diagram.png
│
├── terraform/
│   ├── modules/
│   │   ├── resource-group/
│   │   ├── vnet/
│   │   ├── aks/
│   │   ├── acr/
│   │   ├── dns/
│   │   ├── ingress/
│   │   ├── prometheus-grafana/
│   │   ├── velero/
│   │   ├── argocd/
│   │   └── mysql/
│   │
│   └── environments/
│       ├── dev/
│       └── prod/
│
├── ci-cd/
│   ├── jenkins/
│   │   ├── Jenkinsfile
│   │   └── screenshots/
│   │       ├── pipeline.png
│   │       └── stages.png
│   │
│   └── github-actions/
│       └── build-and-deploy.yml
│
├── kubernetes/
│   ├── deployments/
│   │   ├── frontend.yaml
│   │   ├── backend.yaml
│   │   └── mysql.yaml
│   │
│   ├── services/
│   │   ├── frontend-svc.yaml
│   │   ├── backend-svc.yaml
│   │   └── mysql-svc.yaml
│   │
│   ├── ingress/
│   │   └── ingress.yaml
│   │
│   ├── network-policies/
│   │   ├── default-deny.yaml
│   │   ├── allow-frontend-backend.yaml
│   │   ├── allow-backend-mysql.yaml
│   │   └── allow-prometheus-backend.yaml
│   │
│   └── monitoring/
│       ├── prometheus-values.yaml
│       ├── grafana-values.yaml
│       └── dashboards/
│           └── cicd-dashboard.json
│
├── ai-models/
│   ├── anomaly-detection/
│   │   ├── model/
│   │   │   └── isolation_forest.pkl
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── Dockerfile
│   │   │   └── requirements.txt
│   │   └── README.md
│   │
│   └── predictive-autoscaling/   (future folder)
│
├── app/
│   ├── frontend-angular/
│   └── backend-java/
│       ├── src/
│       └── Dockerfile
│
└── docs/
    ├── setup-guide.md
    ├── aks-installation.md
    ├── argocd-setup.md
    ├── velero-backups.md
    ├── monitoring-stack.md
    ├── ai-integration.md
    └── troubleshooting.md

