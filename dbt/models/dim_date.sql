select distinct source_namespace, business_date,
       extract(year from business_date)::int as year,
       extract(month from business_date)::int as month,
       extract(isodow from business_date)::int as iso_weekday
from {{ ref('fact_invoice_line') }} where business_date is not null

