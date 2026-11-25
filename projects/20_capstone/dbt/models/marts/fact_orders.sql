-- Fact Orders Table (Marts)
-- Explanation: Computes derived business metrics like gross revenue, tax, and net revenue

with orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
)

select
    o.order_id,
    o.customer_id,
    o.product_id,
    cast(strftime(o.order_date, '%Y%m%d') as integer) as order_date_key,
    o.quantity,
    p.price as unit_price,
    round(o.quantity * p.price, 2) as gross_revenue,
    round((o.quantity * p.price) * 0.08, 2) as tax_amount,
    case 
        when (o.quantity * p.price) > 100.0 then 0.0 
        else 9.99 
    end as shipping_fee,
    round(
        (o.quantity * p.price) + 
        round((o.quantity * p.price) * 0.08, 2) + 
        (case when (o.quantity * p.price) > 100.0 then 0.0 else 9.99 end), 
        2
    ) as net_revenue,
    o.order_status,
    o.payment_method,
    o.order_date
from orders o
join products p on o.product_id = p.product_id
