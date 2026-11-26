/*
  ==============================================================================
  dbt Model: stg_customers.sql
  Layer: Staging
  Materialization: View
  ==============================================================================
  
  EXPLANATION:
    Cleanses, renames, and type-casts raw customer records from raw.customers.
    Generates a deterministic hashed surrogate key using dbt_utils.generate_surrogate_key.
    
  BUSINESS USE CASE:
    Serves as the single source of truth for customer identity across the warehouse.
    Standardizes email strings and country codes for downstream CRM enrichment.
    
  PRODUCTION EXAMPLE:
    Raw fields like 'cust_id' or 'CreatedTimestamp' are normalized to snake_case
    ('customer_id', 'created_at') and cast to appropriate timestamp types.
    
  EXPECTED OUTPUT:
    Columns: customer_key, customer_id, first_name, last_name, full_name, email,
             country_code, signup_channel, created_at, updated_at
             
  PERFORMANCE NOTES:
    Materialized as a view to eliminate redundant storage costs while ensuring
    zero latency when querying fresh raw records.
    
  OPTIMIZATION TIPS:
    Keep staging models selection-only. Avoid joining or aggregating in staging.
    
  COMMON MISTAKES:
    Directly calling ref('stg_customers') inside another staging model; use source()
    in staging and ref() in intermediate/marts.
    
  INTERVIEW QUESTIONS:
    Q: Why use surrogate keys in staging models?
    A: Surrogate keys decouple warehouse joins from natural keys that may change
       or contain multi-column composite keys.
  ==============================================================================
*/

with source as (

    select * from {{ source('ecom_raw', 'raw_customers') }}

),

renamed as (

    select
        -- Primary Key & Surrogate Key
        {{ dbt_utils.generate_surrogate_key(['id']) }} as customer_key,
        cast(id as varchar(50)) as customer_id,

        -- Attributes
        cast(first_name as varchar(100)) as first_name,
        cast(last_name as varchar(100)) as last_name,
        trim(concat(first_name, ' ', last_name)) as full_name,
        lower(trim(email)) as email,
        upper(trim(country_code)) as country_code,
        coalesce(signup_channel, 'organic') as signup_channel,

        -- Timestamps
        cast(created_at as timestamp) as created_at,
        cast(updated_at as timestamp) as updated_at

    from source

)

select * from renamed
