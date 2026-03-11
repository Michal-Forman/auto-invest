-- Add email column
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS email text NOT NULL DEFAULT '';

-- Trigger: on public.users INSERT, copy email from auth.users
CREATE OR REPLACE FUNCTION public.set_user_email_on_insert()
RETURNS trigger AS $$
BEGIN
  SELECT email INTO NEW.email FROM auth.users WHERE id = NEW.id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_set_user_email_on_insert
  BEFORE INSERT ON public.users
  FOR EACH ROW EXECUTE FUNCTION public.set_user_email_on_insert();

-- Trigger: on auth.users email UPDATE, cascade to public.users
CREATE OR REPLACE FUNCTION public.sync_user_email_on_update()
RETURNS trigger AS $$
BEGIN
  UPDATE public.users SET email = NEW.email WHERE id = NEW.id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_sync_user_email_on_update
  AFTER UPDATE OF email ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.sync_user_email_on_update();

-- Backfill existing users
UPDATE public.users u
SET email = COALESCE(a.email, '')
FROM auth.users a
WHERE u.id = a.id;
