output "kube_config" {
  value     = module.aks.kube_config
  sensitive = true
}

output "host" {
  value     = module.aks.host
  sensitive = true
}

output "fqdn" {
  value = module.aks.fqdn
}

output "cluster_name" {
  value = module.aks.cluster_name
}

output "resource_group_name" {
  value = module.resource_group.name
}
