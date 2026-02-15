FROM apache/airflow:3.1.7

# Install Python dependencies needed by DAGs
COPY infra/docker/airflow.requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Ensure English locale is available
USER root
RUN apt-get update && apt-get install -y locales \
    && locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Switch back to airflow user
USER airflow

