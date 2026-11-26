-- Marketing Metrics Table (Marts)
-- Explanation: Computes clickstream stats and purchase conversion rates per customer

with events as (
    select * from {{ ref('stg_events') }}
)

select
    customer_id,
    count(event_id) as total_interactions,
    sum(case when event_type = 'view_item' then 1 else 0 end) as total_pageviews,
    sum(case when event_type = 'add_to_cart' then 1 else 0 end) as total_add_to_carts,
    sum(case when event_type = 'purchase' then 1 else 0 end) as total_purchases,
    round(
        cast(sum(case when event_type = 'purchase' then 1 else 0 end) as double) / 
        cast(count(event_id) as double), 
        4
    ) as conversion_rate
from events
where customer_id is not null
group by customer_id
