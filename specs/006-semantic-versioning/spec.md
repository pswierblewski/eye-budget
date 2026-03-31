# Feature Specification: Semantic Versioning Display

**Feature Branch**: `006-semantic-versioning`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "już mam zrobione cicd. Chcę teraz wersjonować ten projekt. Chcę wersjonować oddzielnie frontend i backend. Chcę na UI wyświetlać wersję obu. chcę użyć semantic versioning i zaczynamy od 1.0.0. wyświelanie wersji niech będzie na dole lewego sidebaru."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Current Application Versions (Priority: P1)

A developer or user opens the application and can see the current version of both the frontend and backend displayed at the bottom of the left sidebar. This gives instant visibility into what version is running, which is especially useful after a deployment.

**Why this priority**: Core deliverable — without visible version numbers, the entire feature has no user-facing value.

**Independent Test**: Can be tested by running the app and checking the bottom of the sidebar for version strings.

**Acceptance Scenarios**:

1. **Given** the application is running, **When** the user looks at the bottom of the left sidebar, **Then** they see the frontend version (e.g., "Frontend v1.0.0") and the backend version (e.g., "Backend v1.0.0") displayed.
2. **Given** the frontend version is `1.2.0` and the backend version is `1.1.3`, **When** the user opens the sidebar, **Then** both version strings are visible and correct.
3. **Given** the backend is unreachable, **When** the sidebar loads, **Then** the frontend version is still shown, and the backend version shows a graceful fallback (e.g., "Backend: unknown").

---

### User Story 2 - Increment Version on New Release (Priority: P2)

When a new release of the frontend or backend is deployed, the displayed version updates to reflect the new version. Frontend and backend versions are tracked independently — updating one does not affect the other.

**Why this priority**: Version display is only useful if versions actually advance with releases. This story covers the workflow that keeps versions in sync with deployments.

**Independent Test**: Can be tested by bumping the version in the version source file, deploying, and verifying the new version appears in the UI.

**Acceptance Scenarios**:

1. **Given** the current frontend version is `1.0.0`, **When** a new frontend release is prepared with version `1.1.0`, **Then** after deployment the sidebar shows "Frontend v1.1.0".
2. **Given** the current backend version is `1.0.0`, **When** a new backend release is prepared with version `1.0.1`, **Then** after deployment the sidebar shows "Backend v1.0.1".
3. **Given** the frontend version is bumped to `2.0.0`, **When** the backend version remains `1.0.0`, **Then** the sidebar shows both "Frontend v2.0.0" and "Backend v1.0.0" independently.

---

### Edge Cases

- What happens when the backend version endpoint is unavailable — the UI should not crash and should show a fallback value.
- What happens if a version string is malformed or missing — the UI shows a fallback rather than an empty or broken label.
- Both versions start at `1.0.0` and must be set explicitly before the first release.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain a version identifier for the frontend component, following Semantic Versioning (MAJOR.MINOR.PATCH), starting at `1.0.0`.
- **FR-002**: The system MUST maintain a version identifier for the backend component, following Semantic Versioning (MAJOR.MINOR.PATCH), starting at `1.0.0`.
- **FR-003**: Frontend and backend versions MUST be versioned independently — changing one does not change the other.
- **FR-004**: The UI MUST display both the frontend version and the backend version at the bottom of the left sidebar.
- **FR-005**: The backend MUST expose the current backend version through a dedicated public endpoint (no authentication required) accessible to the frontend.
- **FR-006**: The frontend MUST fetch the backend version once at application startup and cache it in memory for the duration of the session. The cached value is displayed in the sidebar without re-fetching on subsequent page navigations.
- **FR-007**: If the backend version cannot be retrieved, the UI MUST display a graceful fallback (e.g., "unknown") rather than crashing or showing an empty value.
- **FR-008**: Version values MUST be defined in a single authoritative source per component (one file/config for frontend, one for backend) — not duplicated across multiple locations.

### Key Entities

- **Frontend Version**: A semantic version string (MAJOR.MINOR.PATCH) representing the current release of the frontend application. Defined in one place in the frontend codebase.
- **Backend Version**: A semantic version string (MAJOR.MINOR.PATCH) representing the current release of the backend application. Defined in one place in the backend codebase and exposed via an API endpoint.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both version numbers are visible in the sidebar on every page of the application without any user action.
- **SC-002**: Frontend and backend versions can be bumped independently — verifiable by incrementing one and confirming only that version changes in the UI.
- **SC-003**: After a new deployment, the updated version is visible in the sidebar within the normal page load time (no additional user refresh required beyond normal navigation).
- **SC-004**: When the backend is unavailable, the sidebar version display degrades gracefully — the application remains fully functional and shows a fallback version string.
- **SC-005**: Each component version is defined in exactly one authoritative location, confirmed by there being a single point of change required to bump each version.

## Clarifications

### Session 2026-03-31

- Q: When should the frontend fetch the backend version — once at startup or on every page navigation? → A: Fetch once at app startup; cache in memory for the session lifetime.
- Q: Should the backend version endpoint require authentication? → A: Public endpoint — no authentication required.

## Assumptions

- The left sidebar (`Sidebar.tsx`) is already implemented and present on all pages; the version display will be added to its bottom section.
- The backend already has a health or info endpoint pattern in place; a `/version` or `/info` endpoint will follow the same conventions.
- Version bumping is a manual step performed by the developer before creating a release — no automated version bumping tool (e.g., semantic-release) is required at this stage.
- The version display is purely informational — no version-based feature flags, compatibility checks, or upgrade prompts are in scope.
- Both components start at version `1.0.0` for this feature.
