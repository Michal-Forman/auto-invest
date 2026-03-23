import type { LucideIcon } from "lucide-react";
import { History, ListOrdered } from "lucide-react";

export type SectionId = "runs" | "orders";

export interface SectionMeta {
  id: SectionId;
  label: string;
  description: string;
  icon: LucideIcon;
}

export const SECTIONS: SectionMeta[] = [
  { id: "runs",   label: "Runs",   description: "Investment run history",   icon: History     },
  { id: "orders", label: "Orders", description: "Individual order records", icon: ListOrdered },
];
