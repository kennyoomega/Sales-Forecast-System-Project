# src/bq_client.py
from google.cloud import bigquery
from google.oauth2 import service_account
import os

PROJECT_ID = os.getenv('BQ_PROJECT_ID', 'peppy-ward-497115-k8')
DATASET    = os.getenv('BQ_DATASET', 'analytics')
KEY_FILE   = os.getenv('BQ_KEY_FILE', '')

def get_client() -> bigquery.Client:
    if KEY_FILE and os.path.exists(KEY_FILE):
        creds = service_account.Credentials.from_service_account_file(KEY_FILE)
        return bigquery.Client(project=PROJECT_ID, credentials=creds)
    return bigquery.Client(project=PROJECT_ID)

def query_mart(model_name: str, limit: int = 1000) -> list[dict]:
    client = get_client()
    query = f'SELECT * FROM `{PROJECT_ID}.{DATASET}.{model_name}` LIMIT {limit}'
    return [dict(row) for row in client.query(query).result()]