-- 1. users table (linked to auth.users)
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    -- Exchange credentials
    t212_id_key TEXT NOT NULL DEFAULT '',
    t212_private_key TEXT NOT NULL DEFAULT '',
    coinmate_client_id INTEGER,
    coinmate_public_key TEXT NOT NULL DEFAULT '',
    coinmate_private_key TEXT NOT NULL DEFAULT '',
    -- Portfolio
    pie_id INTEGER,
    t212_weight INTEGER NOT NULL DEFAULT 90,
    btc_weight NUMERIC NOT NULL DEFAULT 10.0,
    invest_amount NUMERIC NOT NULL DEFAULT 5000.0,
    invest_interval TEXT NOT NULL DEFAULT '0 9 1 * *',
    balance_buffer NUMERIC NOT NULL DEFAULT 500.0,
    balance_alert_days INTEGER NOT NULL DEFAULT 5,
    btc_withdrawal_treshold INTEGER NOT NULL DEFAULT 500000,
    btc_external_adress TEXT NOT NULL DEFAULT '',
    -- Mail
    mail_host TEXT NOT NULL DEFAULT '',
    mail_port INTEGER NOT NULL DEFAULT 465,
    mail_password TEXT NOT NULL DEFAULT '',
    my_mail TEXT NOT NULL DEFAULT '',
    mail_recipient TEXT NOT NULL DEFAULT '',
    -- Deposit (optional)
    t212_deposit_account TEXT,
    t212_deposit_vs TEXT,
    coinmate_deposit_account TEXT,
    coinmate_deposit_vs TEXT,
    -- Control
    cron_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Add user_id FK to data tables
ALTER TABLE public.runs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id);
ALTER TABLE public.mails ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id);
ALTER TABLE public.btc_withdrawals ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id);

-- 3. RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mails ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.btc_withdrawals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users: own row" ON public.users FOR ALL USING (auth.uid() = id);
CREATE POLICY "runs: own rows" ON public.runs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "orders: own rows" ON public.orders FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "mails: own rows" ON public.mails FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "btc_withdrawals: own rows" ON public.btc_withdrawals FOR ALL USING (auth.uid() = user_id);
-- service_role bypasses RLS automatically — no extra policy needed

-- 4. updated_at trigger
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;
CREATE TRIGGER users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- One-time data backfill (run once after inserting user row into public.users):
-- UPDATE runs SET user_id = '<your-uuid>';
-- UPDATE orders SET user_id = '<your-uuid>';
-- UPDATE mails SET user_id = '<your-uuid>';
-- UPDATE btc_withdrawals SET user_id = '<your-uuid>';
