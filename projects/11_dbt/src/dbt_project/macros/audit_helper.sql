{% macro audit_helper_compare_relations(a_relation, b_relation, primary_key) %}
    {# 
      Custom Jinja macro to compare row counts, missing keys, and column diffs
      between two database relations (useful during model refactoring).
    #}
    with a as (
        select * from {{ a_relation }}
    ),
    b as (
        select * from {{ b_relation }}
    ),
    a_minus_b as (
        select {{ primary_key }} from a
        except
        select {{ primary_key }} from b
    ),
    b_minus_a as (
        select {{ primary_key }} from b
        except
        select {{ primary_key }} from a
    )
    select
        (select count(*) from a) as relation_a_count,
        (select count(*) from b) as relation_b_count,
        (select count(*) from a_minus_b) as rows_in_a_not_b,
        (select count(*) from b_minus_a) as rows_in_b_not_a
{% endmacro %}
