import type { LucideIcon } from "lucide-react";

export type SectionId = "account" | "brokers" | "portfolio" | "automation" | "notifications" | "instruments";

export interface SectionMeta {
  id: SectionId;
  label: string;
  description: string;
  icon: LucideIcon;
}

import { Bell, Briefcase, Clock, ListOrdered, UserCircle, Wallet } from "lucide-react";

export const SECTIONS: SectionMeta[] = [
  { id: "account", label: "Account", description: "Identity & sign out", icon: UserCircle },
  { id: "brokers", label: "Brokers", description: "Trading 212 & Coinmate keys", icon: Briefcase },
  { id: "portfolio", label: "Portfolio", description: "Investment amounts & weights", icon: Wallet },
  { id: "automation", label: "Automation", description: "Scheduled investing", icon: Clock },
  { id: "notifications", label: "Notifications", description: "Email alerts & balance warnings", icon: Bell },
  { id: "instruments", label: "Instruments", description: "Read-only registry", icon: ListOrdered },
];
