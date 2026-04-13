# OCR Lidl Discount Prompt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one prompt bullet to `OCRService` so the model reliably classifies Lidl Plus kupons/vouchers and multi-buy promotions as negative-price discount entries.

**Architecture:** Single string insertion in `OCRService.__init__()` — between the existing `Rabat <name>` bullet and the closing summary sentence. A matching unit test asserts the new text is present in `self.prompt`.

**Tech Stack:** Python 3.11, pytest ≥ 8.0

---

### Task 1: Add prompt bullet and test it

**Files:**
- Modify: `backend/src/services/ocr.py:30`
- Modify: `backend/tests/unit/test_services_llm.py`

- [ ] **Step 1: Write the failing test**

Open `backend/tests/unit/test_services_llm.py` and add this test inside `TestOCRService` (after the last existing test method):

```python
def test_prompt_contains_lidl_discount_rules(self):
    # Arrange
    svc = OCRService(client=MagicMock(), async_client=MagicMock())

    # Assert — both concrete examples and the general guard are present
    assert "Lidl Plus kupon" in svc.prompt
    assert "Lidl Plus voucher" in svc.prompt
    assert "Taniej za 2" in svc.prompt
    assert "Never assign a positive price" in svc.prompt
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /home/pawel/eye-budget && source venv/bin/activate && python -m pytest backend/tests/unit/test_services_llm.py::TestOCRService::test_prompt_contains_lidl_discount_rules -v
```

Expected: `FAILED` — `AssertionError` on the first missing string.

- [ ] **Step 3: Add the new bullet to the prompt**

In `backend/src/services/ocr.py`, replace line 30:

```python
            "   - In all cases, discounts and rebates must appear in the product list with a negative price. "
```

with:

```python
            "   - Loyalty-card discounts (e.g. 'Lidl Plus kupon', 'Lidl Plus voucher') and multi-buy promotions "
            "     (e.g. 'Taniej za 2', 'Taniej z 2') always carry a negative price — add each as a separate "
            "     product entry. Never assign a positive price to a line that is clearly a discount or promotion. "
            "   - In all cases, discounts and rebates must appear in the product list with a negative price. "
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd /home/pawel/eye-budget && source venv/bin/activate && python -m pytest backend/tests/unit/test_services_llm.py::TestOCRService::test_prompt_contains_lidl_discount_rules -v
```

Expected: `PASSED`

- [ ] **Step 5: Run the full unit suite to check for regressions**

```bash
cd /home/pawel/eye-budget && source venv/bin/activate && python -m pytest backend/tests/unit/ -v
```

Expected: all tests pass (no failures).

- [ ] **Step 6: Commit**

```bash
cd /home/pawel/eye-budget && git add backend/src/services/ocr.py backend/tests/unit/test_services_llm.py && git commit -m "feat: add Lidl Plus and multi-buy discount rules to OCR prompt"
```
