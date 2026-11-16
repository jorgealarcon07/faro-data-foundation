select * from {{ ref('fact_invoice_line') }}
where record_class='sale' and (quantity<=0 or unit_price<=0 or event_local_time is null)

