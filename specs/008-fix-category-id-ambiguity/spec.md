# Feature Specification: Fix Ambiguous Column in Category Creation

**Feature Branch**: `008-fix-category-id-ambiguity`  
**Created**: 2026-04-01  
**Status**: Draft  
**Input**: User description: "chcę mieć ten błąd naprawiony"

## Context

When a user attempts to create a new expense category, the operation fails with HTTP 500. Investigation on the server revealed the error message: `column reference "id" is ambiguous`. The SQL query that checks for an existing category with the same name performs a self-join on the `categories` table but does not qualify the `id` column with a table alias, causing PostgreSQL to reject the query.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Create a New Category Successfully (Priority: P1)

A user opens the category management view and adds a new expense category (with or without a parent). The system saves the category and returns it without errors.

**Why this priority**: This is the core broken flow — the entire create-category feature is currently non-functional due to this bug.

**Independent Test**: Submit a create-category request with a valid name and optional parent; verify the category is returned and appears in the category list without any server error.

**Acceptance Scenarios**:

1. **Given** a valid category name and no parent, **When** the user submits the create-category form, **Then** the category is created and visible in the list with no error.
2. **Given** a valid category name and an existing parent category, **When** the user submits the form, **Then** the child category is created and linked to the parent.
3. **Given** the same category name and parent already exist, **When** the user submits the form again, **Then** the existing category is returned without creating a duplicate.

---

### Edge Cases

- What happens when the provided parent category does not exist?
- What happens if the database connection is unavailable at request time?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST successfully create a new expense category without returning a server error.
- **FR-002**: The system MUST correctly identify duplicate categories (same name and same parent) and return the existing record instead of inserting a new one.
- **FR-003**: The system MUST return the created (or existing) category including its identifier, name, and parent name.
- **FR-004**: The system MUST roll back any partial database changes if an error occurs during category creation.

### Key Entities

- **Category**: An expense classification with a unique identifier, a name, an optional parent category, and a fixed type (`expense`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A create-category request with a valid payload succeeds (no server error) 100% of the time under normal operating conditions.
- **SC-002**: No regression — all existing category-related operations (listing categories, assigning a category to a transaction) continue to work correctly after the fix.
- **SC-003**: The bug fix is covered by at least one automated test that would have detected this failure before deployment.

## Assumptions

- The fix requires only a correction of the duplicate-check query — no schema changes, no API contract changes, and no frontend changes.
- Existing rollback-on-failure behaviour is correct and must be preserved.
- No other endpoints are affected by this specific query issue.
