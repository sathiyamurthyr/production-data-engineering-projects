{% macro date_spine(start_date, end_date) %}
    {# 
      Custom Jinja macro generating a continuous series of calendar dates.
      Compatible with PostgreSQL date generation functions.
    #}
    select
        cast(datum as date) as date_day,
        extract(year from datum) as year_number,
        extract(month from datum) as month_number,
        extract(day from datum) as day_of_month,
        extract(dow from datum) as day_of_week,
        to_char(datum, 'Day') as day_name,
        to_char(datum, 'Month') as month_name
    from generate_series(
        cast('{{ start_date }}' as date),
        cast('{{ end_date }}' as date),
        cast('1 day' as interval)
    ) as datum
{% endmacro %}
