# Import CSV — lista kont otwierana klikiem, nie hoverem

**Date:** 2026-07-14
**Status:** Approved
**Suggested branch:** krótki fix, np. `fix/import-csv-dropdown-click`

---

## Problem

W `frontend/app/bank-transactions/page.tsx` przycisk „Import CSV” otwiera listę kont do wyboru przez CSS `group` + `hidden group-hover:block`. Lista jest pozycjonowana `absolute right-0 top-full mt-1` — czyli z 4px odstępem od przycisku. Przy przesuwaniu kursora z przycisku w stronę listy, kursor na moment opuszcza `group`, hover się przerywa i lista chowa się **zanim** użytkownik zdąży kliknąć element. W efekcie nie da się wybrać konta z listy przy imporcie.

---

## Scope

- **Tylko** blok „Import CSV” w `frontend/app/bank-transactions/page.tsx` (obecnie ok. linii 893–914).
- **Bez zmian:** logika importu (`handleImportClick`, `handleFileChange`, `importMutation`), pozostałe przyciski w nagłówku (`Ponów kategoryzację`, `Zarządzaj kontami`), karty kont pod nagłówkiem, jakikolwiek inny komponent.
- Sprawdzone: to jedyne miejsce w całym frontendzie z wzorcem hover-menu (`group-hover:block` użyty do pokazywania listy) — pozostałe wystąpienia `group-hover` w kodzie to tylko zmiany kolorów/obrotu ikon przy już klikalnych, rozwijanych sekcjach (`receipts/[id]/page.tsx`), nie osobny problem.

---

## Zachowanie docelowe (UI)

1. Klik na przycisk „Import CSV” **przełącza** (toggle) widoczność listy kont — nie hover.
2. Po otwarciu lista pozostaje widoczna niezależnie od ruchu kursora (brak przerwy w hover, bo mechanizm nie zależy od hover).
3. Klik na nazwę konta na liście: zamyka listę **i** wywołuje istniejące `handleImportClick(acc.id)` (otwiera skryty `<input type="file">`) — logika importu bez zmian.
4. Klik gdziekolwiek poza przyciskiem i listą (np. w innym miejscu strony) zamyka listę.
5. Mały `ChevronDown` (lucide-react, już używany w projekcie w `receipts/[id]/page.tsx`) obok etykiety „Import CSV”; obrócony o 180° (`rotate-180`) gdy lista jest otwarta — sygnalizuje, że to menu rozwijane.
6. Branch bez kont (`accountsQuery.data` puste/undefined) — przycisk `disabled` z `title="Najpierw dodaj konto bankowe"` — **bez zmian**.
7. Gdy `importMutation.isPending`, przycisk „Import CSV” jest `disabled` — **bez zmian** (naturalnie blokuje też otwarcie listy, bo `disabled` button nie odpala `onClick`).

---

## Podejście techniczne

**A — lokalny `useState` + listener `mousedown` na `document` (wybrane).**

- Jeden `useRef<HTMLDivElement>` na wrapper obejmujący przycisk „Import CSV” **i** listę (zamiast `className="relative group"` — zostaje `relative`, ale bez `group`).
- `const [importMenuOpen, setImportMenuOpen] = useState(false)`.
- Klik na przycisk: `setImportMenuOpen(v => !v)`.
- Lista renderowana warunkowo: `{importMenuOpen && (...)}"` zamiast `hidden group-hover:block`.
- `useEffect` (aktywny tylko gdy `importMenuOpen`) z listenerem `mousedown` na `document`: jeśli `event.target` nie jest zawarty w wrapperze — `setImportMenuOpen(false)`. Ten sam mechanizm co już działa w `components/ui/ThreeDotsMenu.tsx` (bez potrzeby portalu/`fixed` — to nagłówek strony, nie wiersz przewijanej tabeli, więc zwykłe `absolute` wystarcza, clipping nie jest problemem).
- Klik na element listy: dodatkowo `setImportMenuOpen(false)` przed/po `handleImportClick(acc.id)`.
- Zero nowych zależności, zero zmian w innych plikach.

Rozważone i odrzucone (opisane w rozmowie brainstormingowej): wydzielenie generycznego `DropdownMenu` w `components/ui/` (zbyt duży zakres na ten bugfix, YAGNI) i `@radix-ui/react-dropdown-menu` (nowa zależność, nieproporcjonalna do skali problemu — projekt ma już sprawdzony własny wzorzec).

---

## Testy / weryfikacja

Czysto interakcyjna zmiana UI, bez logiki biznesowej i bez istniejących testów automatycznych dla tej strony (RTL/Playwright). Weryfikacja:

- `npx tsc --noEmit` (frontend)
- `npm run lint` (frontend)
- Ręczna weryfikacja w przeglądarce: klik otwiera/zamyka listę, przesunięcie kursora przez odstęp nie zamyka listy, klik na konto zamyka listę i otwiera file picker, klik poza listą zamyka ją, przycisk `disabled` (brak kont / trwający import) nie otwiera listy.

Brak nowych testów automatycznych — zgodnie z konwencją analogicznych drobnych poprawek UI w tym repo (np. `2026-04-21-bank-tx-list-save-button-layout-design.md`).

---

## Self-review

- [x] Brak TBD / placeholderów.
- [x] Zakres ograniczony do jednego bloku w jednym pliku.
- [x] Logika importu (`handleImportClick`, `handleFileChange`, mutation) niezmieniona.
- [x] Zachowanie disabled-state (brak kont, trwający import) zachowane.
- [x] Wzorzec zamykania po kliknięciu poza obszarem zgodny z istniejącym `ThreeDotsMenu` — konsystentność z resztą kodu.
