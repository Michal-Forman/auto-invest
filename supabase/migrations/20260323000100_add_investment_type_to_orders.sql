ALTER TABLE public.orders
  ADD COLUMN investment_type text
  CHECK (investment_type IN ('dca', 'one_time'));

UPDATE public.orders SET investment_type = 'dca' WHERE investment_type IS NULL;

ALTER TABLE public.orders ALTER COLUMN investment_type SET NOT NULL;
