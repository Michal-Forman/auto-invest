-- Mail config moved to server-side environment variables.
-- Recipient is derived from the user's auth email (auth.users.email).
ALTER TABLE public.users
    DROP COLUMN IF EXISTS mail_host,
    DROP COLUMN IF EXISTS mail_port,
    DROP COLUMN IF EXISTS mail_password,
    DROP COLUMN IF EXISTS my_mail,
    DROP COLUMN IF EXISTS mail_recipient;
