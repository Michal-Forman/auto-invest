import { ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { SECTIONS, type SectionId } from "./types";

interface HistoryNavProps {
  selected: SectionId;
  onSelect: (id: SectionId) => void;
}

export function HistoryNav({ selected, onSelect }: HistoryNavProps) {
  return (
    <Card className="py-1 overflow-hidden">
      <ul className="flex flex-col">
        {SECTIONS.map((section, i) => {
          const Icon = section.icon;
          const isActive = selected === section.id;
          return (
            <li key={section.id}>
              {i > 0 && <Separator />}
              <button
                type="button"
                onClick={() => onSelect(section.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-accent hover:text-accent-foreground ${
                  isActive ? "bg-accent text-accent-foreground" : ""
                }`}
              >
                <div className="flex-shrink-0 h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Icon className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium leading-tight">{section.label}</div>
                  <div className="text-xs text-muted-foreground truncate">{section.description}</div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              </button>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
