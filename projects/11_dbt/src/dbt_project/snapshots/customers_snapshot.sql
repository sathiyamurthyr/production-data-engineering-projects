/*
  ==============================================================================
  dbt Snapshot: customers_snapshot.sql
  Type: SCD Type 2 (Slowly Changing Dimension)
  ==============================================================================
  
  EXPLANATION:
    Tracks historical mutations to customer attributes over time (e.g. email updates,
    name changes, country updates).
    Uses the 'timestamp' strategy based on the updated_at column in raw.customers.
    
  BUSINESS USE CASE:
    Maintains point-in-time accuracy for historic customer attributes when calculating
    historical marketing attribution and cohort metrics.
    
  EXPECTED METADATA COLUMNS ADDED BY DBT:
    dbt_updated_at, dbt_valid_from, dbt_valid_to, dbt_scd_id
  ==============================================================================
*/

{% snapshot customers_snapshot %}

{{
    config(
      target_schema='snapshots',
      unique_key='id',
      strategy='timestamp',
      updated_at='updated_at'
    )
}}

select
    id,
    first_name,
    last_name,
    email,
    country_code,
    signup_channel,
    created_at,
    updated_at
from {{ source('ecom_raw', 'raw_customers') }}

{% endsnapshot %}
