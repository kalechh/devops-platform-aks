#!/bin/bash

# test-integration.sh - Test the complete integration
set -e

echo "Testing Prometheus → Model → KEDA Integration"

# Port forward to access the API
kubectl port-forward svc/pod-predictor-service 8080:80 &
PF_PID=$!

# Wait for port forward
sleep 10

echo "1. Testing Prometheus connectivity..."
curl -s http://localhost:8080/health | jq '.'

echo "2. Testing current metrics from Prometheus..."
curl -s http://localhost:8080/current-metrics | jq '.'

echo "3. Testing prediction with Prometheus data..."
curl -s http://localhost:8080/predict-from-prometheus | jq '.'

echo "4. Testing KEDA metric endpoint..."
curl -s http://localhost:8080/keda-metric | jq '.'

echo "5. Testing Prometheus metrics exposition..."
curl -s http://localhost:8080/prometheus-metrics

# Kill port forward
kill $PF_PID

echo "Integration test completed!"

# validate-scaling.sh - Validate that KEDA is using your predictions
#!/bin/bash
set -e

echo "Validating KEDA scaling behavior..."

# Check KEDA ScaledObject status
echo "KEDA ScaledObject status:"
kubectl get scaledobject ml-predictor-scaler -o yaml

# Check current replica count
echo "Current replica count:"
kubectl get deployment your-workload-deployment -o jsonpath='{.status.replicas}'

# Monitor scaling events
echo "Recent scaling events:"
kubectl get events --field-selector involvedObject.name=your-workload-deployment --sort-by='.lastTimestamp' | tail -10

# Check KEDA operator logs
echo "KEDA operator logs (last 20 lines):"
kubectl logs -n keda -l app=keda-operator --tail=20

# Check your predictor logs
echo "Pod predictor logs (last 20 lines):"
kubectl logs -l app=pod-predictor --tail=20

echo "Validation completed!"

# monitor-predictions.sh - Monitor predictions in real-time
#!/bin/bash
set -e

echo "Monitoring predictions in real-time..."

# Function to get prediction
get_prediction() {
    kubectl exec -it deployment/pod-predictor -- curl -s http://localhost:8000/predict-from-prometheus | jq -r '.predicted_pod_count'
}

# Function to get current replicas
get_replicas() {
    kubectl get deployment your-workload-deployment -o jsonpath='{.status.replicas}'
}

echo "Time,Predicted_Pods,Actual_Replicas,CPU_Usage,Memory_Usage,Request_Rate"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Get prediction and metrics
    PREDICTION=$(kubectl exec deployment/pod-predictor -- curl -s http://localhost:8000/predict-from-prometheus 2>/dev/null | jq -r '.predicted_pod_count // "N/A"')
    REPLICAS=$(get_replicas)
    
    # Get metrics
    METRICS=$(kubectl exec deployment/pod-predictor -- curl -s http://localhost:8000/current-metrics 2>/dev/null)
    CPU=$(echo "$METRICS" | jq -r '.metrics.cpu_usage // "N/A"')
    MEMORY=$(echo "$METRICS" | jq -r '.metrics.memory_usage // "N/A"')
    REQUESTS=$(echo "$METRICS" | jq -r '.metrics.request_rate // "N/A"')
    
    echo "$TIMESTAMP,$PREDICTION,$REPLICAS,$CPU,$MEMORY,$REQUESTS"
    
    sleep 30
done

# setup-grafana-dashboard.sh - Create Grafana dashboard for monitoring
#!/bin/bash
set -e

echo "Setting up Grafana dashboard..."

# Create dashboard JSON
cat > pod-predictor-dashboard.json << 'EOF'
{
  "dashboard": {
    "title": "Pod Predictor Dashboard",
    "panels": [
      {
        "title": "Predicted vs Actual Pods",
        "type": "timeseries",
        "targets": [
          {
            "expr": "predicted_pod_count",
            "legendFormat": "Predicted Pods"
          },
          {
            "expr": "kube_deployment_status_replicas{deployment=\"your-workload-deployment\"}",
            "legendFormat": "Actual Replicas"
          }
        ]
      },
      {
        "title": "Model Confidence",
        "type": "stat",
        "targets": [
          {
            "expr": "model_confidence",
            "legendFormat": "Confidence"
          }
        ]
      },
      {
        "title": "Prediction Requests",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(prediction_requests_total[5m])",
            "legendFormat": "Predictions/sec"
          }
        ]
      },
      {
        "title": "Workload Metrics",
        "type": "timeseries",
        "targets": [
          {
            "expr": "avg(rate(container_cpu_usage_seconds_total{namespace=\"default\", pod=~\"your-workload.*\"}[5m])) * 100",
            "legendFormat": "CPU Usage %"
          },
          {
            "expr": "avg(container_memory_working_set_bytes{namespace=\"default\", pod=~\"your-workload.*\"}) / 1024 / 1024",
            "legendFormat": "Memory Usage MB"
          }
        ]
      }
    ]
  }
}
EOF

# Import dashboard to Grafana
GRAFANA_URL="http://grafana.monitoring.svc.cluster.local:3000"
GRAFANA_USER="admin"
GRAFANA_PASS="admin"  # Change this to your actual password

curl -X POST \
  "$GRAFANA_URL/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASS" \
  -d @pod-predictor-dashboard.json

echo "Dashboard created successfully!"

# debug-integration.sh - Debug integration issues
#!/bin/bash
set -e

echo "Debugging integration issues..."

echo "1. Checking pod predictor deployment..."
kubectl get deployment pod-predictor -o wide

echo "2. Checking pod predictor logs..."
kubectl logs -l app=pod-predictor --tail=50

echo "3. Checking KEDA ScaledObject..."
kubectl describe scaledobject ml-predictor-scaler

echo "4. Checking KEDA operator logs..."
kubectl logs -n keda -l app=keda-operator --tail=50

echo "5. Testing Prometheus connectivity from pod..."
POD_NAME=$(kubectl get pods -l app=pod-predictor -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD_NAME -- curl -s http://prometheus-server.monitoring.svc.cluster.local:80/api/v1/query?query=up | jq '.'

echo "6. Testing prediction endpoint..."
kubectl exec $POD_NAME -- curl -s http://localhost:8000/predict-from-prometheus | jq '.'

echo "7. Checking service endpoints..."
kubectl get endpoints pod-predictor-service

echo "Debug completed!"