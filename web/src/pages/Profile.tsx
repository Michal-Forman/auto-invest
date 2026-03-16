import { usePageTitle } from "@/hooks/use-page-title";
import { useProfile } from "@/hooks/use-profile";
import { Skeleton } from "@/components/ui/skeleton";
import { SettingsShell } from "./profile/SettingsShell";

export function Profile() {
  usePageTitle("Settings");
  const { data: profile, loading, error, updateProfile, updating } = useProfile();

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-32" />
        <div className="flex gap-6 items-start">
          <div className="w-64 flex-shrink-0 space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
          <div className="flex-1 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        </div>
      </div>
    );
  }
  if (error || !profile) return <p className="text-red-600 p-6">Failed to load profile.</p>;

  return (
    <SettingsShell
      profile={profile}
      updateProfile={updateProfile}
      updating={updating}
    />
  );
}
