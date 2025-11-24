terraform {
  required_providers {
    helm = {
      source = "hashicorp/helm"
    }
    kubernetes = {
      source = "hashicorp/kubernetes"
    }
  }
}

resource "helm_release" "argocd" {
  name             = "argocd"
  namespace        = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "5.46.6" # latest stable as of now
  create_namespace = true

  values = [
    file("${path.module}/values.yaml")
  ]
}

resource "null_resource" "patch_argocd_service" {
  depends_on = [helm_release.argocd]

  provisioner "local-exec" {
    command = <<EOT
kubectl patch svc argocd-server -n argocd -p '{"spec": {"ports": [{"name": "https", "port": 443, "targetPort": 8080}]}}'
EOT
  }
}

