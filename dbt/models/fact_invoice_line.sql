{{ config(materialized='incremental', unique_key='source_row_id', incremental_strategy='delete+insert',
          indexes=[{'columns':['source_row_id'],'unique':true},{'columns':['business_date']}]) }}
with typed as (
 select *,
   case when nullif(invoice,'') is null or nullif(stock_code,'') is null
          or event_local_time is null or quantity is null or quantity <> trunc(quantity)
          or unit_price is null then 'invalid_field'
        when upper(invoice) like 'C%' or quantity < 0 then 'cancellation_or_correction'
        when stock_code !~ '^[0-9]{5}[A-Za-z]?$' then 'non_merchandise_code'
        when quantity = 0 then 'zero_quantity'
        when unit_price <= 0 then 'non_positive_price'
        else 'eligible_sale' end as classification_reason
 from {{ ref('stg_invoice_line') }}
)
select source_namespace, data_kind, dataset_sha256, source_row_id, sheet, row_number,
       invoice as invoice_id, stock_code as product_key,
       coalesce(nullif(customer_text,''),'__UNKNOWN__') as customer_key,
       description, country, event_local_time, event_local_time::date as business_date,
       quantity, unit_price, quantity * unit_price as signed_amount,
       'GBP'::text as currency,
       case classification_reason when 'invalid_field' then 'quarantine'
         when 'cancellation_or_correction' then 'cancellation'
         when 'eligible_sale' then 'sale' else 'adjustment' end as record_class,
       classification_reason
from typed

