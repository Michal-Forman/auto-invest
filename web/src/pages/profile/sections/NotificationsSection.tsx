import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import type { UserProfile } from "@/types";
import { CardSaveButton } from "../shared/CardSaveButton";
import { Field } from "../shared/Field";

interface SectionProps {
  profile: UserProfile;
  updateProfile: (updates: Partial<UserProfile>) => Promise<UserProfile>;
  updating: boolean;
}

export function NotificationsSection({ profile, updateProfile, updating }: SectionProps) {
  const [form, setForm] = useState({
    balance_buffer: profile.balance_buffer != null ? String(profile.balance_buffer) : "",
    balance_alert_days: profile.balance_alert_days != null ? String(profile.balance_alert_days) : "",
  });

  const hasChanges =
    form.balance_buffer !== (profile.balance_buffer != null ? String(profile.balance_buffer) : "") ||
    form.balance_alert_days !== (profile.balance_alert_days != null ? String(profile.balance_alert_days) : "");

  const save = () =>
    updateProfile({
      balance_buffer: Number(form.balance_buffer),
      balance_alert_days: Number(form.balance_alert_days),
    });

  return (
    <Card>
      <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
        <CardTitle className="text-base text-primary">Notifications</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        <div className="flex items-center gap-3">
          <Switch
            id="notifications_enabled"
            checked={profile.notifications_enabled}
            onCheckedChange={(checked) => updateProfile({ notifications_enabled: checked })}
            disabled={updating}
          />
          <Label htmlFor="notifications_enabled" className="text-sm">
            Enable email notifications
          </Label>
        </div>

        <Separator />

        <p className="text-xs font-medium text-muted-foreground">Balance Alerts</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Balance Buffer" tooltip="Multiplier applied to your per-run spending when estimating when your balance will run out. Higher values give more conservative estimates.">
            <Input
              value={form.balance_buffer}
              onChange={(e) => setForm((s) => ({ ...s, balance_buffer: e.target.value }))}
            />
          </Field>
          <Field label="Balance Alert Days" tooltip="You'll receive an email alert when your exchange balance is estimated to run out within this many days.">
            <Input
              value={form.balance_alert_days}
              onChange={(e) => setForm((s) => ({ ...s, balance_alert_days: e.target.value }))}
            />
          </Field>
        </div>

        <CardSaveButton onClick={save} disabled={updating || !hasChanges} />
      </CardContent>
    </Card>
  );
}
