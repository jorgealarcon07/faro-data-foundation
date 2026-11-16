select source_namespace, data_kind, currency, business_date,
       count(*) as input_rows,
       count(*) filter(where customer_key='__UNKNOWN__') as unknown_customer_rows,
       count(*) filter(where record_class='quarantine') as quarantine_rows,
       count(*) filter(where record_class='adjustment') as adjustment_rows,
       count(*) filter(where signed_amount is null) as unknown_amount_rows,
       sum(signed_amount) filter(where record_class='quarantine') as quarantined_known_amount,
       case when count(*) filter(where record_class='quarantine' or customer_key='__UNKNOWN__')>0
            then 'provisional' else 'ready' end as publication_status
from {{ ref('fact_invoice_line') }} group by 1,2,3,4

