import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { SchedulePicker } from "@/components/SchedulePicker";
import type { UserProfile } from "@/types";
import { CardSaveButton } from "../shared/CardSaveButton";
import { Field } from "../shared/Field";

interface SectionProps {
    profile: UserProfile;
    updateProfile: (updates: Partial<UserProfile>) => Promise<UserProfile>;
    updating: boolean;
}

export function AutomationSection({ profile, updateProfile, updating }: SectionProps) {
    const [form, setForm] = useState({
        invest_amount: String(profile.invest_amount),
        t212_weight: String(profile.t212_weight),
        btc_weight: String(profile.btc_weight),
        invest_interval: profile.invest_interval,
        btc_withdrawal_treshold: String(profile.btc_withdrawal_treshold),
        btc_external_adress: profile.btc_external_adress,
    });

    const hasChanges =
        form.invest_amount !== String(profile.invest_amount) ||
        form.t212_weight !== String(profile.t212_weight) ||
        form.btc_weight !== String(profile.btc_weight) ||
        form.invest_interval !== profile.invest_interval ||
        form.btc_withdrawal_treshold !== String(profile.btc_withdrawal_treshold) ||
        form.btc_external_adress !== profile.btc_external_adress;

    const save = () =>
        updateProfile({
            invest_amount: Number(form.invest_amount),
            t212_weight: Number(form.t212_weight),
            btc_weight: Number(form.btc_weight),
            invest_interval: form.invest_interval,
            btc_withdrawal_treshold: Number(form.btc_withdrawal_treshold),
            btc_external_adress: form.btc_external_adress,
        });

    return (
        <Card>
            <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
                <CardTitle className="text-base text-primary">Automation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
                <div className="flex items-center gap-3">
                    <Switch
                        id="cron_enabled"
                        checked={profile.cron_enabled}
                        onCheckedChange={(checked) => updateProfile({ cron_enabled: checked })}
                        disabled={updating}
                    />
                    <Label htmlFor="cron_enabled" className="text-sm">
                        Scheduled investing
                    </Label>
                </div>
                {profile.cron_enabled && (
                    <>
                        <div className="grid gap-3 sm:grid-cols-2">
                            <Field label="Invest Amount (CZK)" tooltip="The total amount in CZK that will be invested each scheduled run.">
                                <Input
                                    value={form.invest_amount}
                                    onChange={(e) => setForm((s) => ({ ...s, invest_amount: e.target.value }))}
                                />
                            </Field>
                            <Field label="T212 Weight" tooltip="Percentage of your invest amount allocated to Trading212 instruments. The T212 pie ratios are scaled by this weight.">
                                <Input
                                    value={form.t212_weight}
                                    onChange={(e) => setForm((s) => ({ ...s, t212_weight: e.target.value }))}
                                />
                            </Field>
                            <Field label="BTC Weight" tooltip="Percentage of your invest amount allocated to Bitcoin via Coinmate.">
                                <Input
                                    value={form.btc_weight}
                                    onChange={(e) => setForm((s) => ({ ...s, btc_weight: e.target.value }))}
                                />
                            </Field>
                            <Field label="Invest Schedule" className="sm:col-span-2">
                                <SchedulePicker
                                    value={form.invest_interval}
                                    onChange={(cron) => setForm((s) => ({ ...s, invest_interval: cron }))}
                                />
                            </Field>
                        </div>
                    </>
                )}

                <Separator />

                <div className="flex items-center gap-3">
                    <Switch
                        id="btc_withdrawals_enabled"
                        checked={profile.btc_withdrawals_enabled}
                        onCheckedChange={(checked) => updateProfile({ btc_withdrawals_enabled: checked })}
                        disabled={updating}
                    />
                    <Label htmlFor="btc_withdrawals_enabled" className="text-sm">
                        Automatic BTC withdrawals
                    </Label>
                </div>
                {profile.btc_withdrawals_enabled && (
                    <div className="grid gap-3 sm:grid-cols-2">
                        <Field label="BTC Withdrawal Threshold (CZK)" tooltip="When your total BTC holdings on Coinmate exceed this value in CZK, an automatic withdrawal to your external address is triggered.">
                            <Input
                                value={form.btc_withdrawal_treshold}
                                onChange={(e) => setForm((s) => ({ ...s, btc_withdrawal_treshold: e.target.value }))}
                            />
                        </Field>
                        <Field label="BTC External Address" tooltip="Bitcoin wallet address where automatic withdrawals are sent when the threshold is exceeded.">
                            <Input
                                value={form.btc_external_adress}
                                onChange={(e) => setForm((s) => ({ ...s, btc_external_adress: e.target.value }))}
                                placeholder="bc1q..."
                            />
                        </Field>
                    </div>
                )}

                <CardSaveButton onClick={save} disabled={updating || !hasChanges} />
            </CardContent>
        </Card>
    );
}
