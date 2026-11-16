select 1 as failed from {{ ref('mart_quality') }}
having sum(input_rows) <> (select count(*) from {{ ref('fact_invoice_line') }})
