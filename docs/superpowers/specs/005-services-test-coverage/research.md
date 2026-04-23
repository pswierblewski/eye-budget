# Research: Backend Services Test Coverage

**Phase**: 0 — Research  
**Feature**: 005-services-test-coverage  
**Date**: 2026-03-30

---

## Decision 1: LLM client injection strategy

**Decision**: Refactor the five LLM services that create their `OpenAI` / `AsyncOpenAI` clients internally to accept optional injected client parameters — mirroring the pattern already in `BudgetSimulationService`.

**Services requiring refactor**:
| Service | Change |
|---------|--------|
| `OCRService` | Add `client: OpenAI | None = None`, `async_client: AsyncOpenAI | None = None` params |
| `CategoriesService` | Add `client: OpenAI | None = None` param |
| `BankCategorizationService` | Add `client: OpenAI | None = None`, `async_client: AsyncOpenAI | None = None` params |
| `ProductsService` | Add `client: OpenAI | None = None` param |
| `VendorsService` | Add `client: OpenAI | None = None` param |

**Pattern** (matches `BudgetSimulationService` lines 35–40):
```python
def __init__(self, ..., client: OpenAI | None = None):
    self.client = client if client is not None else OpenAI()
```

**Rationale**: Module-level patching (`mock.patch("openai.OpenAI")`) is banned by FR-003. Constructor injection is the established DI pattern from 003-backend-app-tests. `BudgetSimulationService` is the canonical reference.

**Alternatives considered**:
- Module-level `mock.patch` — rejected (violates FR-003).
- Environment-variable disabling of real client — rejected (fragile, non-deterministic).

**Impact on `App`**: `App.__init__` currently constructs these services without injection. After the refactor it still works unchanged — the `client` param defaults to `None`, which falls back to the real client in production. No change to `App.__init__` is required.

---

## Decision 2: Async variant coverage

**Decision**: Test both sync and async variants for the three services that expose both: `OCRService` (`process_image` / `process_image_async`), `BankCategorizationService` (`assign_candidates` / `assign_candidates_async`), and `EvaluationService` (`run_evaluation` / `run_evaluation_async`).

**Rationale**: The async paths contain non-trivial orchestration (semaphore, asyncio Lock, gather with concurrency limit) that can fail independently of the sync path. Leaving them untested undermines the ≥80% coverage gate (SC-003).

**Async test approach**: Use `pytest-asyncio` (already available transitively via `testcontainers`) with `@pytest.mark.asyncio` decorator, or use `asyncio.run()` inside a sync test for simple cases.

**Alternatives considered**:
- Test sync only, assume async is a thin wrapper — rejected (async orchestration is substantive, not thin).

---

## Decision 3: `MarkdownTableService` is ABC but has no abstract methods

**Decision**: Instantiate `MarkdownTableService` directly in tests — no concrete subclass needed.

**Rationale**: The class inherits from `ABC` but declares no `@abstractmethod`, so Python allows direct instantiation. This simplifies test setup.

**Alternatives considered**:
- Create a minimal concrete subclass — rejected (unnecessary boilerplate given direct instantiation works).

---

## Decision 4: `PreprocessingService` test isolation

**Decision**: Use `tempfile.NamedTemporaryFile` / `tempfile.TemporaryDirectory` for test images. Generate a minimal valid JPEG in-memory (1×1 pixel) using `PIL.Image` in the test itself — no checked-in fixture files.

**Rationale**: Keeps tests self-contained; no binary fixtures to maintain in the repo. PIL is already a production dependency.

---

## Decision 5: `TextLocalizationService` mock strategy

**Decision**: Mock the PaddleOCR engine at constructor-injection level. `TextLocalizationService.__init__` accepts `ocr=None`; when `None`, it creates PaddleOCR. In tests, pass a `MagicMock()` instance.

**Rationale**: PaddleOCR requires a GPU-compatible PaddlePaddle installation. It MUST NOT be imported in unit test runs. The mock is injected via the constructor, consistent with FR-003.

**Verification**: Confirm `TextLocalizationService` already accepts `ocr` param — if not, add it (same refactor pattern as LLM services).

---

## Decision 6: Test file organisation

**Decision**: Five new unit test files under `backend/tests/unit/`:

| File | Services covered |
|------|-----------------|
| `test_services_pure.py` | `PekaoCsvParser`, `MarkdownTableService`, `TextMatchingService` |
| `test_services_llm.py` | `OCRService`, `CategoriesService`, `BankCategorizationService`, `ProductsService`, `VendorsService`, `BudgetSimulationService` |
| `test_services_infra.py` | `MinioStorageService`, `PusherService` |
| `test_services_domain.py` | `BudgetAnalysisService`, `BudgetGoalsService`, `GroundTruthService`, `EvaluationService.calculate_metrics`, `EvaluationService.run_evaluation_async` |
| `test_services_image.py` | `PreprocessingService`, `TextLocalizationService` |

**Rationale**: Groups by external dependency type — aligns with User Stories 1-5 in spec. Each file is independently runnable.

---

## Decision 7: `pytest-asyncio` availability

**Decision**: Use `asyncio.run()` for simple async tests rather than adding `pytest-asyncio` as a new dependency, unless `pytest-asyncio` is already transitively available.

**Research finding**: `requirements-test.txt` does NOT list `pytest-asyncio` directly. Add it explicitly:
```
pytest-asyncio>=0.23
```

**Rationale**: `asyncio.run()` inside a sync test works for simple cases, but `pytest-asyncio` with `@pytest.mark.asyncio` is cleaner for `async def` tests and avoids event-loop management issues.

---

## Decision 8: Coverage configuration

**Decision**: Add/update `pytest.ini` or `pyproject.toml` to set `--cov=src/services --cov-fail-under=80` when running the service test files, or document as a separate coverage invocation.

**Research finding**: No `pyproject.toml` or `pytest.ini` was found in the research. The project likely runs pytest without a config file. Add a `[tool.pytest.ini_options]` section or `pytest.ini` to define addopts for coverage.

**Rationale**: SC-003 requires ≥80% statement coverage for `src/services/`. This gate must be enforced by the test runner, not just documented.
