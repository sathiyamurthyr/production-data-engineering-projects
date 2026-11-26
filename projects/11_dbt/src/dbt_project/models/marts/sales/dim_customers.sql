/*
  ==============================================================================
  dbt Model: dim_customers.sql
  Layer: Marts (Sales)
  Materialization: Table
  ==============================================================================
  
  EXPLANATION:
    Customer dimension table enriched with purchasing behavior, tenure flags,
    country lookup metadata, and customer segmentation tiers (VIP, Active, Low Value).
    
  BUSINESS USE CASE:
    Serves as the primary dimension for customer segmentation, cohort analytics,
    and CRM audience targeting.
    
  EXPECTED OUTPUT:
    Columns: customer_key, customer_id, full_name, email, country_name, region,
             signup_channel, first_order_date, most_recent_order_date, total_orders,
             total_spend, avg_order_value, customer_segment, created_at
  ==============================================================================
*/

with customers as (

    select * from {{ ref('stg_customers') }}

),

customer_orders as (

    select * from {{ ref('int_customer_orders') }}

),

country_codes as (

    select * from {{ ref('country_codes') }}

),

final as (

    select
        customers.customer_key,
        customers.customer_id,
        customers.first_name,
        customers.last_name,
        customers.full_name,
        customers.email,
        customers.country_code,
        coalesce(country_codes.country_name, 'Unknown') as country_name,
        coalesce(country_codes.region, 'Global') as region,
        customers.signup_channel,

        orders.first_order_date,
        orders.most_recent_order_date,
        orders.total_orders,
        orders.completed_orders_count,
        orders.total_spend,
        orders.avg_order_value,

        -- Customer Segmentation Rationale
        case
            when orders.total_spend >= 1000.00 then 'VIP Customer'
            when orders.total_spend >= 250.00 then 'Regular Customer'
            when orders.total_orders > 0 then 'Low-Value Customer'
            else 'Prospect (No Orders)'
        end as customer_segment,

        customers.created_at

    from customers
    left join customer_orders as orders
        on customers.customer_id = orders.customer_id
    left join country_codes
        on customers.country_code = country_codes.country_code

)

select * from final
