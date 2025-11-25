import requests
import pandas as pd
import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Configuration ===
PROMETHEUS_URL = "https://prometheus.hamzakalech.com"
NAMESPACE = "hamzadevops"
STEP = 60  # in seconds
DAYS = 7

# === Time range (UTC) ===
end_time = datetime.datetime.utcnow()
start_time = end_time - datetime.timedelta(days=DAYS)
start_unix = int(start_time.timestamp())
end_unix = int(end_time.timestamp())

# === PromQL queries (limited to worker nodes) ===
label_filter = f"namespace='{NAMESPACE}', container!='', node_label_agentpool='worker'"
queries = {
    "cpu_usage": f"rate(container_cpu_usage_seconds_total{{{label_filter}}}[2m])",
    "memory_usage": f"container_memory_usage_bytes{{{label_filter}}}",
    "network_rx": f"rate(container_network_receive_bytes_total{{{label_filter}}}[2m])",
    "network_tx": f"rate(container_network_transmit_bytes_total{{{label_filter}}}[2m])",
    "pod_count": f"count(kube_pod_status_phase{{namespace='{NAMESPACE}',phase='Running'}})",
    "node_count": "count(kube_node_status_condition{condition='Ready',status='true',node_label_agentpool='worker'})",
    "restart_rate": f"rate(kube_pod_container_status_restarts_total{{{label_filter}}}[5m])"
}

def query_prometheus(query, start, end, step):
    url = f"{PROMETHEUS_URL}/prometheus/api/v1/query_range"
    params = {"query": query, "start": start, "end": end, "step": step}
    response = requests.get(url, params=params, verify=True)
    print(f"🔍 Query: {query[:50]}... → Status {response.status_code}")
    if not response.ok:
        print("❌ Error:", response.text[:300])
    return response.json()

def extract_aggregate_series(prom_data, label, method="sum"):
    rows = []
    for pod in prom_data.get("data", {}).get("result", []):
        for point in pod["values"]:
            ts = datetime.datetime.fromtimestamp(float(point[0]))
            value = float(point[1])
            rows.append({"timestamp": ts, label: value})
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()
    return df.groupby("timestamp").agg({label: method}).reset_index()

def extract_single_series(prom_data, label):
    values = prom_data.get("data", {}).get("result", [])
    if not values:
        return pd.DataFrame()
    series = values[0]["values"]
    return pd.DataFrame([(datetime.datetime.fromtimestamp(float(ts)), float(val)) for ts, val in series], columns=["timestamp", label])

# === Query all metrics
raw = {k: query_prometheus(v, start_unix, end_unix, STEP) for k, v in queries.items()}

# === Convert to DataFrames
df_cpu = extract_aggregate_series(raw["cpu_usage"], "cpu_usage")
df_mem = extract_aggregate_series(raw["memory_usage"], "memory_usage")
df_rx = extract_aggregate_series(raw["network_rx"], "network_rx")
df_tx = extract_aggregate_series(raw["network_tx"], "network_tx")
df_restart = extract_aggregate_series(raw["restart_rate"], "restart_rate")
df_pod = extract_single_series(raw["pod_count"], "pod_count")
df_node = extract_single_series(raw["node_count"], "node_count")

# === Merge all DataFrames
df_full = df_cpu
for df in [df_mem, df_rx, df_tx, df_restart, df_pod, df_node]:
    if not df.empty:
        df_full = df_full.merge(df, on="timestamp", how="left")

# === Save to CSV
df_full.to_csv("prometheus_metrics.csv", index=False)
print("✅ Saved enriched data to prometheus_metrics.csv")
