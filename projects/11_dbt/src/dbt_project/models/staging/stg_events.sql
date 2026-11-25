/*
  ==============================================================================
  dbt Model: stg_events.sql
  Layer: Staging
  Materialization: View
  ==============================================================================
  
  EXPLANATION:
    Staging model for clickstream web behavioral events (e.g. page_view, add_to_cart, checkout).
    Standardizes timestamps, user device attributes, and event names.
    
  BUSINESS USE CASE:
    Powers conversion rate analysis, funnel metrics, and user engagement cohorts.
    
  EXPECTED OUTPUT:
    Columns: event_key, event_id, customer_id, event_type, device_type,
             page_url, event_timestamp
  ==============================================================================
*/

with source as (

    select * from {{ source('ecom_raw', 'raw_events') }}

),

renamed as (

    select
        -- Primary Key
        {{ dbt_utils.generate_surrogate_key(['id']) }} as event_key,
        cast(id as varchar(50)) as event_id,
        cast(customer_id as varchar(50)) as customer_id,

        -- Event Characteristics
        lower(trim(event_type)) as event_type,
        lower(trim(device_type)) as device_type,
        trim(page_url) as page_url,

        -- Timestamp
        cast(event_timestamp as timestamp) as event_timestamp

    from source

)

select * from renamed
