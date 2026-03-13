import type { LucideIcon } from "lucide-react";

export type SectionId = "account" | "brokers" | "portfolio" | "automation" | "instruments";

export interface SectionMeta {
  id: SectionId;
  label: string;
  description: string;
  icon: LucideIcon;
}

import { Briefcase, Clock, ListOrdered, UserCircle, Wallet } from "lucide-react";

export const SECTIONS: SectionMeta[] = [
  { id: "account", label: "Account", description: "Identity & sign out", icon: UserCircle },
  { id: "brokers", label: "Brokers", description: "Trading 212 & Coinmate keys", icon: Briefcase },
  { id: "portfolio", label: "Portfolio", description: "Investment amounts & weights", icon: Wallet },
  { id: "automation", label: "Automation", description: "Cron & notifications", icon: Clock },
  { id: "instruments", label: "Instruments", description: "Read-only registry", icon: ListOrdered },
];
