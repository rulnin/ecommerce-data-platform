select requested_date, rate_date
from {{ source('raw', 'fx_requests') }}
