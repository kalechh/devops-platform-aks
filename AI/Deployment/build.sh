#!/bin/bash

# build.sh - Build and push the Docker image
set -e

# Configuration - UPDATE THESE VALUES
REGISTRY="hamzakalech"
IMAGE_NAME="pod-predictor"
TAG="latest"

echo "🔨 Building Docker image..."
docker build -t ${REGISTRY}/${IMAGE_NAME}:${TAG} --no-cache .

echo "🏷️  Tagging image with timestamp..."
TIMESTAMP_TAG=$(date +%Y%m%d-%H%M%S)
docker tag ${REGISTRY}/${IMAGE_NAME}:${TAG} ${REGISTRY}/${IMAGE_NAME}:${TIMESTAMP_TAG}

echo "📤 Pushing images..."
docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}
docker push ${REGISTRY}/${IMAGE_NAME}:${TIMESTAMP_TAG}

echo "✅ Build and push completed!"
echo "📦 Image: ${REGISTRY}/${IMAGE_NAME}:${TAG}"
echo "📦 Tagged: ${REGISTRY}/${IMAGE_NAME}:${TIMESTAMP_TAG}"
