#!/usr/bin/env python3

import requests
import pandas as pd
import datetime
import time
import json
import os
import numpy as np
from typing import Dict, List, Optional, Tuple
import urllib3
import logging
from dataclasses import dataclass

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('prometheus_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class PrometheusConfig:
    """Configuration for Prometheus data collection"""
    url: str = "https://prometheus.hamzakalech.com"
    namespace: str = "hamzadevops"
    step_seconds: int = 30  # Higher resolution for ML
    days_back: int = 1  # Focus on recent load test data
    timeout: int = 30
    verify_ssl: bool = True
    max_retries: int = 3
    retry_delay: int = 5

class PrometheusCollector:
    """Enhanced Prometheus data collector for autoscaling ML models"""
    
    def __init__(self, config: PrometheusConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        
        # First test connectivity
        self._test_connectivity()
        
        # Define comprehensive PromQL queries for autoscaling
        self.queries = self._build_queries()
        
    def _test_connectivity(self):
        """Test Prometheus connectivity and discover correct endpoints"""
        logger.info("Testing Prometheus connectivity...")
        
        # Test different possible endpoints
        test_endpoints = [
            f"{self.config.url}/api/v1/query?query=up",
            f"{self.config.url}/prometheus/api/v1/query?query=up",
            f"{self.config.url}/-/healthy",
            f"{self.config.url}/prometheus/-/healthy",
            f"{self.config.url}",
            f"{self.config.url}/prometheus"
        ]
        
        for endpoint in test_endpoints:
            try:
                logger.info(f"Testing: {endpoint}")
                response = self.session.get(
                    endpoint, 
                    timeout=10,
                    verify=self.config.verify_ssl
                )
                logger.info(f"  Status: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"  Response: {response.text[:200]}...")
                    
                    # If this is a query endpoint and it works, update our config
                    if 'api/v1/query' in endpoint and response.status_code == 200:
                        base_url = endpoint.replace('/api/v1/query?query=up', '')
                        logger.info(f"✅ Found working API endpoint: {base_url}")
                        self.config.url = base_url
                        return
                        
            except Exception as e:
                logger.info(f"  Error: {str(e)}")
        
        logger.warning("Could not find working API endpoint, using original URL")
    
    def _build_queries(self) -> Dict[str, str]:
        """Build comprehensive PromQL queries for autoscaling metrics"""
        ns = self.config.namespace
        
        # Start with basic queries that are more likely to work
        basic_queries = {
            # Basic metrics that should exist
            "up_metrics": "up",
            "prometheus_build_info": "prometheus_build_info",
            
            # Node metrics (usually available)
            "node_load1": "node_load1",
            "node_memory_available": "node_memory_MemAvailable_bytes",
            
            # Try container metrics without namespace first
            "container_cpu_all": 'rate(container_cpu_usage_seconds_total[2m])',
            "container_memory_all": 'container_memory_working_set_bytes',
        }
        
        # Extended queries with namespace
        extended_queries = {
            # === RESOURCE UTILIZATION ===
            "cpu_usage_rate": f'rate(container_cpu_usage_seconds_total{{namespace="{ns}", container!="", container!="POD"}}[2m])',
            "cpu_requests": f'kube_pod_container_resource_requests{{namespace="{ns}", resource="cpu"}}',
            "cpu_limits": f'kube_pod_container_resource_limits{{namespace="{ns}", resource="cpu"}}',
            "memory_usage": f'container_memory_working_set_bytes{{namespace="{ns}", container!="", container!="POD"}}',
            "memory_requests": f'kube_pod_container_resource_requests{{namespace="{ns}", resource="memory"}}',
            "memory_limits": f'kube_pod_container_resource_limits{{namespace="{ns}", resource="memory"}}',
            
            # === NETWORK METRICS ===
            "network_rx_rate": f'rate(container_network_receive_bytes_total{{namespace="{ns}"}}[2m])',
            "network_tx_rate": f'rate(container_network_transmit_bytes_total{{namespace="{ns}"}}[2m])',
            
            # === APPLICATION METRICS ===
            "http_requests_rate": f'rate(http_requests_total{{namespace="{ns}"}}[2m])',
            "http_request_duration": f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{namespace="{ns}"}}[2m]))',
            "error_rate": f'rate(http_requests_total{{namespace="{ns}", status=~"5.."}}[2m])',
            
            # === KUBERNETES METRICS (MODIFIED) ===
            "pod_count_running": f'count(kube_pod_status_phase{{namespace="{ns}", phase="Running"}})',
            "pod_count_pending": f'count(kube_pod_status_phase{{namespace="{ns}", phase="Pending"}})',
            "worker_nodes_count": 'count(kube_node_labels{label_agentpool="worker"}) or count(kube_node_role{role="worker"}) or count(kube_node_info)',

            # === HPA METRICS ===
            "hpa_current_replicas": f'kube_horizontalpodautoscaler_status_current_replicas{{namespace="{ns}"}}',
            "hpa_desired_replicas": f'kube_horizontalpodautoscaler_status_desired_replicas{{namespace="{ns}"}}',
        }
        
        # Combine queries - start with basic ones
        all_queries = {**basic_queries, **extended_queries}
        return all_queries
   
    
    def test_single_query(self, query: str) -> bool:
        """Test a single query to see if it works"""
        url = f"{self.config.url}/api/v1/query"
        params = {"query": query}
        
        try:
            response = self.session.get(
                url, 
                params=params, 
                timeout=10,
                verify=self.config.verify_ssl
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    result_count = len(data.get('data', {}).get('result', []))
                    logger.info(f"✅ Query works: {query[:50]}... ({result_count} series)")
                    return True
            
            logger.warning(f"❌ Query failed: {query[:50]}... (Status: {response.status_code})")
            return False
            
        except Exception as e:
            logger.warning(f"❌ Query error: {query[:50]}... ({str(e)})")
            return False
    
    def discover_available_metrics(self) -> List[str]:
        """Discover what metrics are actually available"""
        logger.info("Discovering available metrics...")
        
        # Get all metric names
        try:
            url = f"{self.config.url}/api/v1/label/__name__/values"
            response = self.session.get(url, timeout=10, verify=self.config.verify_ssl)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    metrics = data.get('data', [])
                    logger.info(f"Found {len(metrics)} available metrics")
                    
                    # Show some examples
                    container_metrics = [m for m in metrics if 'container' in m]
                    kube_metrics = [m for m in metrics if 'kube' in m]
                    node_metrics = [m for m in metrics if 'node' in m]
                    
                    logger.info(f"Container metrics: {len(container_metrics)} (e.g., {container_metrics[:3]})")
                    logger.info(f"Kubernetes metrics: {len(kube_metrics)} (e.g., {kube_metrics[:3]})")
                    logger.info(f"Node metrics: {len(node_metrics)} (e.g., {node_metrics[:3]})")
                    
                    return metrics
        except Exception as e:
            logger.error(f"Failed to discover metrics: {str(e)}")
        
        return []
    
    def query_prometheus(self, query: str, start_time: int, end_time: int) -> Optional[Dict]:
        """Query Prometheus with retry logic"""
        url = f"{self.config.url}/api/v1/query_range"
        params = {
            "query": query,
            "start": start_time,
            "end": end_time,
            "step": f"{self.config.step_seconds}s"
        }
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Querying: {query[:60]}... (attempt {attempt + 1})")
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.config.timeout,
                    verify=self.config.verify_ssl
                )
                
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        result_count = len(data.get('data', {}).get('result', []))
                        logger.info(f"✅ Success: {result_count} time series returned")
                        return data
                    else:
                        error_msg = data.get('error', 'Unknown error')
                        logger.error(f"Prometheus error: {error_msg}")
                else:
                    logger.error(f"HTTP {response.status_code}: {response.text[:200]}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                
            if attempt < self.config.max_retries - 1:
                logger.info(f"Retrying in {self.config.retry_delay} seconds...")
                time.sleep(self.config.retry_delay)
        
        logger.error(f"Failed to query after {self.config.max_retries} attempts")
        return None
    
    def extract_time_series(self, prom_data: Dict, metric_name: str, 
                           aggregation: str = "mean") -> pd.DataFrame:
        """Extract and aggregate time series data"""
        if not prom_data or 'data' not in prom_data:
            return pd.DataFrame()
        
        results = prom_data['data'].get('result', [])
        if not results:
            return pd.DataFrame()
        
        all_data = []
        for result in results:
            labels = result.get('metric', {})
            values = result.get('values', [])
            
            for timestamp_str, value_str in values:
                try:
                    timestamp = datetime.datetime.fromtimestamp(float(timestamp_str))
                    value = float(value_str)
                    
                    row = {
                        'timestamp': timestamp,
                        metric_name: value,
                        **{f"{metric_name}_{k}": v for k, v in labels.items() if k != '__name__'}
                    }
                    all_data.append(row)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid data point: {e}")
                    continue
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        
        # Aggregate by timestamp if multiple series
        if len(results) > 1:
            numeric_cols = [metric_name]
            if len(df) > 0:
                agg_funcs = {col: aggregation for col in numeric_cols}
                df = df.groupby('timestamp').agg(agg_funcs).reset_index()
        
        return df
    
    def collect_all_metrics(self, start_time: datetime.datetime, 
                           end_time: datetime.datetime) -> pd.DataFrame:
        """Collect all metrics and merge into single DataFrame"""
        start_unix = int(start_time.timestamp())
        end_unix = int(end_time.timestamp())
        
        logger.info(f"Collecting metrics from {start_time} to {end_time}")
        logger.info(f"Time range: {start_unix} to {end_unix} (step: {self.config.step_seconds}s)")
        
        # First discover available metrics
        available_metrics = self.discover_available_metrics()
        
        # Test a few basic queries first
        logger.info("Testing basic queries...")
        working_queries = {}
        
        for metric_name, query in self.queries.items():
            if self.test_single_query(query):
                working_queries[metric_name] = query
        
        if not working_queries:
            logger.error("No working queries found! Check Prometheus connectivity.")
            return pd.DataFrame()
        
        logger.info(f"Found {len(working_queries)} working queries, proceeding with data collection...")
        
        # Collect all metrics
        dataframes = []
        failed_queries = []
        
        for metric_name, query in working_queries.items():
            logger.info(f"Processing metric: {metric_name}")
            
            prom_data = self.query_prometheus(query, start_unix, end_unix)
            if prom_data:
                df = self.extract_time_series(prom_data, metric_name)
                if not df.empty:
                    dataframes.append(df)
                    logger.info(f"✅ {metric_name}: {len(df)} data points")
                else:
                    logger.warning(f"⚠️  {metric_name}: No data points")
            else:
                failed_queries.append(metric_name)
                logger.error(f"❌ {metric_name}: Query failed")
        
        if failed_queries:
            logger.warning(f"Failed queries: {', '.join(failed_queries)}")
        
        if not dataframes:
            logger.error("No data collected from any metric!")
            return pd.DataFrame()
        
        # Merge all dataframes
        logger.info("Merging all metrics...")
        merged_df = dataframes[0]
        
        for df in dataframes[1:]:
            merged_df = pd.merge(merged_df, df, on='timestamp', how='outer')
        
        # Sort by timestamp
        merged_df = merged_df.sort_values('timestamp').reset_index(drop=True)
        
        # Forward fill missing values (common in time series)
        merged_df = merged_df.fillna(method='ffill').fillna(method='bfill')
        
        logger.info(f"✅ Merged dataset: {len(merged_df)} rows × {len(merged_df.columns)} columns")
        return merged_df
    
    def add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived features useful for ML model training"""
        if df.empty:
            return df
        
        logger.info("Adding derived features for ML...")
        
        # Time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Rolling averages (5 minute, 15 minute, 1 hour windows)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in ['hour', 'day_of_week', 'is_weekend']:
                for window in [10, 30, 120]:  # 5min, 15min, 1hr at 30s intervals
                    try:
                        df[f'{col}_rolling_{window}'] = df[col].rolling(window=window, min_periods=1).mean()
                    except Exception as e:
                        logger.warning(f"Could not create rolling feature for {col}: {e}")
        
        # Rate of change features
        for col in numeric_cols:
            if col not in ['hour', 'day_of_week', 'is_weekend'] and not col.endswith('_rolling_10') and not col.endswith('_rolling_30') and not col.endswith('_rolling_120'):
                try:
                    df[f'{col}_rate_of_change'] = df[col].diff()
                    df[f'{col}_rate_of_change_pct'] = df[col].pct_change() * 100
                except Exception as e:
                    logger.warning(f"Could not create rate of change for {col}: {e}")
        
        logger.info(f"✅ Added derived features: {len(df.columns)} total columns")
        return df
    
    def save_data(self, df: pd.DataFrame, base_filename: str = "prometheus_autoscaling_data"):
        """Save data in multiple formats for ML training"""
        if df.empty:
            logger.error("No data to save!")
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create results directory
        os.makedirs("ml_data", exist_ok=True)
        
        # Save as CSV
        csv_file = f"ml_data/{base_filename}_{timestamp}.csv"
        df.to_csv(csv_file, index=False)
        logger.info(f"✅ Saved CSV: {csv_file}")
        
        # Save as Parquet (better for ML workflows)
        try:
            parquet_file = f"ml_data/{base_filename}_{timestamp}.parquet"
            df.to_parquet(parquet_file, index=False)
            logger.info(f"✅ Saved Parquet: {parquet_file}")
        except Exception as e:
            logger.warning(f"Could not save Parquet file: {e}")
            parquet_file = None
        
        # Save metadata
        metadata = {
            "collection_time": datetime.datetime.now().isoformat(),
            "data_points": len(df),
            "features": len(df.columns),
            "time_range": {
                "start": str(df['timestamp'].min()),
                "end": str(df['timestamp'].max())
            },
            "metrics_collected": [col for col in df.columns if not col.startswith(('timestamp', 'hour', 'day_of_week'))],
            "config": {
                "prometheus_url": self.config.url,
                "namespace": self.config.namespace,
                "step_seconds": self.config.step_seconds,
                "days_back": self.config.days_back
            }
        }
        
        metadata_file = f"ml_data/{base_filename}_{timestamp}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info(f"✅ Saved metadata: {metadata_file}")
        
        # Data quality report
        self.generate_data_quality_report(df, f"ml_data/{base_filename}_{timestamp}_quality_report.txt")
        
        return csv_file, parquet_file, metadata_file

    def generate_data_quality_report(self, df: pd.DataFrame, filename: str):
        """Generate data quality report"""
        with open(filename, 'w') as f:
            f.write("=== DATA QUALITY REPORT ===\n\n")
            f.write(f"Dataset Shape: {df.shape}\n")
            f.write(f"Time Range: {df['timestamp'].min()} to {df['timestamp'].max()}\n")
            f.write(f"Duration: {df['timestamp'].max() - df['timestamp'].min()}\n\n")
            
            f.write("=== MISSING DATA ===\n")
            missing = df.isnull().sum()
            missing_pct = (missing / len(df)) * 100
            for col, count in missing.items():
                if count > 0:
                    f.write(f"{col}: {count} ({missing_pct[col]:.1f}%)\n")
            
            f.write("\n=== BASIC STATISTICS ===\n")
            f.write(str(df.describe()))
            
        logger.info(f"✅ Generated quality report: {filename}")

def main():
    """Main execution function"""
    print("🚀 Enhanced Prometheus Data Collector for Predictive Autoscaling")
    print("=" * 70)
    
    # Configuration
    config = PrometheusConfig(
        url="https://prometheus.hamzakalech.com",
        namespace="hamzadevops",
        step_seconds=30,  # 30-second resolution for detailed ML training
        days_back=1,  # Collect last 24 hours (adjust based on your load test duration)
        verify_ssl=False  # Try without SSL verification first
    )
    
    # Calculate time range
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=config.days_back)
    
    print(f"📊 Collection Config:")
    print(f"   • Prometheus: {config.url}")
    print(f"   • Namespace: {config.namespace}")
    print(f"   • Time Range: {start_time} to {end_time}")
    print(f"   • Resolution: {config.step_seconds} seconds")
    print(f"   • Expected Data Points: ~{int((end_time - start_time).total_seconds() / config.step_seconds)}")
    print()
    
    # Initialize collector
    collector = PrometheusCollector(config)
    
    try:
        # Collect metrics
        print("🔍 Starting data collection...")
        df = collector.collect_all_metrics(start_time, end_time)
        
        if df.empty:
            logger.error("❌ No data collected! Check Prometheus connectivity and queries.")
            return
        
        # Add ML features
        df = collector.add_derived_features(df)
        
        # Save data
        print("💾 Saving data for ML training...")
        files = collector.save_data(df)
        
        print("\n🎉 Data Collection Complete!")
        print(f"   • Collected {len(df)} data points")
        print(f"   • Features: {len(df.columns)}")
        print(f"   • Files saved in ml_data/ directory")
        print("\n📈 Ready for ML model training!")
        
        # Display sample data
        print("\n📋 Sample Data Preview:")
        print(df.head())
        
    except Exception as e:
        logger.error(f"❌ Collection failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
