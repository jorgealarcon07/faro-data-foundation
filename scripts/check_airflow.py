"""Run inside the Linux Airflow image; a source compile alone is not a DAG import test."""

from itertools import pairwise

from airflow.dag_processing.dagbag import DagBag

bag = DagBag(dag_folder="/app/dags")
if bag.import_errors:
    raise SystemExit(str(bag.import_errors))
dag = bag.dags["faro_data_close"]
stages = ("prepare", "load", "build", "validate", "publish")
assert set(dag.task_ids) == set(stages)
for stage, successor in pairwise(stages):
    assert dag.get_task(stage).downstream_task_ids == {successor}
assert not dag.get_task(stages[-1]).downstream_task_ids
assert dag.max_active_runs == 1
print("Airflow DAG imported; 5 phases and dependencies checked")
