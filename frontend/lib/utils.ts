/**
 * Convert ISO date string (yyyy-mm-dd) to Polish display format (dd-mm-yyyy).
 * Returns "—" for null / undefined / empty / malformed input.
 */
export function isoToDisplay(date: string | null | undefined): string {
  if (!date) return "—";
  const [y, m, d] = date.split("-");
  if (!y || !m || !d) return date;
  return `${d}-${m}-${y}`;
}

/**
 * Convert Polish display format (dd-mm-yyyy) back to ISO (yyyy-mm-dd).
 * Returns the input unchanged if it does not match the expected format.
 */
export function displayToIso(date: string): string {
  const [d, m, y] = date.split("-");
  if (!d || !m || !y) return date;
  return `${y}-${m}-${d}`;
}
