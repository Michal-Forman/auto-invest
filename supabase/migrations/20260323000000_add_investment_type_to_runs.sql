ALTER TABLE public.runs
  ADD COLUMN investment_type text
  CHECK (investment_type IN ('dca', 'one_time'));

UPDATE public.runs SET investment_type = 'dca' WHERE investment_type IS NULL;

ALTER TABLE public.runs ALTER COLUMN investment_type SET NOT NULL;
