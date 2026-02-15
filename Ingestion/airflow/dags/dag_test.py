from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def test_func():
    print("Hello Airflow!")

with DAG(
    dag_id="test_logging",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    task = PythonOperator(
        task_id="print_hello",
        python_callable=test_func,
    )
