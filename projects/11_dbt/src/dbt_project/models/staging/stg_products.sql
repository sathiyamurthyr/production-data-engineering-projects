/*
  ==============================================================================
  dbt Model: stg_products.sql
  Layer: Staging
  Materialization: View
  ==============================================================================
  
  EXPLANATION:
    Staging model for product catalog master data. Standardizes product names,
    categories, pricing, and active flags.
    
  BUSINESS USE CASE:
    Feeds downstream product performance dashboards, margin calculations,
    and inventory analytics.
    
  EXPECTED OUTPUT:
    Columns: product_key, product_id, product_name, category_id, unit_price,
             cost_price, is_active, created_at
  ==============================================================================
*/

with source as (

    select * from {{ source('ecom_raw', 'raw_products') }}

),

renamed as (

    select
        -- Primary Key
        {{ dbt_utils.generate_surrogate_key(['id']) }} as product_key,
        cast(id as varchar(50)) as product_id,

        -- Product Attributes
        trim(name) as product_name,
        cast(category_id as varchar(50)) as category_id,
        cast(unit_price as numeric(16, 2)) as unit_price,
        cast(cost_price as numeric(16, 2)) as cost_price,
        coalesce(is_active, true) as is_active,

        -- Timestamps
        cast(created_at as timestamp) as created_at

    from source

)

select * from renamed
