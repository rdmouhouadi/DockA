from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from ingestion.pipelines.purge_expired import purge_expired

# ---------------------------------------------------------------------------
# Temporary uploads — purge everything past its expiry
#
# Runs every 15 minutes. Search already hides expired documents
# (expires_at filter in /search); this job deletes them for good from
# Elasticsearch, PostgreSQL (incl. chunks) and kept files.
#
# is_paused_upon_creation=False: the stack pauses new DAGs by default
# (AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION), but a retention promise
# must not depend on someone remembering to unpause a DAG.
# ---------------------------------------------------------------------------


def run_purge():
    summary = purge_expired()
    print("Purge summary:", summary)


with DAG(
    dag_id="docka_purge_expired",
    description="Delete temporary uploads whose retention has passed",
    start_date=datetime(2025, 1, 1),
    schedule="*/15 * * * *",
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    tags=["docka", "retention"],
) as dag:

    purge_expired_documents = PythonOperator(
        task_id="purge_expired_documents",
        python_callable=run_purge,
    )
