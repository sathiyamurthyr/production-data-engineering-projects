-- Staging model for Events reading from Silver Parquet layer
-- Explanation: Standardises event fields and filters anonymous sessions

with raw_events as (
    select * from read_parquet('d:/engineering-projects/production-data-engineering-projects/projects/20_capstone/data/silver/events/*.parquet')
)

select
    cast(event_id as string) as event_id,
    cast(customer_id as string) as customer_id,
    cast(event_type as string) as event_type,
    cast(product_id as string) as product_id,
    cast(timestamp as timestamp) as timestamp,
    cast(ip_address as string) as ip_address,
    cast(device as string) as device,
    cast(session_id as string) as session_id
from raw_events
