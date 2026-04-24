# Receipt PDF preprocessing — design

**Status:** approved (approach + multi-page behavior)  
**Date:** 2026-04-24  
**Context:** Paragony są dziś obsługiwane jako obrazy rastrowe. `PreprocessingService.preprocess_image()` używa `PIL.Image.open()` na pliku w `INPUT_DIR`. Pliki PDF kończą się błędem typu `cannot identify image file '.../file.pdf'` (przykład: `receipts_scans.id = 9126`, `PN_26634_04_26_MG.pdf`). OCR i MinIO nie są wywoływane, `minio_object_key` pozostaje `NULL`.

## Goal

Dopuścić pliki `.pdf` w tym samym pipeline co obrazy: po przygotowaniu **jednego** obrazu rastrowego dalsze kroki (skalowanie, zapis JPEG, upload MinIO, OCR z `input_image`) pozostają bez zmian semantycznych.

## Decisions (locked)

| Topic | Choice |
|--------|--------|
| Library | **PyMuPDF** (`pymupdf` on PyPI, import `fitz`) — bez zewnętrznego Popplera w systemie, spójne z `python:3.11-slim`. |
| Multi-page | **Wszystkie strony łączone w jeden obraz w układzie pionowym** (góra → dół w kolejności stron). |
| Post-render | Obecna logika: zmniejszenie wymiarów, konwersja do RGB, JPEG w `OUTPUT_DIR` pod stemem nazwy oryginalnego pliku (np. `PN_26634_04_26_MG.jpg` dla `.pdf`). |

## Architecture

1. **Wykrycie wejścia:** Po ścieżce w `input_dir` + `os.path` — jeśli rozszerzenie (case-insensitive) to `.pdf`, gałąź PDF; w przecznym razie obecna ścieżka `Image.open` dla rastrów.
2. **Render PDF:** Otworzenie dokumentu w PyMuPDF, iteracja po stronach, render każdej strony do pixmapy (rozsądna rozdzielczość — np. domyślna matryca `fitz` / DPI z ustalonym sane default, żeby tekst był czytelny i rozmiar pod kontrolą; unikać nadmiernych pikseli przed późniejszym `resize // 2`).
3. **Sklejenie pionowe:** Strony o różnej szerokości: **wyrównać do maksymalnej szerokości** (dla węższych stron: białe tło, wyśrodkowanie poziome lub wyrównanie do lewej — **rekomendacja: wyśrodkowanie** na białym tle, żeby oś wizualna była spójna). Wysokość wynikowa = suma wysokości po ewentualnym dopasowaniu szerokości. Wynik: jeden `PIL.Image` w RGB.
4. **Dalszy przebieg:** Identyczny jak dziś od momentu posiadania obrazu PIL w pamięci: resize, flatten alpha jeśli kiedykolwiek wystąpi, zapis JPEG do `output_path`, zwrot `output_path` jak dotąd.
5. **Pojedynczy punkt wejścia:** Rozszerzyć `preprocess_image` (lub wydzielić prywatne `\_render_pdf_to_pil` / `\_stack_pages_vertically` w tym samym module, by testy były czytelne) — **wszystkie** wywołujące miejsca (`_process_single_file`, reupload, ground truth, ewaluacja) korzystają z tej samej usługi bez duplikacji.

## Error handling

- **0 stron, uszkodzony plik, PDF z hasłem:** Jasny wyjątek lub komunikat w `message` w repozytorium (tak jak obecne błędy pipeline), bez częściowego zapisu do MinIO.
- **Bardzo duże PDF (pamięć):** Ewentualny bezpiecznik (limit stron / max wymiary po renderze) — **YAGNI na v1** chyba że podczas implementacji pokaże się realny problem; w spec pozostawiam opcjonalny follow-up, nie wymagamy w pierwszym MERGE.
- Pliki tymczasowe: preferuj pracę w pamięci (`PIL` + pixmapy) bez zbędnych plików dyskowych; jeśli temp files — `tempfile` + `finally` cleanup.

## Dependencies

- `backend/requirements.txt`: dodać `pymupdf` z wersją przypiętą (np. po `pip install` weryfikacja kompatybilności z 3.11).
- `backend/Dockerfile`: tylko jeśli build wymaga dodatkowego kroku (zwykle `pip` wystarczy); **nie** dodawać `poppler-utils` o ile PyMuPDF wystarcza.

## Frontend (opcjonalnie w tej samej pracy)

Miejsca z `accept="image/*"` dla paragonów: rozważyć `accept="image/*,application/pdf"` tylko tam, gdzie użytkownik realnie wgrywa plik paragonu z przeglądarki, żeby PDF dało się wybrać w dialugu pliku. Nie blokuje backendu; można zrobić w osobnym komicie / PR.

## Testing

- **Unit:** Mock lub mały fixture PDF (1 strona, 2 strony) — asercja, że wynik ma oczekiwany rozmiar / liczbę „pasów” pionowych (np. wysokość zależna od sumy stron) i że `.jpg` istnieje w `output_dir`.
- **Regresja:** Istniejące testy `PreprocessingService` z PNG/JPG pozostają zielone.
- **Integracja (opcjonalnie):** Jedna ścieżka w `test_pipeline` z plikiem PDF w `input/`, jeśli koszt utrzymania niski.

## Out of scope

- Osobne traktowanie PDF w API OCR (wejście natywne PDF) — **nie**; wszystko idzie przez jeden obraz JPEG.
- Wybór „tylko strona 1” przez użytkownika w UI — **nie** w tej iteracji.
- Analiza treści wektorowej PDF (tekst bez renderu) — **nie**.

## Success criteria

- Plik taki jak `PN_26634_04_26_MG.pdf` po przetworzeniu dostaje `status` końcowy zgodny z sukcesem reszty pipeline, `minio_object_key` ustawiony, OCR wykonany.
- Dla wielu stron OCR dostaje **jeden** długi obraz; jakość odczytu akceptowalna dla typowych paragonów (ewentualne strojenie DPI w późniejszej iteracji).

## References (code)

- `backend/src/services/preprocessing.py` — główna zmiana.
- `backend/src/app.py` — `_process_single_file`, reupload, ground truth (pośrednio).
- `backend/Dockerfile`, `backend/requirements.txt` — zależności.
