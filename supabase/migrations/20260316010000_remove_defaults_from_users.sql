-- Drop defaults and allow NULL for numeric/portfolio fields
ALTER TABLE public.users
  ALTER COLUMN t212_weight DROP DEFAULT,
  ALTER COLUMN t212_weight DROP NOT NULL,
  ALTER COLUMN btc_weight DROP DEFAULT,
  ALTER COLUMN btc_weight DROP NOT NULL,
  ALTER COLUMN invest_amount DROP DEFAULT,
  ALTER COLUMN invest_amount DROP NOT NULL,
  ALTER COLUMN invest_interval DROP DEFAULT,
  ALTER COLUMN invest_interval DROP NOT NULL,
  ALTER COLUMN balance_buffer DROP DEFAULT,
  ALTER COLUMN balance_buffer DROP NOT NULL,
  ALTER COLUMN balance_alert_days DROP DEFAULT,
  ALTER COLUMN balance_alert_days DROP NOT NULL,
  ALTER COLUMN btc_withdrawal_treshold DROP DEFAULT,
  ALTER COLUMN btc_withdrawal_treshold DROP NOT NULL;

-- Change boolean broker/cron defaults to FALSE
ALTER TABLE public.users
  ALTER COLUMN cron_enabled SET DEFAULT FALSE,
  ALTER COLUMN btc_withdrawals_enabled SET DEFAULT FALSE,
  ALTER COLUMN trading212_enabled SET DEFAULT FALSE,
  ALTER COLUMN coinmate_enabled SET DEFAULT FALSE;
-- notifications_enabled stays DEFAULT TRUE (intentional)
