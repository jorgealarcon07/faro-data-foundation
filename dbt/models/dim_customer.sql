select source_namespace, customer_key,
       customer_key = '__UNKNOWN__' as is_unknown,
       count(distinct country) as observed_country_count
from {{ ref('fact_invoice_line') }} group by 1,2

