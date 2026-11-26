-- Staging model for Customers reading from Silver Parquet layer
-- Explanation: Standardises customer demographic schemas

with raw_customers as (
    select * from read_parquet('d:/engineering-projects/production-data-engineering-projects/projects/20_capstone/data/silver/customers/*.parquet')
)

select
    cast(customer_id as string) as customer_id,
    cast(first_name as string) as first_name,
    cast(last_name as string) as last_name,
    cast(email as string) as email,
    cast(phone as string) as phone,
    cast(country as string) as country,
    cast(segment as string) as segment,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at
from raw_customers
