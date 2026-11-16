select source_namespace, product_key,
       min(description) as sample_description,
       count(distinct description) as observed_description_count
from {{ ref('fact_invoice_line') }} group by 1,2

