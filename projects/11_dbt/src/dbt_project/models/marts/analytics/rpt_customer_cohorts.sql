/*
  ==============================================================================
  dbt Model: rpt_customer_cohorts.sql
  Layer: Marts (Analytics / Reporting)
  Materialization: Table
  ==============================================================================
  
  EXPLANATION:
    Customer acquisition cohort retention and LTV matrix.
    Groups customers by their initial sign-up / first order month, tracking
    order activity and cumulative revenue across subsequent activity months.
    
  BUSINESS USE CASE:
    Enables growth, marketing, and product analytics teams to measure customer
    retention rates and lifetime value (LTV) dynamics over time.
    
  EXPECTED OUTPUT:
    Columns: cohort_month, activity_month, month_number, cohort_size,
             active_retained_customers, total_cohort_revenue, cumulative_ltv
  ==============================================================================
*/

with customers as (

    select * from {{ ref('dim_customers') }}

),

orders as (

    select * from {{ ref('fct_orders') }}

),

customer_cohort_base as (

    select
        customers.customer_id,
        to_char(coalesce(customers.first_order_date, customers.created_at), 'YYYY-MM') as cohort_month,
        to_char(orders.order_date, 'YYYY-MM') as activity_month,
        orders.total_amount

    from customers
    inner join orders
        on customers.customer_id = orders.customer_id
    where orders.order_status != 'cancelled'

),

cohort_sizes as (

    select
        to_char(coalesce(first_order_date, created_at), 'YYYY-MM') as cohort_month,
        count(distinct customer_id) as cohort_size
    from customers
    where first_order_date is not null
    group by 1

),

monthly_cohort_activity as (

    select
        base.cohort_month,
        base.activity_month,
        count(distinct base.customer_id) as active_retained_customers,
        sum(base.total_amount) as total_cohort_revenue

    from customer_cohort_base as base
    group by 1, 2

),

final as (

    select
        act.cohort_month,
        act.activity_month,
        sizes.cohort_size,
        act.active_retained_customers,
        cast(act.active_retained_customers as numeric) / nullif(sizes.cohort_size, 0) as retention_rate,
        act.total_cohort_revenue,
        cast(act.total_cohort_revenue as numeric) / nullif(sizes.cohort_size, 0) as average_revenue_per_user

    from monthly_cohort_activity as act
    left join cohort_sizes as sizes
        on act.cohort_month = sizes.cohort_month

)

select * from final
order by cohort_month desc, activity_month asc
