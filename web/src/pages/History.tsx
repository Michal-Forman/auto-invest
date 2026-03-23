import { usePageTitle } from "@/hooks/use-page-title";
import { HistoryShell } from "./history/HistoryShell";

export function History() {
  usePageTitle("History");
  return <HistoryShell />;
}
