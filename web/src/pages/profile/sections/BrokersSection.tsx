import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { UserProfile } from "@/types";
import { CardSaveButton } from "../shared/CardSaveButton";
import { Field } from "../shared/Field";
import { SecretInput } from "../shared/SecretInput";

interface SectionProps {
  profile: UserProfile;
  updateProfile: (updates: Partial<UserProfile>) => Promise<UserProfile>;
  updating: boolean;
}

export function BrokersSection({ profile, updateProfile, updating }: SectionProps) {
  const [t212, setT212] = useState({
    t212_id_key: profile.t212_id_key,
    t212_private_key: profile.t212_private_key,
    pie_id: profile.pie_id != null ? String(profile.pie_id) : "",
    t212_deposit_account: profile.t212_deposit_account ?? "",
    t212_deposit_vs: profile.t212_deposit_vs ?? "",
  });

  const [coinmate, setCoinmate] = useState({
    coinmate_client_id: profile.coinmate_client_id != null ? String(profile.coinmate_client_id) : "",
    coinmate_public_key: profile.coinmate_public_key,
    coinmate_private_key: profile.coinmate_private_key,
    coinmate_deposit_account: profile.coinmate_deposit_account ?? "",
    coinmate_deposit_vs: profile.coinmate_deposit_vs ?? "",
  });

  const saveT212 = () =>
    updateProfile({
      t212_id_key: t212.t212_id_key,
      t212_private_key: t212.t212_private_key,
      pie_id: t212.pie_id !== "" ? Number(t212.pie_id) : null,
      t212_deposit_account: t212.t212_deposit_account || null,
      t212_deposit_vs: t212.t212_deposit_vs || null,
    } as Partial<UserProfile>);

  const saveCoinmate = () =>
    updateProfile({
      coinmate_client_id: coinmate.coinmate_client_id !== "" ? Number(coinmate.coinmate_client_id) : null,
      coinmate_public_key: coinmate.coinmate_public_key,
      coinmate_private_key: coinmate.coinmate_private_key,
      coinmate_deposit_account: coinmate.coinmate_deposit_account || null,
      coinmate_deposit_vs: coinmate.coinmate_deposit_vs || null,
    } as Partial<UserProfile>);

  return (
    <Card>
      <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
        <CardTitle className="text-base text-primary">Brokers</CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        <Tabs defaultValue="trading212">
          <TabsList className="mb-4">
            <TabsTrigger value="trading212">Trading 212</TabsTrigger>
            <TabsTrigger value="coinmate">Coinmate</TabsTrigger>
          </TabsList>

          <TabsContent value="trading212" className="space-y-3">
            <Field label="API ID Key">
              <SecretInput
                id="t212_id_key"
                value={t212.t212_id_key}
                onChange={(v) => setT212((s) => ({ ...s, t212_id_key: v }))}
                placeholder="t212_id_key"
              />
            </Field>
            <Field label="Private Key">
              <SecretInput
                id="t212_private_key"
                value={t212.t212_private_key}
                onChange={(v) => setT212((s) => ({ ...s, t212_private_key: v }))}
                placeholder="t212_private_key"
              />
            </Field>
            <Field label="Pie ID (optional)">
              <Input
                id="pie_id"
                value={t212.pie_id}
                onChange={(e) => setT212((s) => ({ ...s, pie_id: e.target.value }))}
                placeholder="123456"
              />
            </Field>
            <div className="flex items-center gap-2 pt-1">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs font-medium text-muted-foreground">Deposit</span>
              <div className="h-px flex-1 bg-border" />
            </div>
            <Field label="Deposit Account">
              <Input
                id="t212_deposit_account"
                value={t212.t212_deposit_account}
                onChange={(e) => setT212((s) => ({ ...s, t212_deposit_account: e.target.value }))}
              />
            </Field>
            <Field label="Deposit VS">
              <Input
                id="t212_deposit_vs"
                value={t212.t212_deposit_vs}
                onChange={(e) => setT212((s) => ({ ...s, t212_deposit_vs: e.target.value }))}
              />
            </Field>
            <CardSaveButton onClick={saveT212} disabled={updating} />
          </TabsContent>

          <TabsContent value="coinmate" className="space-y-3">
            <Field label="Client ID">
              <Input
                id="coinmate_client_id"
                value={coinmate.coinmate_client_id}
                onChange={(e) => setCoinmate((s) => ({ ...s, coinmate_client_id: e.target.value }))}
                placeholder="12345"
              />
            </Field>
            <Field label="Public Key">
              <Input
                id="coinmate_public_key"
                value={coinmate.coinmate_public_key}
                onChange={(e) => setCoinmate((s) => ({ ...s, coinmate_public_key: e.target.value }))}
              />
            </Field>
            <Field label="Private Key">
              <SecretInput
                id="coinmate_private_key"
                value={coinmate.coinmate_private_key}
                onChange={(v) => setCoinmate((s) => ({ ...s, coinmate_private_key: v }))}
              />
            </Field>
            <div className="flex items-center gap-2 pt-1">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs font-medium text-muted-foreground">Deposit</span>
              <div className="h-px flex-1 bg-border" />
            </div>
            <Field label="Deposit Account">
              <Input
                id="coinmate_deposit_account"
                value={coinmate.coinmate_deposit_account}
                onChange={(e) => setCoinmate((s) => ({ ...s, coinmate_deposit_account: e.target.value }))}
              />
            </Field>
            <Field label="Deposit VS">
              <Input
                id="coinmate_deposit_vs"
                value={coinmate.coinmate_deposit_vs}
                onChange={(e) => setCoinmate((s) => ({ ...s, coinmate_deposit_vs: e.target.value }))}
              />
            </Field>
            <CardSaveButton onClick={saveCoinmate} disabled={updating} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
