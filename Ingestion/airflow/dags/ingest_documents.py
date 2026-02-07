from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from Ingestion.pipelines.ingest_folder import ingest_folder


# ---- Configuration (can later move to Airflow Variables) ----
DATA_ROOT = Path("/opt/airflow/data/samples/CrystalcloudDoc")


def run_ingestion():
    result = ingest_folder(DATA_ROOT)
    print("Ingestion summary:", result)


with DAG(
    dag_id="docka_ingest_documents",
    description="Ingest documents into DocKA knowledge base",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,  # manual trigger for now
    catchup=False,
    tags=["docka", "ingestion"],
) as dag:

    ingest_task = PythonOperator(
        task_id="ingest_documents",
        python_callable=run_ingestion,
    )
