/*
  ==============================================================================
  dbt Model: dim_products.sql
  Layer: Marts (Sales)
  Materialization: Table
  ==============================================================================
  
  EXPLANATION:
    Product dimension model joining product master attributes with catalog seeds
    and sales performance aggregates.
    
  BUSINESS USE CASE:
    Enables merchandising analysis, product category sales performance reporting,
    and profitability evaluation.
    
  EXPECTED OUTPUT:
    Columns: product_key, product_id, product_name, category_name, department,
             unit_price, cost_price, gross_profit_margin, total_units_sold, total_product_revenue
  ==============================================================================
*/

with products as (

    select * from {{ ref('stg_products') }}

),

categories as (

    select * from {{ ref('product_categories') }}

),

order_items as (

    select * from {{ ref('int_order_items') }}

),

product_sales_agg as (

    select
        product_id,
        sum(quantity) as total_units_sold,
        sum(net_amount) as total_product_revenue,
        sum(gross_margin) as total_product_margin

    from order_items
    group by 1

),

final as (

    select
        products.product_key,
        products.product_id,
        products.product_name,
        products.category_id,
        coalesce(categories.category_name, 'Uncategorized') as category_name,
        coalesce(categories.department, 'General') as department,

        products.unit_price,
        products.cost_price,
        cast(products.unit_price - products.cost_price as numeric(16, 2)) as unit_margin,

        coalesce(agg.total_units_sold, 0) as total_units_sold,
        coalesce(agg.total_product_revenue, 0.00) as total_product_revenue,
        coalesce(agg.total_product_margin, 0.00) as total_product_margin,

        products.is_active,
        products.created_at

    from products
    left join categories
        on products.category_id = categories.category_id
    left join product_sales_agg as agg
        on products.product_id = agg.product_id

)

select * from final
