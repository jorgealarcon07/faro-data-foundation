select f.source_row_id from {{ ref('fact_invoice_line') }} f
left join {{ ref('dim_customer') }} d using(source_namespace,customer_key)
where d.customer_key is null

