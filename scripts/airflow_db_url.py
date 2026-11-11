"""Print metadata connection URL only for Airflow's _CMD configuration reader."""

import os
import sys
from urllib.parse import quote

if __name__ == "__main__":
    password = quote(os.environ["AIRFLOW_DB_PASSWORD"], safe="")
    sys.stdout.write(f"postgresql+psycopg2://airflow_meta:{password}@postgres:5432/airflow_meta")
