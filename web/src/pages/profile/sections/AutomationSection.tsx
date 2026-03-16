import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import type { UserProfile } from "@/types";

interface SectionProps {
  profile: UserProfile;
  updateProfile: (updates: Partial<UserProfile>) => Promise<UserProfile>;
  updating: boolean;
}

export function AutomationSection({ profile, updateProfile, updating }: SectionProps) {
  return (
    <Card>
      <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
        <CardTitle className="text-base text-primary">Automation</CardTitle>
      </CardHeader>
      <CardContent className="pt-4 space-y-3">
        <div className="flex items-center gap-3">
          <Switch
            id="cron_enabled"
            checked={profile.cron_enabled}
            onCheckedChange={(checked) => updateProfile({ cron_enabled: checked })}
            disabled={updating}
          />
          <Label htmlFor="cron_enabled" className="text-sm">
            Enable scheduled investing (cron)
          </Label>
        </div>
      </CardContent>
    </Card>
  );
}
