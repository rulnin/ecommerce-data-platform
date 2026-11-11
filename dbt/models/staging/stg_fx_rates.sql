select base_currency, quote_currency, rate_date, provider, rate
from {{ source('raw', 'fx_rates') }}
