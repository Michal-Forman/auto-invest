-- Add amount_czk if not already present (fresh installs get it from the original migration)
ALTER TABLE btc_withdrawals
    ADD COLUMN IF NOT EXISTS amount_czk NUMERIC;

UPDATE btc_withdrawals SET amount_czk = 0 WHERE amount_czk IS NULL;

ALTER TABLE btc_withdrawals
    ALTER COLUMN amount_czk SET NOT NULL;

-- Change id to UUID only if it is still an integer (remote was created before the original migration was updated)
DO $$
BEGIN
    IF (SELECT data_type FROM information_schema.columns
            WHERE table_name = 'btc_withdrawals' AND column_name = 'id') = 'integer' THEN
        ALTER TABLE btc_withdrawals ALTER COLUMN id DROP DEFAULT;
        ALTER TABLE btc_withdrawals ALTER COLUMN id SET DATA TYPE UUID USING gen_random_uuid();
        ALTER TABLE btc_withdrawals ALTER COLUMN id SET DEFAULT gen_random_uuid();
    END IF;
END $$;
