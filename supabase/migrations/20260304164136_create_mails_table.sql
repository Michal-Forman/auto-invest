CREATE TABLE IF NOT EXISTS "public"."mails" (
    "id"       uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    "type"     text NOT NULL,
    "subject"  text NOT NULL,
    "sent_at"  timestamp with time zone NOT NULL DEFAULT now(),
    "period"   text,

    CONSTRAINT "mails_pkey" PRIMARY KEY ("id")
);
