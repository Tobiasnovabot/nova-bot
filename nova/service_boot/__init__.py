{
  "title": "NovaX Ops",
  "schemaVersion": 38,
  "version": 1,
  "editable": True,
  "time": { "from": "now-6h", "to": "now" },
  "templating": {
    "list": [
      {
        "name": "ds",
        "type": "datasource",
        "label": "Prometheus",
        "query": "prometheus",
        "current": { "text": "Prometheus", "value": "Prometheus" }
      }
    ]
  },
  "panels": [
    {
      "type": "stat",
      "title": "Exporter up (novax_exporter)",
      "gridPos": { "x": 0, "y": 0, "w": 6, "h": 4 },
      "datasource": { "type": "prometheus", "uid": "$ds" },
      "targets": [{ "expr": "avg_over_time(up{job=\"novax_exporter\"}[5m])", "legendFormat": "up" }],
      "options": {
        "reduceOptions": {"calcs": ["lastNotNull"]},
        "thresholds": { "mode": "absolute", "steps": [{ "color": "red", "value": 0 }, { "color": "green", "value": 0.99 }] }
      }
    },
    {
      "type": "stat",
      "title": "Heartbeats (15m)",
      "gridPos": { "x": 6, "y": 0, "w": 6, "h": 4 },
      "datasource": { "type": "prometheus", "uid": "$ds" },
      "targets": [{ "expr": "count_over_time(novax_engine_heartbeat_total[15m])" }],
      "options": { "reduceOptions": {"calcs": ["lastNotNull"]} }
    },
    {
      "type": "timeseries",
      "title": "Heartbeat rate (/min)",
      "gridPos": { "x": 0, "y": 4, "w": 12, "h": 8 },
      "datasource": { "type": "prometheus", "uid": "$ds" },
      "targets": [{ "expr": "rate(novax_engine_heartbeat_total[5m])" }],
      "fieldConfig": { "defaults": { "unit": "opsmin" } }
    },
    {
      "type": "table",
      "title": "Active Alerts",
      "gridPos": { "x": 0, "y": 12, "w": 12, "h": 8 },
      "datasource": { "type": "prometheus", "uid": "$ds" },
      "targets": [{ "expr": "ALERTS{alertstate=\"firing\"}" }],
      "options": { "showHeader": True }
    }
  ]
}
