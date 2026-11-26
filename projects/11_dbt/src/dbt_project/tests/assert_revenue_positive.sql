/*
  ==============================================================================
  dbt Singular Test: assert_revenue_positive.sql
  ==============================================================================
  
  EXPLANATION:
    Asserts that total financial amounts in fct_orders are non-negative.
    Returns order records where total_amount or subtotal_amount < 0.
    
  PASS CONDITION:
    0 rows returned.
  ==============================================================================
*/

select
    order_id,
    subtotal_amount,
    total_amount
from {{ ref('fct_orders') }}
where total_amount < 0
   or subtotal_amount < 0
