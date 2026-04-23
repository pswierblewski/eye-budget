/** Tekst błędu z zapytania lub mutacji (np. `Error` z `apiFetch`). */
export function formatQueryError(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  try {
    return JSON.stringify(error);
  } catch {
    return "Nieznany błąd";
  }
}
