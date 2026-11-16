{{ config(materialized='view') }}
select r.*, '{{ var("namespace") }}'::text as source_namespace,
       '{{ var("data_kind") }}'::text as data_kind
from faro.source_rows r
where dataset_sha256 = '{{ var("dataset_sha256") }}'
{% if var('start_date', '') %}
  and event_local_time >= '{{ var("start_date") }}'::date
  and event_local_time < '{{ var("end_date") }}'::date
{% endif %}

