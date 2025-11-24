resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.cluster_name
  kubernetes_version  = var.kubernetes_version

  default_node_pool {
    name                = "agentpool"
    vm_size             = "Standard_B2als_v2"
    os_disk_size_gb     = 30
    os_sku              = "Ubuntu"
    vnet_subnet_id      = var.subnet_id
    enable_auto_scaling = true
    min_count           = 1
    max_count           = 3
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "calico"
    load_balancer_sku = "standard"
    service_cidr      = "10.0.2.0/24"
    dns_service_ip    = "10.0.2.10"
  }

  role_based_access_control_enabled = true
}

resource "azurerm_kubernetes_cluster_node_pool" "worker" {
  name                  = "worker"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_B2als_v2"
  os_disk_size_gb       = 30
  os_type               = "Linux"
  os_sku                = "Ubuntu"
  vnet_subnet_id        = var.subnet_id
  mode                  = "User"
  enable_auto_scaling   = true
  min_count             = 1
  max_count             = 6

  node_taints           = ["dedicated=app:NoSchedule"]
}
