/*
  ==============================================================================
  dbt Singular Test: assert_orders_have_customers.sql
  ==============================================================================
  
  EXPLANATION:
    Asserts referential integrity between fct_orders and dim_customers.
    Returns any order records whose customer_id does NOT exist in dim_customers.
    
  PASS CONDITION:
    0 rows returned.
  ==============================================================================
*/

select
    orders.order_id,
    orders.customer_id
from {{ ref('fct_orders') }} as orders
left join {{ ref('dim_customers') }} as customers
    on orders.customer_id = customers.customer_id
where customers.customer_id is null
