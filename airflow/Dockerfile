FROM python:3.14.4-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -o /tmp/microsoft.deb \
    && dpkg -i /tmp/microsoft.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18=18.7.1.1-1 \
    && rm -rf /var/lib/apt/lists/* /tmp/microsoft.deb
COPY airflow/constraints/constraints-3.14.txt /tmp/airflow-constraints.txt
COPY airflow/requirements.txt /tmp/project-requirements.txt
RUN python -m pip install --no-cache-dir pip==26.3 \
    && pip install --no-cache-dir -r /tmp/project-requirements.txt --constraint /tmp/airflow-constraints.txt \
    && pip check
# Keep warehouse dependencies out of Airflow's constrained environment.
COPY requirements.txt requirements-dbt.txt /tmp/warehouse/
RUN python -m venv /opt/warehouse \
    && /opt/warehouse/bin/pip install --no-cache-dir -r /tmp/warehouse/requirements-dbt.txt \
    && /opt/warehouse/bin/pip check
# Airflow metadata uses the SQLAlchemy psycopg2 dialect; ingestion uses psycopg3.
RUN pip install --no-cache-dir psycopg2-binary==2.9.13 --constraint /tmp/airflow-constraints.txt
RUN useradd --uid 50000 --gid 0 --home-dir /opt/airflow --create-home airflow \
    && mkdir -p /opt/airflow/logs /opt/airflow/dags \
    && chown -R airflow:root /opt/airflow
COPY --chown=airflow:root src /opt/project/src
COPY --chown=airflow:root sql /opt/project/sql
COPY --chown=airflow:root scripts /opt/project/scripts
COPY --chown=airflow:root dbt /opt/project/dbt
COPY --chown=airflow:root config /opt/project/config
RUN mkdir -p /opt/project/docs && chown -R airflow:root /opt/project/docs
ENV PYTHONPATH=/opt/project AIRFLOW_HOME=/opt/airflow
USER airflow
WORKDIR /opt/project
ENTRYPOINT ["airflow"]
