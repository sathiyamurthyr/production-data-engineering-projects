/*
  ==============================================================================
  dbt Model: stg_orders.sql
  Layer: Staging
  Materialization: View
  ==============================================================================
  
  EXPLANATION:
    Staging model for e-commerce transactional orders. Normalizes status codes,
    casts financial amounts to numeric decimals, and generates surrogate keys.
    
  BUSINESS USE CASE:
    Provides standardized order transaction records for revenue recognition,
    fulfillment tracking, and sales analytics.
    
  EXPECTED OUTPUT:
    Columns: order_key, order_id, customer_id, order_status, order_date,
             subtotal_amount, tax_amount, discount_amount, total_amount, updated_at
  ==============================================================================
*/

with source as (

    select * from {{ source('ecom_raw', 'raw_orders') }}

),

renamed as (

    select
        -- Primary Key & Foreign Keys
        {{ dbt_utils.generate_surrogate_key(['id']) }} as order_key,
        cast(id as varchar(50)) as order_id,
        cast(customer_id as varchar(50)) as customer_id,

        -- Order Status & Categorization
        lower(trim(status)) as order_status,

        -- Financial Amounts
        cast(subtotal_amount as numeric(16, 2)) as subtotal_amount,
        cast(tax_amount as numeric(16, 2)) as tax_amount,
        cast(discount_amount as numeric(16, 2)) as discount_amount,
        cast(total_amount as numeric(16, 2)) as total_amount,

        -- Timestamps
        cast(order_date as timestamp) as order_date,
        cast(updated_at as timestamp) as updated_at

    from source

)

select * from renamed
