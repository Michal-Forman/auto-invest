import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { Info } from "lucide-react";

export function Field({ label, tooltip, children, className }: { label: string; tooltip?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("space-y-1", className)}>
      <Label className="text-xs text-muted-foreground inline-flex items-center gap-1">
        {label}
        {tooltip && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="h-3.5 w-3.5 text-muted-foreground/60 cursor-help" />
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs text-xs">
              {tooltip}
            </TooltipContent>
          </Tooltip>
        )}
      </Label>
      {children}
    </div>
  );
}
