import { useConfig } from "@/hooks/use-config";
import { usePageTitle } from "@/hooks/use-page-title";
import { useProfile } from "@/hooks/use-profile";
import { SettingsShell } from "./profile/SettingsShell";

export function Profile() {
  usePageTitle("Settings");
  const { data: profile, loading, error, updateProfile, updating } = useProfile();
  const { data: config } = useConfig();

  if (loading) return <p className="text-muted-foreground p-6">Loading…</p>;
  if (error || !profile) return <p className="text-red-600 p-6">Failed to load profile.</p>;

  return (
    <SettingsShell
      profile={profile}
      config={config ?? null}
      updateProfile={updateProfile}
      updating={updating}
    />
  );
}
