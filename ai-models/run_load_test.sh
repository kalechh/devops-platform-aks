#!/bin/bash
# Enhanced Load Test Execution for Event Management System

set -e

# Colors for better output visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_phase() { echo -e "${PURPLE}[PHASE]${NC} $1"; }

echo "🚀 Event Management System - Optimized Load Test"
echo "================================================="
echo "Target: https://hamzakalech.com"
echo "Duration: 2 hours (7200 seconds)"
echo "Test Type: 5-Phase Dynamic Load with HPA Validation"
echo ""

# Enhanced pre-test validation
print_status "🔍 Running comprehensive pre-test validation..."

# Create enhanced directory structure
mkdir -p results/{raw,reports} logs/{monitoring,artillery,validation} screenshots

# Test site accessibility with detailed checks
print_status "Testing site accessibility and performance..."
INGRESS_IP="20.253.53.57"
TARGET_HOST="hamzakalech.com"
if timeout 15 curl -k -H "Host: $TARGET_HOST" -s -w "HTTP: %{http_code} | DNS: %{time_namelookup}s | Connect: %{time_connect}s | Total: %{time_total}s\n" https://$INGRESS_IP > logs/validation/connectivity-$(date +%Y%m%d-%H%M%S).log; then
    print_success "✅ $TARGET_HOST is accessible via Ingress IP $INGRESS_IP"
    cat logs/validation/connectivity-*.log | tail -1
else
    print_error "❌ Cannot access https://hamzakalech.com"
    echo "Please verify:"
    echo "1. Site is online and accessible"
    echo "2. DNS resolution works correctly"
    echo "3. No firewall or network blocking"
    echo "4. SSL certificate is valid"
    exit 1
fi

# Enhanced API endpoint testing
print_status "Testing critical API endpoints..."
API_ENDPOINTS=(
    "/api/actuator/health"
    "/api/events"
    "/api/events?page=0&size=5"
)

for endpoint in "${API_ENDPOINTS[@]}"; do
    if timeout 10 curl -s -f "https://hamzakalech.com${endpoint}" > /dev/null; then
        print_success "✅ API endpoint accessible: ${endpoint}"
    else
        print_warning "⚠️  API endpoint not accessible: ${endpoint}"
    fi
done

# Enhanced cluster status validation
print_status "📊 Current cluster baseline status..."

echo ""
print_phase "HPA Configuration:"
kubectl get hpa -n hamzadevops -o custom-columns="NAME:.metadata.name,MIN:.spec.minReplicas,MAX:.spec.maxReplicas,CURRENT:.status.currentReplicas,TARGET:.spec.targetCPUUtilizationPercentage" --no-headers

echo ""
print_phase "Current Pod Distribution:"
kubectl get pods -n hamzadevops --no-headers | grep -E "(eventmanagement|angular)" | wc -l | xargs echo "App pods:"
kubectl get pods -n hamzadevops --field-selector=status.phase=Running --no-headers | wc -l | xargs echo "Running pods:"

echo ""
print_phase "Node Resources:"
kubectl get nodes --no-headers | wc -l | xargs echo "Total nodes:"
kubectl top nodes --no-headers 2>/dev/null | head -5 || print_warning "Node metrics temporarily unavailable"

# Verify Artillery installation and version
if ! command -v artillery &> /dev/null; then
    print_error "Artillery not found. Installing globally..."
    npm install -g artillery
fi

ARTILLERY_VERSION=$(artillery version)
print_success "Artillery ready: ${ARTILLERY_VERSION}"

# Create enhanced real-time monitoring script
print_status "🖥️  Setting up enhanced monitoring dashboard..."

cat <<'EOF' > monitor_enhanced.sh
#!/bin/bash
# Enhanced real-time monitoring for load test phases

LOG_FILE="logs/monitoring/enhanced-monitoring-$(date +%Y%m%d-%H%M%S).log"
PHASE_LOG="logs/monitoring/phase-transitions-$(date +%Y%m%d-%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

{
    echo "Enhanced Load Test Monitoring Started: $(date)"
    echo "=============================================="
    echo "Expected Scaling Pattern:"
    echo "Phase 1: Medium Load (30min)  - 45-55 RPS  → 3-5 pods, 2-3 nodes"
    echo "Phase 2: Light Load (20min)   - 10 RPS     → 1-2 pods, 1-2 nodes"
    echo "Phase 3: Heavy Load (25min)   - 90-110 RPS → 8-12 pods, 4-6 nodes"
    echo "Phase 4: Medium Load (30min)  - 45-55 RPS  → 3-5 pods, 2-3 nodes"
    echo "Phase 5: Light Load (15min)   - 10 RPS     → 1-2 pods, 1-2 nodes"
    echo "=============================================="
} | tee -a $LOG_FILE

ITERATION=0
START_TIME=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    ELAPSED_MINUTES=$((ELAPSED / 60))
    
    # Determine current phase based on elapsed time
    if [ $ELAPSED_MINUTES -lt 30 ]; then
        CURRENT_PHASE="Phase 1: Medium Load (45-55 RPS)"
        EXPECTED_PODS="3-5"
        EXPECTED_NODES="2-3"
    elif [ $ELAPSED_MINUTES -lt 50 ]; then
        CURRENT_PHASE="Phase 2: Light Load (10 RPS)"
        EXPECTED_PODS="1-2"
        EXPECTED_NODES="1-2"
    elif [ $ELAPSED_MINUTES -lt 75 ]; then
        CURRENT_PHASE="Phase 3: Heavy Load (90-110 RPS)"
        EXPECTED_PODS="8-12"
        EXPECTED_NODES="4-6"
    elif [ $ELAPSED_MINUTES -lt 105 ]; then
        CURRENT_PHASE="Phase 4: Medium Load (45-55 RPS)"
        EXPECTED_PODS="3-5"
        EXPECTED_NODES="2-3"
    else
        CURRENT_PHASE="Phase 5: Light Load (10 RPS)"
        EXPECTED_PODS="1-2"
        EXPECTED_NODES="1-2"
    fi
    
    {
        echo ""
        echo -e "${PURPLE}📊 Monitoring Update #$((++ITERATION)) - $(date)${NC}"
        echo -e "${BLUE}⏱️  Elapsed: ${ELAPSED_MINUTES}min | Current: ${CURRENT_PHASE}${NC}"
        echo -e "${YELLOW}🎯 Expected: ${EXPECTED_PODS} pods, ${EXPECTED_NODES} nodes${NC}"
        echo "================================================================"
        
        # Cluster nodes status
        TOTAL_NODES=$(kubectl get nodes --no-headers | wc -l)
        WORKER_NODES=$(kubectl get nodes -l agentpool=worker --no-headers 2>/dev/null | wc -l || echo "N/A")
        echo -e "${GREEN}🏗️  Cluster Nodes: ${TOTAL_NODES} total, ${WORKER_NODES} workers${NC}"
        
        # HPA detailed status
        echo -e "${BLUE}📈 HPA Scaling Status:${NC}"
        kubectl get hpa -n hamzadevops -o custom-columns="NAME:.metadata.name,CURRENT:.status.currentReplicas,DESIRED:.status.desiredReplicas,MIN:.spec.minReplicas,MAX:.spec.maxReplicas,CPU%:.status.currentMetrics[0].resource.current.averageUtilization" 2>/dev/null || echo "HPA data unavailable"
        
        # Pod distribution and status
        APP_PODS=$(kubectl get pods -n hamzadevops --no-headers | grep -E "(eventmanagement|angular)" | wc -l)
        RUNNING_PODS=$(kubectl get pods -n hamzadevops --field-selector=status.phase=Running --no-headers | wc -l)
        PENDING_PODS=$(kubectl get pods -n hamzadevops --field-selector=status.phase=Pending --no-headers | wc -l)
        
        echo -e "${GREEN}🔄 Pod Status: ${APP_PODS} app pods (${RUNNING_PODS} running, ${PENDING_PODS} pending)${NC}"
        
        # Resource utilization
        echo -e "${CYAN}💻 Resource Usage (Top 5 Pods):${NC}"
        kubectl top pods -n hamzadevops --no-headers 2>/dev/null | head -5 | while read line; do
            echo "   $line"
        done || echo "   Pod metrics temporarily unavailable"
        
        echo -e "${CYAN}🖥️  Node Resource Usage:${NC}"
        kubectl top nodes --no-headers 2>/dev/null | while read line; do
            echo "   $line"
        done || echo "   Node metrics temporarily unavailable"
        
        # Phase validation
        if [ $APP_PODS -ge 8 ] && [ $ELAPSED_MINUTES -ge 50 ] && [ $ELAPSED_MINUTES -lt 75 ]; then
            echo -e "${GREEN}✅ Heavy load scaling detected: ${APP_PODS} pods${NC}" | tee -a $PHASE_LOG
        fi
        
        echo "================================================================"
        
    } | tee -a $LOG_FILE
    
    sleep 30
done
EOF

chmod +x monitor_enhanced.sh

# Start enhanced monitoring in background
print_status "🔥 Starting enhanced monitoring dashboard..."
./monitor_enhanced.sh &
MONITOR_PID=$!

# Enhanced cleanup trap
trap 'kill $MONITOR_PID 2>/dev/null || true; print_status "Monitoring stopped"; echo "📁 Check logs/ directory for detailed results"' EXIT

# Wait for monitoring to initialize
sleep 5

# Display enhanced test plan
echo ""
print_phase "📋 Detailed Load Test Execution Plan:"
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ Phase │ Duration │    Load     │ Expected Scaling │ Validation            │"
echo "├────────────────────────────────────────────────────────────────────────────┤"
echo "│  1    │ 30 min   │ 45–55 RPS   │ 3-5 pods, 2-3 n │ HPA triggered         │"
echo "│  2    │ 20 min   │ 10 RPS      │ 1-2 pods, 1-2 n │ Scale down            │"
echo "│  3    │ 25 min   │ 90–110 RPS  │ 8-12 pods,4-6 n │ Peak scaling          │"
echo "│  4    │ 30 min   │ 45–55 RPS   │ 3-5 pods, 2-3 n │ Stabilization         │"
echo "│  5    │ 15 min   │ 10 RPS      │ 1-2 pods, 1-2 n │ Final cleanup         │"
echo "└────────────────────────────────────────────────────────────────────────────┘"
echo ""

print_warning "⏰ Starting optimized load test in 15 seconds..."
print_warning "   Press Ctrl+C to cancel"
echo ""

for i in {15..1}; do
    echo -ne "\r${YELLOW}Starting in: ${i} seconds...${NC} "
    sleep 1
done
echo ""

print_success "🔥 LAUNCHING OPTIMIZED LOAD TEST!"
print_phase "Start time: $(date)"
print_phase "Target: https://hamzakalech.com"
print_phase "Configuration: event-management-load-test.yml"

START_TIMESTAMP=$(date +%s)
START_TIME=$(date)

artillery run \
    --output "results/raw/load-test-$(date +%Y%m%d-%H%M%S).json" \
    event-management-load-test.yml 2>&1 | tee "logs/artillery/execution-$(date +%Y%m%d-%H%M%S).log"

END_TIMESTAMP=$(date +%s)
END_TIME=$(date)
TOTAL_DURATION=$((END_TIMESTAMP - START_TIMESTAMP))

print_success "🎉 Load test execution completed!"
echo ""
print_phase "Execution Summary:"
echo "Start time: $START_TIME"
echo "End time: $END_TIME"
echo "Total duration: $((TOTAL_DURATION / 60)) minutes and $((TOTAL_DURATION % 60)) seconds"

print_status "📊 Final cluster analysis..."

echo ""
print_phase "Final HPA Status:"
kubectl get hpa -n hamzadevops -o wide

echo ""
print_phase "Final Pod Distribution:"
kubectl get pods -n hamzadevops -o wide | grep -E "(eventmanagement|angular)"

echo ""
print_phase "Final Node Status:"
kubectl get nodes -o wide

print_status "📈 Generating comprehensive test report..."

cat > "results/reports/test-summary-$(date +%Y%m%d-%H%M%S).md" <<EOF
# Event Management Load Test Summary

## Test Configuration
- **Target**: https://hamzakalech.com
- **Duration**: 2 hours (120 minutes)
- **Start Time**: $START_TIME
- **End Time**: $END_TIME
- **Actual Duration**: $((TOTAL_DURATION / 60)) minutes

## Load Phases Executed
1. **Medium Load** (30min): 45-55 RPS → Expected 3-5 pods, 2-3 nodes
2. **Light Load** (20min): 10 RPS → Expected 1-2 pods, 1-2 nodes
3. **Heavy Load** (25min): 90-110 RPS → Expected 8-12 pods, 4-6 nodes
4. **Medium Load** (30min): 45-55 RPS → Expected 3-5 pods, 2-3 nodes
5. **Light Load** (15min): 10 RPS → Expected 1-2 pods, 1-2 nodes

## Files Generated
- **Raw Results**: results/raw/load-test-*.json
- **Execution Logs**: logs/artillery/execution-*.log
- **Monitoring Logs**: logs/monitoring/enhanced-monitoring-*.log
- **Phase Transitions**: logs/monitoring/phase-transitions-*.log

## Next Steps
1. Analyze Artillery results with: \`artillery report results/raw/load-test-*.json\`
2. Review HPA scaling behavior in monitoring logs
3. Check Grafana dashboards for detailed metrics
4. Validate that scaling matched expected pod/node counts
5. Review any errors or performance bottlenecks

## Validation Checklist
- [ ] Phase 1: Achieved 3-5 pods scaling
- [ ] Phase 2: Scaled down to 1-2 pods
- [ ] Phase 3: Peak scaling to 8-12 pods
- [ ] Phase 4: Stabilized at 3-5 pods
- [ ] Phase 5: Final scale down to 1-2 pods
- [ ] No persistent errors during peak load
- [ ] Response times remained acceptable
- [ ] HPA functioned correctly
EOF

echo ""
print_success "✅ Comprehensive load test completed successfully!"
echo ""
echo "📁 Generated Files:"
echo "   • Test Summary: results/reports/test-summary-*.md"
echo "   • Raw Results: results/raw/load-test-*.json"
echo "   • Execution Log: logs/artillery/execution-*.log"
echo "   • Monitoring Log: logs/monitoring/enhanced-monitoring-*.log"
echo ""
echo "📊 Analysis Commands:"
echo "   • artillery report results/raw/load-test-*.json"
echo "   • cat logs/monitoring/enhanced-monitoring-*.log | grep 'Heavy load scaling'"
echo ""

print_status "🔍 Monitoring scale-down behavior for 10 minutes..."
print_warning "   This helps validate HPA scale-down policies"

sleep 600  # 10 minutes

print_success "🏁 Complete load test cycle finished!"
print_status "   Check your monitoring dashboards and generated reports"
print_status "   Review the test summary in results/reports/ directory"
