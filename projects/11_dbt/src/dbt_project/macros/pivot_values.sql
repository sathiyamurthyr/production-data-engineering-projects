{% macro pivot_values(column_name, values_list, agg='sum', value_col='amount', prefix='', suffix='_amount') %}
    {# 
      Custom Jinja macro to dynamically pivot categorical values into aggregate columns.
      Usage: {{ pivot_values('payment_type', ['credit_card', 'paypal']) }}
    #}
    {%- for val in values_list -%}
        {{ agg }}(case when {{ column_name }} = '{{ val }}' then {{ value_col }} else 0 end) as {{ prefix }}{{ val | replace(' ', '_') | lower }}{{ suffix }}
        {%- if not loop.last %}, {% endif -%}
    {%- endfor -%}
{% endmacro %}
