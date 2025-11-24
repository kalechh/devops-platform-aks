terraform {
  required_providers {
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

# Provider Configurations

provider "azurerm" {
  features {}
}

# Kubernetes provider - dynamically configured from AKS outputs
provider "kubernetes" {
  host                   = module.aks.kube_config_host
  client_certificate     = base64decode(module.aks.kube_config_client_certificate)
  client_key             = base64decode(module.aks.kube_config_client_key)
  cluster_ca_certificate = base64decode(module.aks.kube_config_cluster_ca_certificate)
}

# Helm provider - explicitly configured to use the same AKS connection details
provider "helm" {
  kubernetes {
    host                   = module.aks.kube_config_host
    client_certificate     = base64decode(module.aks.kube_config_client_certificate)
    client_key             = base64decode(module.aks.kube_config_client_key)
    cluster_ca_certificate = base64decode(module.aks.kube_config_cluster_ca_certificate)
  }
}

# Modules

module "resource_group" {
  source              = "./modules/resource_group"
  resource_group_name = var.resource_group_name
  location            = var.location
}

module "network" {
  source              = "./modules/network"
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
}

module "aks" {
  source              = "./modules/aks"
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  cluster_name        = var.cluster_name
  kubernetes_version  = var.kubernetes_version
  subnet_id           = module.network.subnet_id
}

# Update kubeconfig using a null_resource
resource "null_resource" "update_kubeconfig" {
  depends_on = [module.aks]

  provisioner "local-exec" {
    command = <<EOT
az aks get-credentials --resource-group ${module.resource_group.name} --name ${module.aks.cluster_name} --overwrite-existing
sleep 5
EOT
  }
}

# Monitoring module that deploys the helm chart for kube-prometheus-stack.
module "monitoring" {
  source     = "./modules/monitoring"
  depends_on = [null_resource.update_kubeconfig]
  providers = {
    helm = helm
  }
}

# automated daily snapshots with 15-day retention for your MySQL PVC disk
module "velero" {
  source = "./modules/velero"

  resource_group_name         = module.resource_group.name
  location                    = module.resource_group.location

  kube_host                   = module.aks.kube_config_host
  kube_client_certificate     = module.aks.kube_config_client_certificate
  kube_client_key             = module.aks.kube_config_client_key
  kube_cluster_ca_certificate = module.aks.kube_config_cluster_ca_certificate
  kube_config_ready           = null_resource.update_kubeconfig
  
  cluster_name                = var.cluster_name

  providers = {
    azurerm    = azurerm
    helm       = helm
    kubernetes = kubernetes
  }
}


resource "null_resource" "bootstrap" {
  depends_on = [
    null_resource.update_kubeconfig,
    module.monitoring,
    module.velero
  ]

  provisioner "local-exec" {
    command = <<EOT

# Create namespace if not exists
kubectl apply -f modules/bootstrap/namespace.yaml
# Apply Jenkins RBAC
kubectl apply -f modules/bootstrap/jenkins-serviceaccount.yaml
kubectl apply -f modules/bootstrap/jenkins-role.yaml
kubectl apply -f modules/bootstrap/jenkins-rolebinding.yaml
kubectl apply -f modules/bootstrap/jenkins-clusterrole.yaml
kubectl apply -f modules/bootstrap/jenkins-clusterrolebinding.yaml

# Install Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.4/deploy/static/provider/cloud/deploy.yaml
sleep 20
# Install Cert-Manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# Apply Jenkins Secret
kubectl apply -f modules/bootstrap/secret.yaml -n hamzadevops
EOT
  }
}

module "argocd" {
  source     = "./modules/argocd"

  depends_on = [
    module.monitoring,
    null_resource.bootstrap 
  ]

  providers = {
    helm       = helm
    kubernetes = kubernetes
  }
}



