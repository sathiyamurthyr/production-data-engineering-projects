/*
  ==============================================================================
  dbt Analysis: revenue_reconciliation.sql
  ==============================================================================
  
  EXPLANATION:
    Ad-hoc analytical query used by finance and analytics engineers to verify
    100% financial revenue reconciliation across all 3 dbt modeling layers:
    1. Staging (`stg_orders`)
    2. Fact Mart (`fct_orders`)
    3. Executive Summary (`rpt_sales_summary`)
    
  USAGE:
    Compiled via `dbt compile`. Results can be audited in database client.
  ==============================================================================
*/

with stg_totals as (

    select
        '1_staging' as layer,
        count(order_id) as total_order_count,
        sum(total_amount) as total_revenue
    from {{ ref('stg_orders') }}
    where order_status != 'cancelled'

),

fct_totals as (

    select
        '2_fct_orders' as layer,
        count(order_id) as total_order_count,
        sum(total_amount) as total_revenue
    from {{ ref('fct_orders') }}
    where order_status != 'cancelled'

),

rpt_totals as (

    select
        '3_rpt_sales_summary' as layer,
        sum(total_orders) as total_order_count,
        sum(net_revenue) as total_revenue
    from {{ ref('rpt_sales_summary') }}

),

combined as (

    select * from stg_totals
    union all
    select * from fct_totals
    union all
    select * from rpt_totals

)

select
    layer,
    total_order_count,
    total_revenue,
    total_revenue - lag(total_revenue) over (order by layer) as revenue_variance_from_prior_layer
from combined
