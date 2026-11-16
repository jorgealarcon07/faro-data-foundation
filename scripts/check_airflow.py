"""Run inside the Linux Airflow image; a source compile alone is not a DAG import test."""

from airflow.models import DagBag

bag = DagBag(dag_folder="/app/dags", include_examples=False)
if bag.import_errors:
    raise SystemExit(str(bag.import_errors))
dag = bag.get_dag("faro_data_close")
assert dag is not None
assert set(dag.task_ids) == {"prepare", "load", "build", "validate", "publish"}
assert dag.get_task("validate").downstream_task_ids == {"publish"}
assert dag.max_active_runs == 1
print("Airflow DAG imported; 5 phases and dependencies checked")
