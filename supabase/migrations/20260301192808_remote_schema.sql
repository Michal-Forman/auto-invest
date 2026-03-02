


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";





SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."orders" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "run_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "idempotency_key" "text" NOT NULL,
    "external_order_id" "text",
    "exchange" "text" NOT NULL,
    "instrument_type" "text" NOT NULL,
    "t212_ticker" "text" NOT NULL,
    "yahoo_symbol" "text" NOT NULL,
    "currency" "text" NOT NULL,
    "side" "text" NOT NULL,
    "order_type" "text" NOT NULL,
    "quantity" numeric NOT NULL,
    "total" numeric NOT NULL,
    "total_czk" numeric NOT NULL,
    "limit_price" numeric,
    "extended_hours" boolean NOT NULL,
    "status" "text" NOT NULL,
    "submitted_at" timestamp with time zone NOT NULL,
    "filled_at" timestamp with time zone,
    "filled_quantity" numeric,
    "fee_currency" "text",
    "fee" numeric,
    "fee_czk" numeric,
    "request" "jsonb",
    "response" "jsonb",
    "error" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "price" numeric,
    "multiplier" numeric,
    "name" "text",
    "fill_price" numeric,
    "filled_total_czk" numeric,
    "fill_fx_rate" numeric,
    "fx_rate" numeric,
    "filled_total" numeric
);


ALTER TABLE "public"."orders" OWNER TO "postgres";


COMMENT ON TABLE "public"."orders" IS 'collection of every order. Every ticker / instrument has its own order.';



CREATE TABLE IF NOT EXISTS "public"."runs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "started_at" timestamp with time zone NOT NULL,
    "finished_at" timestamp with time zone,
    "status" "text" NOT NULL,
    "invest_amount" numeric NOT NULL,
    "invest_interval" "text" NOT NULL,
    "t212_default_weight" numeric NOT NULL,
    "btc_default_weight" numeric NOT NULL,
    "planned_total_czk" numeric,
    "filled_total_czk" numeric,
    "total_orders" smallint NOT NULL,
    "successful_orders" smallint NOT NULL,
    "failed_orders" smallint NOT NULL,
    "distribution" "jsonb",
    "multipliers" "jsonb",
    "error" "text",
    "test" boolean NOT NULL
);


ALTER TABLE "public"."runs" OWNER TO "postgres";


ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_idempotency_key_key" UNIQUE ("idempotency_key");



ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."runs"
    ADD CONSTRAINT "runs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_run_id_fkey" FOREIGN KEY ("run_id") REFERENCES "public"."runs"("id");





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";








































































































































































GRANT ALL ON TABLE "public"."orders" TO "anon";
GRANT ALL ON TABLE "public"."orders" TO "authenticated";
GRANT ALL ON TABLE "public"."orders" TO "service_role";



GRANT ALL ON TABLE "public"."runs" TO "anon";
GRANT ALL ON TABLE "public"."runs" TO "authenticated";
GRANT ALL ON TABLE "public"."runs" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































drop extension if exists "pg_net";


