-- Staging model for Products reading from Silver Parquet layer
-- Explanation: Standardises product dimensions and pricing data types

with raw_products as (
    select * from read_parquet('d:/engineering-projects/production-data-engineering-projects/projects/20_capstone/data/silver/products/*.parquet')
)

select
    cast(product_id as string) as product_id,
    cast(product_name as string) as product_name,
    cast(category as string) as category,
    cast(price as double) as price,
    cast(stock_quantity as integer) as stock_quantity,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at
from raw_products
