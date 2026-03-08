ALTER TABLE btc_withdrawals
    ADD COLUMN IF NOT EXISTS fee_czk NUMERIC;

UPDATE btc_withdrawals SET fee_czk = 0 WHERE fee_czk IS NULL;

ALTER TABLE btc_withdrawals
    ALTER COLUMN fee_czk SET NOT NULL;
