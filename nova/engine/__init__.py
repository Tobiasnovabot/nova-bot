# Auto-start Prometheus exporter as soon as nova.engine is imported
import os
try:
# removed legacy metrics.start
    if not os.environ.get("NOVAX_METRICS_STARTED"):
        os.environ["NOVAX_METRICS_STARTED"] = "1"
# removed legacy metrics.start call
except Exception as e:
    print(f"[metrics] failed to start: {e}", flush=True)
