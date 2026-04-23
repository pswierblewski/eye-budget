# Feature Specification: Goal Priority Tooltip

**Feature Branch**: `002-goal-priority-tooltip`
**Created**: 2026-03-17
**Status**: Draft
**Input**: User description: "chcę, aby obok tego priorytetu była ikonka 'i' w kółeczku, na której po najechaniu kursorem ma się pojawić popup z informacją, jak ten priorytet powinien być traktowany."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Odczytanie wyjaśnienia priorytetu (Priority: P1)

Użytkownik wypełnia formularz tworzenia lub edycji celu finansowego i nie jest pewien, jak ustawić wartość pola "Priorytet". Najeżdża kursorem na ikonkę informacyjną znajdującą się obok etykiety tego pola i odczytuje wyjaśnienie zasady działania priorytetu, nie opuszczając formularza.

**Why this priority**: To jest jedyna historia w tej funkcji — stanowi cały zakres zmiany. Bezpośrednio rozwiązuje problem braku kontekstu przy uzupełnianiu pola priorytetu.

**Independent Test**: Można przetestować otwierając formularz celu finansowego, najeżdżając na ikonkę i weryfikując treść popupu.

**Acceptance Scenarios**:

1. **Given** formularz tworzenia/edycji celu jest otwarty, **When** użytkownik patrzy na pole "Priorytet", **Then** obok etykiety lub pola widoczna jest ikonka "i" w kółeczku.
2. **Given** formularz jest otwarty, **When** użytkownik najeżdża kursorem na ikonkę "i", **Then** pojawia się tooltip/popup z wyjaśnieniem zasady priorytetu.
3. **Given** tooltip jest widoczny, **When** użytkownik odczytuje treść, **Then** tooltip zawiera informację, że niższy numer oznacza wyższy priorytet, oraz przykład (np. 1 = cel najważniejszy).
4. **Given** tooltip jest widoczny, **When** użytkownik przesuwa kursor poza ikonkę, **Then** tooltip znika.
5. **Given** formularz jest używany na urządzeniu mobilnym (dotyk), **When** użytkownik tapuje ikonkę "i", **Then** tooltip pojawia się i jest czytelny.

---

### Edge Cases

- Co się dzieje, gdy tooltip wychodzi poza krawędź ekranu? Tooltip powinien automatycznie zmieniać stronę wyświetlania, żeby pozostać w widocznym obszarze.
- Czy tooltip działa na urządzeniach dotykowych? Tak — tap na ikonkę powinien przełączać widoczność tooltipa (toggle).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: W formularzu tworzenia i edycji celu finansowego, obok etykiety pola "Priorytet", MUSI być wyświetlona ikonka informacyjna (litera "i" w kółeczku).
- **FR-002**: Po najechaniu kursorem (hover) na ikonkę MUSI pojawić się tooltip z wyjaśnieniem zasady priorytetu.
- **FR-003**: Treść tooltipa MUSI zawierać wyjaśnienie, że niższy numer priorytetu oznacza wyższy priorytet celu, oraz co najmniej jeden przykład ilustrujący tę zasadę.
- **FR-004**: Tooltip MUSI znikać po przesunięciu kursora poza obszar ikonki.
- **FR-005**: Na urządzeniach dotykowych ikonka MUSI reagować na tap, przełączając widoczność tooltipa.
- **FR-006**: Ikonka NIE MOŻE zakłócać nawigacji klawiaturą ani dostępności formularza (pole priorytetu nadal musi być osiągalne i wypełnialne przez klawiaturę).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Użytkownik może odczytać wyjaśnienie priorytetu bez opuszczania formularza i bez wyszukiwania dokumentacji zewnętrznej.
- **SC-002**: Tooltip pojawia się natychmiastowo po najechaniu — brak zauważalnego opóźnienia dla użytkownika.
- **SC-003**: Treść tooltipa jest wystarczająca, aby nowy użytkownik poprawnie ustawił priorytet przy pierwszej próbie (weryfikowalne przez test użyteczności).
- **SC-004**: Ikonka jest widoczna i klikalna zarówno na desktopie, jak i na urządzeniach mobilnych.

## Assumptions

- Formularz celu finansowego (`GoalForm`) już istnieje i zawiera pole "Priorytet" — zmiana jest wyłącznie addytywna (nie modyfikuje istniejącej logiki pola).
- Treść tooltipa jest statyczna — wyjaśnienie zasady priorytetu nie zmienia się dynamicznie i nie jest pobierane z backendu.
- Polska wersja językowa jako domyślna — treść tooltipa po polsku.
- Projekt posiada lub może użyć natywnych mechanizmów tooltip bez konieczności instalowania dodatkowych bibliotek zewnętrznych.
