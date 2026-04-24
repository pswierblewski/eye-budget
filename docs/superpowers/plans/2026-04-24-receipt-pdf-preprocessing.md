# Receipt PDF preprocessing — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow `.pdf` receipt files to flow through the same MinIO and OCR pipeline as images by rendering all pages with PyMuPDF, stacking them vertically (max-width canvas, narrower pages centered on white), then applying the existing half-scale JPEG pre-processing.

**Architecture:** Detect PDF by filename extension in `PreprocessingService.preprocess_image()`. If PDF, use `fitz` to render each page to RGB pixmaps, convert to `PIL.Image`, pad/center to common width, concatenate vertically, then hand off to a shared helper that contains today’s logic (halve size, mode handling, progressive JPEG to `output_dir`). Rasters use `Image.open` as today, then the same helper. No changes to `app.py` pipeline wiring; only `preprocessing.py`, `requirements.txt`, and tests.

**Tech stack:** Python 3.11, `pymupdf` (import `fitz`), `Pillow` (existing).

**Spec:** `docs/superpowers/specs/2026-04-24-receipt-pdf-preprocessing-design.md`

## File map

| File | Role |
|------|------|
| `backend/requirements.txt` | Add `pymupdf` with pinned version. |
| `backend/src/services/preprocessing.py` | PDF branch, shared JPEG writer from `PIL.Image`, helpers for path detection and vertical stack. |
| `backend/Dockerfile` | No `apt` change (PyMuPDF wheels); only rebuild after `pip install` picks up new requirements. |
| `backend/tests/unit/test_services_image.py` | New tests in `TestPreprocessingService` for PDF (1-page, 2-page width mismatch, errors). |
| `frontend/app/ground-truth/page.tsx` (optional) | Widen `accept` to allow PDF in file picker. |

---

### Task 1: Add `pymupdf` to backend dependencies

**Files:**
- Modify: `backend/requirements.txt`
- Test: `cd backend && .venv/bin/pip install -r requirements.txt` (no new test file yet)

- [ ] **Step 1: Pin dependency**

Append after the `pillow` line (or alphabetically; keep the file style consistent — currently loosely grouped):

```text
pymupdf==1.27.2.2
```

- [ ] **Step 2: Install in local venv**

```bash
cd /home/pawel/eye-budget/backend
.venv/bin/pip install -r requirements.txt
```

Expected: installs `pymupdf` without error.

- [ ] **Step 3: Verify import**

```bash
.venv/bin/python -c "import fitz; print(fitz.__doc__[:40])"
```

Expected: no `ImportError`.

- [ ] **Step 4: Commit**

```bash
cd /home/pawel/eye-budget
git add backend/requirements.txt
git commit -m "chore: add pymupdf for PDF receipt rendering"
```

---

### Task 2: Refactor + PDF — shared JPEG path, then `fitz` branch

**Files:**
- Modify: `backend/src/services/preprocessing.py`
- Test: `backend/tests/unit/test_services_image.py` (Task 2 steps must stay green after raster-only refactor; add PDF tests in Task 4)

**Implementation order in one working tree (avoid committing a broken `preprocess_image`):** first add `_is_pdf_filename`, `_write_preprocessed_jpeg`, and change the raster branch to `with Image.open(...): return self._write_preprocessed_jpeg(...)`; then immediately add the PDF helper functions and `if _is_pdf_filename` branch as in **Task 3** below, run tests, then commit once (or use two local commits: refactor, then feat — but do not push intermediate state with missing PDF if `main` is shared).

- [ ] **Step 1: Add `_is_pdf_filename` and `_write_preprocessed_jpeg`**

In `preprocessing.py`, add after imports:

```python
def _is_pdf_filename(path: str) -> bool:
    return os.path.splitext(path)[1].lower() == ".pdf"
```

Add to `PreprocessingService`:

```python
def _write_preprocessed_jpeg(self, image: "Image.Image", output_path: str) -> str:
    """Apply half-size resize, mode normalization, and JPEG write. Does not close `image`."""
    new_size = (image.width // 2, image.height // 2)
    resized_img = image.resize(new_size, Image.Resampling.LANCZOS)
    if resized_img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", resized_img.size, (255, 255, 255))
        background.paste(
            resized_img,
            mask=resized_img.split()[-1] if resized_img.mode in ("RGBA", "LA") else None,
        )
        resized_img = background
    elif resized_img.mode != "RGB":
        resized_img = resized_img.convert("RGB")
    os.makedirs(self.output_dir, exist_ok=True)
    resized_img.save(
        output_path,
        format="JPEG",
        quality=_JPEG_QUALITY,
        optimize=True,
        progressive=True,
    )
    return output_path
```

- [ ] **Step 2: Keep raster path working**

Non-PDF:

```python
with Image.open(input_image_path) as img:
    return self._write_preprocessed_jpeg(img, output_path)
```

Run: `pytest tests/unit/test_services_image.py::TestPreprocessingService -q` → 2 passed.

- [ ] **Step 3: Proceed to Task 3 (same file)** — add `import fitz`, PDF helpers, and the `if _is_pdf_filename` block; then a single commit covering Tasks 2+3 together is fine.

---

### Task 3: PDF: render, stack vertically, center narrow pages

**Files:**
- Modify: `backend/src/services/preprocessing.py`
- Test: (Task 4)

- [ ] **Step 1: Add imports** at top of `preprocessing.py`:

```python
import fitz
```

(If the team prefers lazy import inside PDF-only functions to speed cold start, use `import fitz` inside ` _pdf_stacked_to_rgb` instead — both are acceptable; pick one and keep it.)

- [ ] **Step 2: Implement PDF loader**

Add a function (module-level or `@staticmethod` private helper) with this behavior — **concrete code:**

```python
def _page_to_rgb_image(page: fitz.Page, matrix: fitz.Matrix) -> Image.Image:
    pix = page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csRGB)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

def _stack_pages_vertically(page_images: list[Image.Image]) -> Image.Image:
    if not page_images:
        raise ValueError("PDF has no pages to render")
    max_w = max(im.width for im in page_images)
    strips: list[Image.Image] = []
    for im in page_images:
        if im.width == max_w:
            strips.append(im if im.mode == "RGB" else im.convert("RGB"))
            continue
        if im.mode != "RGB":
            im = im.convert("RGB")
        canvas = Image.new("RGB", (max_w, im.height), (255, 255, 255))
        x_off = (max_w - im.width) // 2
        canvas.paste(im, (x_off, 0))
        strips.append(canvas)
    total_h = sum(s.height for s in strips)
    out = Image.new("RGB", (max_w, total_h), (255, 255, 255))
    y = 0
    for s in strips:
        out.paste(s, (0, y))
        y += s.height
    return out

def _load_stacked_pil_from_pdf(pdf_path: str) -> Image.Image:
    doc = fitz.open(pdf_path)
    try:
        if doc.is_encrypted and not doc.authenticate(""):
            raise ValueError("PDF is password-protected or encrypted")
        if doc.page_count < 1:
            raise ValueError("PDF has no pages")
        matrix = fitz.Matrix(2, 2)
        page_images: list[Image.Image] = []
        for i in range(doc.page_count):
            page = doc.load_page(i)
            page_images.append(_page_to_rgb_image(page, matrix))
    finally:
        doc.close()
    return _stack_pages_vertically(page_images)
```

Rationale: `fitz.Matrix(2, 2)` matches 2× zoom; combined with the existing `// 2` in `_write_preprocessed_jpeg` the effective downscale is similar to a 1× render then half — adjust only if on-device memory tests fail (YAGNI for v1).

- [ ] **Step 3: Wire `preprocess_image`**

```python
def preprocess_image(self, image_path: str) -> str:
    input_image_path = os.path.join(self.input_dir, image_path)
    stem = os.path.splitext(os.path.basename(image_path))[0]
    output_filename = f"{stem}.jpg"
    output_path = os.path.join(self.output_dir, output_filename)
    if _is_pdf_filename(image_path):
        stacked = _load_stacked_pil_from_pdf(input_image_path)
        try:
            return self._write_preprocessed_jpeg(stacked, output_path)
        finally:
            stacked.close()
    with Image.open(input_image_path) as img:
        return self._write_preprocessed_jpeg(img, output_path)
```

- [ ] **Step 4: Run existing tests + manual smoke on tiny PDF**

```bash
.venv/bin/pytest tests/unit/test_services_image.py::TestPreprocessingService -q
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/preprocessing.py
git commit -m "feat: preprocess PDF receipts as vertically stacked page images"
```

---

### Task 4: Unit tests — synthetic PDFs with PyMuPDF

**Files:**
- Modify: `backend/tests/unit/test_services_image.py`
- Reuse: `TestPreprocessingService` class

- [ ] **Step 1: Add builder helper** above `TestPreprocessingService`:

```python
def _build_pdf(tmp_path, pages: list[tuple[int, int]], name: str = "doc.pdf") -> str:
    """Create a minimal PDF: each entry is (width, height) in points for one page."""
    import fitz
    doc = fitz.open()
    for w, h in pages:
        doc.new_page(width=float(w), height=float(h))
    out = str(tmp_path / name)
    doc.save(out)
    doc.close()
    return out
```

- [ ] **Step 2: Test single-page PDF — expected pixel size**

With `fitz.new_page(width=200, height=100)` (points) and `fitz.Matrix(2, 2)` + `get_pixmap`, pixmap size is **400×200** px. After `_write_preprocessed_jpeg` (half), output JPEG is **200×100** px.

```python
def test_preprocess_pdf_one_page(self, tmp_path):
    import fitz
    pdf_path = str(tmp_path / "one.pdf")
    doc = fitz.open()
    doc.new_page(width=200, height=100)
    doc.save(pdf_path)
    doc.close()

    svc = PreprocessingService()
    svc.input_dir = str(tmp_path)
    svc.output_dir = str(tmp_path / "out")
    os.makedirs(svc.output_dir, exist_ok=True)

    out = svc.preprocess_image("one.pdf")
    with Image.open(out) as im:
        assert im.width == 200
        assert im.height == 100
    assert out.endswith("one.jpg")
```

- [ ] **Step 3: Test two pages, different widths**

Use page A `300×50` pt and page B `150×40` pt. Pixmaps at 2×: A = 600×100 px, B = 300×80 px, padded to 600 wide → strip B height 80, stack total 600×180 px, half → **300×90** px.

```python
def test_preprocess_pdf_two_pages_stack_dimensions(self, tmp_path):
    import fitz
    path = str(tmp_path / "two.pdf")
    doc = fitz.open()
    doc.new_page(width=300, height=50)
    doc.new_page(width=150, height=40)
    doc.save(path)
    doc.close()

    svc = PreprocessingService()
    svc.input_dir = str(tmp_path)
    svc.output_dir = str(tmp_path / "out2")
    os.makedirs(svc.output_dir, exist_ok=True)

    out = svc.preprocess_image("two.pdf")
    with Image.open(out) as im:
        assert im.width == 300
        assert im.height == 90
```

- [ ] **Step 4: Corrupt / non-PDF file**

`fitz` cannot save a 0-page PDF (save errors). Rely on **corrupt** bytes: write `b"not a real pdf"` to `bad.pdf` and use `pytest.raises` — expect a raised exception from `preprocess_image` (exact type: whatever `fitz.open` or PIL raises, e.g. `fitz.fitz.FileDataError` or `RuntimeError` — pin in test with a tuple `(Exception,)` or match message). Alternatively assert `raises` for `OSError`/`ValueError` if you normalize errors in a single `try/except` in `preprocess_image` (YAGNI: prefer letting exceptions propagate; test the concrete first exception type you observe in CI).

- [ ] **Step 5: Run tests**

```bash
.venv/bin/pytest tests/unit/test_services_image.py::TestPreprocessingService -q
```

- [ ] **Step 6: Commit**

```bash
git add backend/tests/unit/test_services_image.py
git commit -m "test: cover PDF preprocessing and error paths"
```

---

### Task 5: Full unit suite (backend)

**Files:** n/a (verification)

- [ ] **Step 1: Run full unit tests**

```bash
cd /home/pawel/eye-budget/backend
.venv/bin/pytest tests/unit/ -q --tb=short
```

Expected: all pass. Fix any import side effects from `fitz` in unrelated tests (unlikely).

- [ ] **Step 2: Commit** only if fixes were needed; otherwise no commit.

---

### Task 6 (optional): Ground-truth upload accepts PDF

**Files:**
- Modify: `frontend/app/ground-truth/page.tsx`

- [ ] **Step 1: Extend `accept` on the file input**

From `accept="image/*"` to:

```tsx
accept="image/*,application/pdf"
```

(Only if the ground-truth flow posts the file to an endpoint that stores it under `input/` the same as images; confirm in `ground_truth` service — if the API rejects non-image MIME, add backend `UploadFile` validation in a follow-up. If unsure, **skip** this task.)

- [ ] **Step 2: Commit**

```bash
git add frontend/app/ground-truth/page.tsx
git commit -m "feat(ground-truth): allow PDF in receipt upload"
```

---

## Spec coverage (self-review)

| Spec section | Task |
|-------------|------|
| PyMuPDF, no poppler in Docker | Task 1 |
| `.pdf` detection case-insensitive | Task 2/3 — `_is_pdf_filename` |
| All pages, vertical, max width, center narrow | Task 3 — `_stack_pages_vertically` |
| Same half-resize + JPEG as images | Task 2 + 3 — `_write_preprocessed_jpeg` |
| Encrypted / 0 pages error | Task 3 `authenticate` + `page_count`; Task 4 tests |
| `requirements.txt` | Task 1 |
| No Dockerfile `apt` | Documented in plan header; no task |
| Optional frontend | Task 6 |
| Regression raster tests | Task 2, 4, 5 |

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-24-receipt-pdf-preprocessing.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.  
2. **Inline Execution** — Execute tasks in this session using *executing-plans*, batch execution with checkpoints.

Which approach do you prefer?
