select source_namespace, data_kind, currency, business_date, record_class,
       count(*) as row_count, sum(signed_amount) as signed_amount,
       count(*) filter(where signed_amount is null) as unknown_amount_rows
from {{ ref('fact_invoice_line') }} group by 1,2,3,4,5

