-- Staging model for Orders reading from Silver Parquet layer
-- Explanation: Casts types, cleans fields, and prepares for Fact transformation

with raw_orders as (
    select * from read_parquet('d:/engineering-projects/production-data-engineering-projects/projects/20_capstone/data/silver/orders/*.parquet')
)

select
    cast(order_id as string) as order_id,
    cast(customer_id as string) as customer_id,
    cast(product_id as string) as product_id,
    cast(quantity as integer) as quantity,
    cast(total_amount as double) as total_amount,
    cast(order_status as string) as order_status,
    cast(payment_method as string) as payment_method,
    cast(order_date as timestamp) as order_date,
    cast(shipping_address as string) as shipping_address
from raw_orders
