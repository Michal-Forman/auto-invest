-- Backfill the cost basis that analytics reads.
--
-- Two historical defects left the recorded cost lower than the money that actually
-- left the accounts, which inflated the reported gain to +85%:
--
--   1. Coinmate BUY fills subtracted the fee from filled_total instead of adding it,
--      so every BTC order understated its cost by twice the fee.
--   2. A run that lost a leg never reached FILLED and was expired to FAILED with
--      filled_total_czk left NULL, hiding the legs that did fill.
--
-- Order matters: correct the orders first so the run-level sums pick up the new values.

-- 1. Coinmate BUY fees: recorded value*qty - fee, should be value*qty + fee.
--    Bounded to orders placed before the fix shipped. Anything reconciled by the
--    corrected code is already right, and adding the fee again would overstate it.
update orders
set
    filled_total = filled_total + 2 * fee,
    filled_total_czk = filled_total_czk + 2 * fee_czk
where
    exchange = 'COINMATE'
    and side = 'BUY'
    and status = 'FILLED'
    and submitted_at < timestamptz '2026-08-13 00:00:00+00'
    and fee is not null
    and fee_czk is not null
    and filled_total is not null
    and filled_total_czk is not null;

-- 2. Runs expired to FAILED still bought whatever their filled legs bought.
update runs r
set filled_total_czk = sub.total
from (
    select run_id, sum(filled_total_czk) as total
    from orders
    where status = 'FILLED' and filled_total_czk is not null
    group by run_id
) sub
where
    r.id = sub.run_id
    and r.status = 'FAILED'
    and r.filled_total_czk is null;

-- 3. FILLED runs already have a total, but it was computed from the pre-fix Coinmate
--    values, so it is now stale by the same amount.
update runs r
set filled_total_czk = sub.total
from (
    select run_id, sum(filled_total_czk) as total
    from orders
    where status = 'FILLED' and filled_total_czk is not null
    group by run_id
) sub
where
    r.id = sub.run_id
    and r.status = 'FILLED';
