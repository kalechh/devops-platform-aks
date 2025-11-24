variable "resource_group_name" {
  type        = string
  description = "Resource group where Velero will store backups"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "kube_host" {
  type = string
}

variable "kube_client_certificate" {
  type = string
}

variable "kube_client_key" {
  type = string
}

variable "kube_cluster_ca_certificate" {
  type = string
}


variable "kube_config_ready" {
  description = "Dependency to wait for kubeconfig to be ready"
  type        = any
  default     = null
}

variable "cluster_name" {
  type        = string
  description = "The name of the AKS cluster (used to compute the MC_* resource group name)"
}
