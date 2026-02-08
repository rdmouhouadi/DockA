FROM apache/airflow:2.8.1

# Install Python dependencies needed by DAGs
COPY infra/docker/airflow.requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
