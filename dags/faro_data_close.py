"""Historical batch replay. Configure input/interval with DAG run conf; no work at parse time."""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

with DAG(
    dag_id="faro_data_close",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=15)},
    tags=["faro", "project-01", "historical-replay"],
    doc_md="Five phases with an isolated candidate. Manual historical intervals [start,end); original hours have no timezone.",
) as dag:
    tasks = []
    for stage in ["prepare", "load", "build", "validate", "publish"]:
        tasks.append(
            BashOperator(
                task_id=stage,
                bash_command="/opt/faro/bin/python -m faro_foundation.workflow " + stage,
                append_env=True,
                env={
                    "FARO_WORKFLOW_KEY": "{{ run_id }}",
                    "FARO_INPUT_FILE": "{{ dag_run.conf.get('input_file','') }}",
                    "FARO_DATA_KIND": "{{ dag_run.conf.get('data_kind','public_real_historical') }}",
                    "FARO_INTERVAL_START": "{{ dag_run.conf.get('start','') }}",
                    "FARO_INTERVAL_END": "{{ dag_run.conf.get('end','') }}",
                },
            )
        )
    for upstream, downstream in zip(tasks, tasks[1:], strict=False):
        upstream >> downstream
