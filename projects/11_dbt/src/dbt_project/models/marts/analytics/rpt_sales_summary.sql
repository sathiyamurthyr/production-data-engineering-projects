/*
  ==============================================================================
  dbt Model: rpt_sales_summary.sql
  Layer: Marts (Analytics / Reporting)
  Materialization: Table
  ==============================================================================
  
  EXPLANATION:
    Executive-level daily and monthly sales performance summary rollup.
    Calculates total orders, active purchasing customers, gross revenue,
    tax, discounts, net revenue, and overall gross profit margin.
    
  BUSINESS USE CASE:
    Powers executive dashboards, daily business health monitoring, and financial
    reporting for leadership.
    
  EXPECTED OUTPUT:
    Columns: report_date, year_month, total_orders, active_customers_count,
             gross_revenue, total_tax, total_discounts, net_revenue,
             total_gross_margin, avg_order_value
  ==============================================================================
*/

with orders as (

    select * from {{ ref('fct_orders') }}

),

daily_rollup as (

    select
        cast(order_date as date) as report_date,
        to_char(order_date, 'YYYY-MM') as year_month,

        count(order_id) as total_orders,
        count(distinct customer_id) as active_customers_count,

        sum(subtotal_amount) as gross_revenue,
        sum(tax_amount) as total_tax,
        sum(discount_amount) as total_discounts,
        sum(total_amount) as net_revenue,
        sum(gross_margin) as total_gross_margin,
        avg(total_amount) as avg_order_value

    from orders
    where order_status != 'cancelled'
    group by 1, 2

)

select * from daily_rollup
order by report_date desc
