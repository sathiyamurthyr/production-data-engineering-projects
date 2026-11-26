-- Customer Dimension Table (Marts)
-- Explanation: Standardises customer profile attributes and appends activity flag

with customers as (
    select * from {{ ref('stg_customers') }}
)

select
    customer_id,
    first_name,
    last_name,
    email,
    phone,
    country,
    segment,
    created_at,
    updated_at,
    true as is_active
from customers
