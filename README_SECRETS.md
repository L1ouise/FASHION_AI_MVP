# Secrets Configuration — Fashion AI

This project runs on **Streamlit Community Cloud**. Secrets are managed
through the Streamlit Cloud dashboard (Settings > Secrets) using TOML
format.

## Required secrets (`.streamlit/secrets.toml` for local dev)

```toml
QDRANT_URL     = "https://9230c799-43b2-4666-980d-f32cc98b2754.europe-west3-0.gcp.cloud.qdrant.io"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Optional secrets (Airflow integration)

```toml
AIRFLOW_BASE_URL = "http://<public-ip-or-ngrok-url>:8080"
AIRFLOW_USER     = "admin"
AIRFLOW_PASSWORD = "admin"
```

If `AIRFLOW_BASE_URL` is empty or absent the Pipeline page will display
an informational message instead of crashing.

## Exposing Airflow from a laptop

Airflow runs on a friend's machine. To make it reachable from
Streamlit Cloud:

```bash
ngrok http 8080
```

Then paste the generated `https://xxxx.ngrok-free.app` URL as
`AIRFLOW_BASE_URL` in Streamlit secrets.
