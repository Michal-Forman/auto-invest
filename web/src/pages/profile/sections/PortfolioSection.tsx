import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SchedulePicker } from "@/components/SchedulePicker";
import type { UserProfile } from "@/types";
import { CardSaveButton } from "../shared/CardSaveButton";
import { Field } from "../shared/Field";

interface SectionProps {
  profile: UserProfile;
  updateProfile: (updates: Partial<UserProfile>) => Promise<UserProfile>;
  updating: boolean;
}

export function PortfolioSection({ profile, updateProfile, updating }: SectionProps) {
  const [portfolio, setPortfolio] = useState({
    invest_amount: String(profile.invest_amount),
    t212_weight: String(profile.t212_weight),
    btc_weight: String(profile.btc_weight),
    invest_interval: profile.invest_interval,
    balance_buffer: String(profile.balance_buffer),
    balance_alert_days: String(profile.balance_alert_days),
    btc_withdrawal_treshold: String(profile.btc_withdrawal_treshold),
    btc_external_adress: profile.btc_external_adress,
  });

  const hasChanges =
    portfolio.invest_amount !== String(profile.invest_amount) ||
    portfolio.t212_weight !== String(profile.t212_weight) ||
    portfolio.btc_weight !== String(profile.btc_weight) ||
    portfolio.invest_interval !== profile.invest_interval ||
    portfolio.balance_buffer !== String(profile.balance_buffer) ||
    portfolio.balance_alert_days !== String(profile.balance_alert_days) ||
    portfolio.btc_withdrawal_treshold !== String(profile.btc_withdrawal_treshold) ||
    portfolio.btc_external_adress !== profile.btc_external_adress;

  const save = () =>
    updateProfile({
      invest_amount: Number(portfolio.invest_amount),
      t212_weight: Number(portfolio.t212_weight),
      btc_weight: Number(portfolio.btc_weight),
      invest_interval: portfolio.invest_interval,
      balance_buffer: Number(portfolio.balance_buffer),
      balance_alert_days: Number(portfolio.balance_alert_days),
      btc_withdrawal_treshold: Number(portfolio.btc_withdrawal_treshold),
      btc_external_adress: portfolio.btc_external_adress,
    });

  return (
    <Card>
      <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
        <CardTitle className="text-base text-primary">Portfolio</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Invest Amount (CZK)">
            <Input
              value={portfolio.invest_amount}
              onChange={(e) => setPortfolio((s) => ({ ...s, invest_amount: e.target.value }))}
            />
          </Field>
          <Field label="T212 Weight">
            <Input
              value={portfolio.t212_weight}
              onChange={(e) => setPortfolio((s) => ({ ...s, t212_weight: e.target.value }))}
            />
          </Field>
          <Field label="BTC Weight">
            <Input
              value={portfolio.btc_weight}
              onChange={(e) => setPortfolio((s) => ({ ...s, btc_weight: e.target.value }))}
            />
          </Field>
          <Field label="Invest Schedule" className="sm:col-span-2">
            <SchedulePicker
              value={portfolio.invest_interval}
              onChange={(cron) => setPortfolio((s) => ({ ...s, invest_interval: cron }))}
            />
          </Field>
          <Field label="Balance Buffer (CZK)">
            <Input
              value={portfolio.balance_buffer}
              onChange={(e) => setPortfolio((s) => ({ ...s, balance_buffer: e.target.value }))}
            />
          </Field>
          <Field label="Balance Alert Days">
            <Input
              value={portfolio.balance_alert_days}
              onChange={(e) => setPortfolio((s) => ({ ...s, balance_alert_days: e.target.value }))}
            />
          </Field>
          <Field label="BTC Withdrawal Threshold (sats)">
            <Input
              value={portfolio.btc_withdrawal_treshold}
              onChange={(e) => setPortfolio((s) => ({ ...s, btc_withdrawal_treshold: e.target.value }))}
            />
          </Field>
          <Field label="BTC External Address">
            <Input
              value={portfolio.btc_external_adress}
              onChange={(e) => setPortfolio((s) => ({ ...s, btc_external_adress: e.target.value }))}
              placeholder="bc1q..."
            />
          </Field>
        </div>
        <CardSaveButton onClick={save} disabled={updating || !hasChanges} />
      </CardContent>
    </Card>
  );
}
