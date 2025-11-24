terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
    }
    helm = {
      source  = "hashicorp/helm"
    }
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_storage_account" "velero" {
  name                     = "velerobackupkalech"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
}

resource "azurerm_role_assignment" "velero_contributor" {
  principal_id         = data.azurerm_client_config.current.object_id
  role_definition_name = "Contributor"
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_group_name}"
  
  depends_on = [azurerm_storage_account.velero]
}

resource "azurerm_role_assignment" "velero_contributor_mc_rg" {
  principal_id         = data.azurerm_client_config.current.object_id
  role_definition_name = "Contributor"
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/MC_${var.resource_group_name}_${var.cluster_name}_${var.location}"

  depends_on = [azurerm_storage_account.velero]
}

resource "azurerm_storage_container" "velero" {
  name                  = "velero"
  storage_account_name  = azurerm_storage_account.velero.name
  container_access_type = "private"
}

resource "kubernetes_namespace" "velero" {
  depends_on = [var.kube_config_ready]
  metadata {
    name = "velero"
  }
}

resource "kubernetes_secret" "velero_credentials" {
  depends_on = [kubernetes_namespace.velero]

  metadata {
    name      = "cloud-credentials"
    namespace = kubernetes_namespace.velero.metadata[0].name
  }

  data = {
    cloud = <<EOT
AZURE_STORAGE_ACCOUNT_NAME=${azurerm_storage_account.velero.name}
AZURE_STORAGE_ACCOUNT_ACCESS_KEY=${azurerm_storage_account.velero.primary_access_key}
AZURE_CLOUD_NAME=AzurePublicCloud
AZURE_RESOURCE_GROUP=${var.resource_group_name}
AZURE_SUBSCRIPTION_ID=${data.azurerm_client_config.current.subscription_id}
EOT
  }

  type = "Opaque"
}

resource "helm_release" "velero" {
  name             = "velero"
  repository       = "https://vmware-tanzu.github.io/helm-charts"
  chart            = "velero"
  namespace        = "velero"
  create_namespace = true
  
  values = [file("${path.module}/velero-values.yaml")]

  set {
    name  = "configuration.backupStorageLocation[0].provider"
    value = "azure"
  }

  set {
    name  = "configuration.backupStorageLocation[0].bucket"
    value = "velero"
  }

  set {
    name  = "configuration.backupStorageLocation[0].config.resourceGroup"
    value = var.resource_group_name
  }

  set {
    name  = "configuration.backupStorageLocation[0].config.storageAccount"
    value = azurerm_storage_account.velero.name
  }

  set {
    name  = "configuration.backupStorageLocation[0].config.storageAccountKeyEnvVar"
    value = "AZURE_STORAGE_ACCOUNT_ACCESS_KEY"
  }

  set {
    name  = "configuration.volumeSnapshotLocation[0].provider"
    value = "azure"
  }

  set {
    name  = "configuration.volumeSnapshotLocation[0].config.resourceGroup"
    value = var.resource_group_name
  }

  set {
    name  = "credentials.existingSecret"
    value = kubernetes_secret.velero_credentials.metadata[0].name
  }

  set {
    name  = "snapshotsEnabled"
    value = "true"
  }


  depends_on = [kubernetes_secret.velero_credentials]
}

