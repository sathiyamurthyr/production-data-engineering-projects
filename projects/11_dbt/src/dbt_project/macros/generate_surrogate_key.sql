{% macro generate_surrogate_key(field_list) %}
    {# 
      Custom Jinja macro to build deterministic MD5 hashed surrogate keys
      across a list of column values, handling NULL values cleanly.
    #}
    {%- set fields = [] -%}
    {%- for field in field_list -%}
        {%- do fields.append("coalesce(cast(" ~ field ~ " as varchar), '_dbt_null_')") -%}
    {%- endfor -%}
    
    md5({{ fields | join(" || '-' || ") }})
{% endmacro %}
