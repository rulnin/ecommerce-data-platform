{% macro generate_schema_name(custom_schema_name, node) -%}
  {%- if target.name == 'dev' and custom_schema_name is not none -%}
    {{ custom_schema_name | trim }}
  {%- elif custom_schema_name is not none -%}
    {{ target.schema }}_{{ custom_schema_name | trim }}
  {%- else -%}
    {{ target.schema }}
  {%- endif -%}
{%- endmacro %}
