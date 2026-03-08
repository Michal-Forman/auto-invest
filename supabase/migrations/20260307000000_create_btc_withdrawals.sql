CREATE TABLE btc_withdrawals (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    exchange_withdrawal_id BIGINT UNIQUE NOT NULL,

    amount                 NUMERIC NOT NULL,
    fee                    NUMERIC NOT NULL,
    amount_czk             NUMERIC NOT NULL,

    currency               TEXT NOT NULL DEFAULT 'BTC',

    status                 TEXT NOT NULL,
    transfer_type          TEXT NOT NULL,

    destination_address    TEXT NOT NULL,

    exchange_timestamp     TIMESTAMP NOT NULL,

    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
