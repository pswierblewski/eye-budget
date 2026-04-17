/** Parsuje string kwoty wpisany przez użytkownika.
 *  Akceptuje ',' i '.' jako separator dziesiętny.
 *  Zwraca null gdy wartość pusta lub nieparsowalna. */
export function parseAmountInput(value: string): number | null {
  const normalized = value.trim().replaceAll(",", ".");
  if (normalized === "") return null;
  const n = parseFloat(normalized);
  return isNaN(n) ? null : n;
}
