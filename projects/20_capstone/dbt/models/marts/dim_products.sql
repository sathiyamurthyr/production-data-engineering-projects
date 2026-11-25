-- Product Dimension Table (Marts)
-- Explanation: Exposes the latest catalog products and stock quantities

with products as (
    select * from {{ ref('stg_products') }}
)

select
    product_id,
    product_name,
    category,
    price,
    stock_quantity,
    created_at,
    updated_at
from products
