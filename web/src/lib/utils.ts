import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a number with spaces as thousand separators (e.g. 1 234 567).
 * Always use this for monetary/numeric display values in the UI.
 * Optional `decimals` controls decimal places (rounds if omitted).
 */
export function formatNumber(value: number, decimals?: number): string {
  const fixed = decimals !== undefined ? value.toFixed(decimals) : String(Math.round(value))
  const [integer, decimal] = fixed.split(".")
  const withSpaces = integer.replace(/\B(?=(\d{3})+(?!\d))/g, "\u00A0")
  return decimal !== undefined ? `${withSpaces}.${decimal}` : withSpaces
}
