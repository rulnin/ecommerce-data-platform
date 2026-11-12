"""Daily simulated historical loads; stock always reflects its latest committed source cursor."""

from datetime import timedelta

import pendulum
from airflow.sdk import DAG, get_current_context, task


@task
def run_step(step):
    from src.orchestration.tasks import execute_step, parse_batch_day

    context = get_current_context()
    config = context["dag_run"].conf or {}
    day = parse_batch_day(config, context.get("data_interval_start"))
    return execute_step(
        step, day, context["run_id"], context["ti"].try_number, config.get("failure_mode", "none")
    )


with DAG(
    "ecommerce_pipeline",
    schedule="@daily",
    start_date=pendulum.datetime(2016, 9, 4, tz="UTC"),
    end_date=pendulum.datetime(2018, 10, 18, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=2,
    dagrun_timeout=timedelta(minutes=40),
    default_args={
        "retries": 2,
        "retry_delay": timedelta(seconds=10),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=1),
        "execution_timeout": timedelta(minutes=5),
    },
    tags=["olist", "local", "simulated-arrivals"],
    is_paused_upon_creation=True,
):
    csv = run_step.override(task_id="csv")("csv")
    fx = run_step.override(task_id="fx")("fx")
    inventory = run_step.override(task_id="inventory")("inventory")
    summary = run_step.override(task_id="transform")("transform")
    checks = run_step.override(task_id="quality")("quality")
    publish = run_step.override(task_id="publish", execution_timeout=timedelta(minutes=15))(
        "publish"
    )
    analytics = run_step.override(task_id="analytics")("analytics")
    [csv, fx, inventory] >> summary >> checks >> publish >> analytics
