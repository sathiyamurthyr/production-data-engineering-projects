/*
  ==============================================================================
  dbt Model: int_order_items.sql
  Layer: Intermediate
  Materialization: View
  ==============================================================================
  
  EXPLANATION:
    Enriches order line-items with product pricing, category info, and margins.
    Calculates line-item gross revenue, discount subtractions, and net profit margins.
    
  BUSINESS USE CASE:
    Enables basket analysis, product margin profitability reporting, and order-level
    cost structure aggregations.
    
  EXPECTED OUTPUT:
    Columns: order_item_key, order_id, product_id, quantity, unit_price,
             cost_price, gross_amount, discount_amount, net_amount, gross_margin
  ==============================================================================
*/

with orders as (

    select * from {{ ref('stg_orders') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

-- Simulating raw order items source inside intermediate join
order_items_raw as (

    select
        orders.order_id,
        products.product_id,
        cast(1 + (abs(hashtext(concat(orders.order_id, products.product_id))) % 5) as integer) as quantity,
        products.unit_price,
        products.cost_price,
        cast(orders.discount_amount / 2 as numeric(16, 2)) as item_discount

    from orders
    cross join products
    -- Subsampling to simulate distinct order line items
    where (abs(hashtext(concat(orders.order_id, products.product_id))) % 3) = 0

),

calculated as (

    select
        {{ dbt_utils.generate_surrogate_key(['order_id', 'product_id']) }} as order_item_key,
        order_id,
        product_id,
        quantity,
        unit_price,
        cost_price,
        cast(quantity * unit_price as numeric(16, 2)) as gross_amount,
        cast(item_discount as numeric(16, 2)) as discount_amount,
        cast((quantity * unit_price) - item_discount as numeric(16, 2)) as net_amount,
        cast(((quantity * unit_price) - item_discount) - (quantity * cost_price) as numeric(16, 2)) as gross_margin

    from order_items_raw

)

select * from calculated
