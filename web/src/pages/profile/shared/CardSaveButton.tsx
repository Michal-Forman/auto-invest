import { useEffect, useRef, useState } from "react";

import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";

export function CardSaveButton({
  onClick,
  disabled,
}: {
  onClick: () => Promise<unknown>;
  disabled?: boolean;
}) {
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  async function handleClick() {
    setState("saving");
    await onClick();
    setState("saved");
    timeoutRef.current = setTimeout(() => setState("idle"), 2000);
  }

  if (state === "saved") {
    return (
      <Button size="sm" disabled className="mt-4 text-green-600">
        <Check className="h-4 w-4" />
        Saved
      </Button>
    );
  }

  if (state === "saving") {
    return (
      <Button size="sm" disabled className="mt-4">
        Saving
      </Button>
    );
  }

  return (
    <Button size="sm" onClick={handleClick} disabled={disabled} className="mt-4">
      Save
    </Button>
  );
}
