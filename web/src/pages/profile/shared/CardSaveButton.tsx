import { Button } from "@/components/ui/button";

export function CardSaveButton({ onClick, disabled }: { onClick: () => void; disabled?: boolean }) {
  return (
    <Button size="sm" onClick={onClick} disabled={disabled} className="mt-4">
      Save
    </Button>
  );
}
