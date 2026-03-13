import { useState } from "react";
import { ChevronLeft } from "lucide-react";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import type { Config, UserProfile } from "@/types";
import { AccountSection } from "./sections/AccountSection";
import { AutomationSection } from "./sections/AutomationSection";
import { BrokersSection } from "./sections/BrokersSection";
import { InstrumentsSection } from "./sections/InstrumentsSection";
import { PortfolioSection } from "./sections/PortfolioSection";
import { SettingsNav } from "./SettingsNav";
import { SECTIONS, type SectionId } from "./types";

interface SettingsShellProps {
  profile: UserProfile;
  config: Config | null;
  updateProfile: (updates: Partial<UserProfile>) => Promise<UserProfile>;
  updating: boolean;
}

function SectionContent({
  id,
  profile,
  config,
  updateProfile,
  updating,
}: {
  id: SectionId;
  profile: UserProfile;
  config: Config | null;
  updateProfile: (updates: Partial<UserProfile>) => Promise<UserProfile>;
  updating: boolean;
}) {
  switch (id) {
    case "account":
      return <AccountSection />;
    case "brokers":
      return <BrokersSection profile={profile} updateProfile={updateProfile} updating={updating} />;
    case "portfolio":
      return <PortfolioSection profile={profile} updateProfile={updateProfile} updating={updating} />;
    case "automation":
      return <AutomationSection profile={profile} updateProfile={updateProfile} updating={updating} />;
    case "instruments":
      return <InstrumentsSection config={config} />;
  }
}

export function SettingsShell({ profile, config, updateProfile, updating }: SettingsShellProps) {
  const [selected, setSelected] = useState<SectionId>("account");
  const [mobileView, setMobileView] = useState<"menu" | "detail">("menu");
  const isMobile = useIsMobile();

  const handleSelect = (id: SectionId) => {
    setSelected(id);
    if (isMobile) setMobileView("detail");
  };

  const selectedMeta = SECTIONS.find((s) => s.id === selected);

  if (isMobile) {
    if (mobileView === "menu") {
      return (
        <div className="space-y-4">
          <h1 className="text-2xl font-semibold text-primary">Settings</h1>
          <SettingsNav selected={selected} onSelect={handleSelect} />
        </div>
      );
    }
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setMobileView("menu")} className="-ml-2">
            <ChevronLeft className="h-4 w-4 mr-1" />
            {selectedMeta?.label}
          </Button>
        </div>
        <SectionContent
          id={selected}
          profile={profile}
          config={config}
          updateProfile={updateProfile}
          updating={updating}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-primary">Settings</h1>
      <div className="flex gap-6 items-start">
        <div className="w-64 flex-shrink-0">
          <SettingsNav selected={selected} onSelect={handleSelect} />
        </div>
        <div className="flex-1 min-w-0">
          <SectionContent
            id={selected}
            profile={profile}
            config={config}
            updateProfile={updateProfile}
            updating={updating}
          />
        </div>
      </div>
    </div>
  );
}
