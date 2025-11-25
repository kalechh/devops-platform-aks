#!/bin/bash

# deploy.sh - Deploy to Kubernetes
set -e

echo "🚀 Deploying to Kubernetes..."

# Check if KEDA is installed
if ! kubectl get crd scaledobjects.keda.sh &> /dev/null; then
    echo "📥 Installing KEDA..."
    kubectl apply -f keda-clean.yaml

    echo "⏳ Waiting for KEDA to be ready..."
    kubectl wait --for=condition=ready pod -l app=keda-operator -n keda --timeout=300s
else
    echo "✅ KEDA is already installed"
fi

# Create namespace if it doesn't exist
kubectl create namespace default --dry-run=client -o yaml | kubectl apply -f -

# Prepare your model file
echo "📊 Skipping model ConfigMap — using initContainer instead."

# Deploy the application
echo "🚢 Deploying FastAPI application..."
kubectl apply -f keda-http-scaler.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available deployment/pod-predictor --timeout=300s

echo "✅ Deployment completed!"

# Check deployment status
echo "📋 Deployment Status:"
kubectl get pods -l app=pod-predictor
kubectl get svc pod-predictor-service

echo ""
echo "🔍 To test the deployment:"
echo "kubectl port-forward svc/pod-predictor-service 8080:80"
echo "curl http://localhost:8080/health"
