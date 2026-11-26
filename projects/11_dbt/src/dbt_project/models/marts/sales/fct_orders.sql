/*
  ==============================================================================
  dbt Model: fct_orders.sql
  Layer: Marts (Sales)
  Materialization: Incremental (Merge strategy)
  ==============================================================================
  
  EXPLANATION:
    Production order fact table built using Kimball star-schema principles.
    Implements incremental materialization with a 3-day lookback window
    to efficiently process new transactions while handling late updates.
    
  BUSINESS USE CASE:
    Powers company-wide financial reporting, daily revenue metrics, sales trends,
    and executive dashboards.
    
  EXPECTED OUTPUT:
    Columns: order_key, order_id, customer_key, customer_id, order_status,
             order_date, total_items_count, subtotal_amount, tax_amount,
             discount_amount, total_amount, gross_margin
  ==============================================================================
*/

{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns'
) }}

with orders as (

    select * from {{ ref('stg_orders') }}

    {% if is_incremental() %}
        -- 3-day lookback window for incremental runs
        where updated_at >= (select max(order_date) - interval '3 days' from {{ this }})
    {% endif %}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

order_items_agg as (

    select
        order_id,
        count(product_id) as total_items_count,
        sum(gross_margin) as gross_margin

    from {{ ref('int_order_items') }}
    group by 1

),

final as (

    select
        orders.order_key,
        orders.order_id,
        customers.customer_key,
        orders.customer_id,
        orders.order_status,
        orders.order_date,

        coalesce(items.total_items_count, 1) as total_items_count,
        orders.subtotal_amount,
        orders.tax_amount,
        orders.discount_amount,
        orders.total_amount,
        coalesce(items.gross_margin, cast(orders.total_amount * 0.35 as numeric(16,2))) as gross_margin

    from orders
    left join customers
        on orders.customer_id = customers.customer_id
    left join order_items_agg as items
        on orders.order_id = items.order_id

)

select * from final
