/*
  ==============================================================================
  dbt Model: int_customer_orders.sql
  Layer: Intermediate
  Materialization: View
  ==============================================================================
  
  EXPLANATION:
    Aggregates order transaction metrics at the customer grain.
    Calculates lifetime spending, order frequencies, and tenure boundaries.
    
  BUSINESS USE CASE:
    Feeds dim_customers to enable customer segmentation (VIP, Churned, New),
    Recency-Frequency-Monetary (RFM) scoring, and Cohort LTV modeling.
    
  EXPECTED OUTPUT:
    Columns: customer_id, first_order_date, most_recent_order_date,
             total_orders, total_spend, avg_order_value, completed_orders_count
  ==============================================================================
*/

with customers as (

    select * from {{ ref('stg_customers') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

customer_orders_summary as (

    select
        customer_id,
        min(order_date) as first_order_date,
        max(order_date) as most_recent_order_date,
        count(order_id) as total_orders,
        sum(case when order_status = 'completed' then 1 else 0 end) as completed_orders_count,
        coalesce(sum(case when order_status != 'cancelled' then total_amount else 0 end), 0) as total_spend,
        coalesce(avg(case when order_status != 'cancelled' then total_amount else null end), 0) as avg_order_value

    from orders
    group by 1

),

joined as (

    select
        customers.customer_id,
        customers.customer_key,
        coalesce(summary.first_order_date, null) as first_order_date,
        coalesce(summary.most_recent_order_date, null) as most_recent_order_date,
        coalesce(summary.total_orders, 0) as total_orders,
        coalesce(summary.completed_orders_count, 0) as completed_orders_count,
        coalesce(summary.total_spend, 0.00) as total_spend,
        coalesce(summary.avg_order_value, 0.00) as avg_order_value

    from customers
    left join customer_orders_summary as summary
        on customers.customer_id = summary.customer_id

)

select * from joined
