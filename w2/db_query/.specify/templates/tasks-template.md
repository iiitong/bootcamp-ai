---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`
- Backend models: `backend/src/models/` (Pydantic with camelCase aliases)
- Frontend types: `frontend/src/types/` (TypeScript interfaces)
- API routes: `backend/src/api/`

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan (backend/, frontend/)
- [ ] T002 Initialize Python backend with FastAPI and Pydantic v2 dependencies
- [ ] T003 [P] Initialize TypeScript frontend with strict mode enabled
- [ ] T004 [P] Configure mypy with strict mode for backend
- [ ] T005 [P] Configure camelCase JSON serialization in Pydantic base model

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**Constitution Compliance**:
- Pydantic base model with `alias_generator = to_camel` configured
- TypeScript strict mode verified
- mypy passing with no errors

- [ ] T006 Create Pydantic base model with camelCase serialization in backend/src/models/base.py
- [ ] T007 [P] Create TypeScript API client types matching Pydantic schemas
- [ ] T008 [P] Setup API routing with FastAPI
- [ ] T009 Setup error handling with typed error responses
- [ ] T010 Configure environment variables (no auth needed)

**Checkpoint**: Foundation ready - all responses use camelCase, types are strict

---

## Phase 3: User Story 1 - [Title] (Priority: P1)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

**Constitution Checklist**:
- [ ] All Pydantic models inherit from camelCase base
- [ ] All Python functions have type hints
- [ ] TypeScript interfaces match API response shapes
- [ ] No authentication barriers

### Tests for User Story 1 (OPTIONAL - only if tests requested)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Contract test verifying camelCase response in tests/contract/
- [ ] T012 [P] [US1] Integration test for user journey in tests/integration/

### Implementation for User Story 1

- [ ] T013 [P] [US1] Create Pydantic model in backend/src/models/ (with type hints)
- [ ] T014 [P] [US1] Create TypeScript interface in frontend/src/types/ (matching model)
- [ ] T015 [US1] Implement service in backend/src/services/ (fully typed)
- [ ] T016 [US1] Implement API endpoint in backend/src/api/ (returns camelCase)
- [ ] T017 [US1] Implement frontend component in frontend/src/components/ (typed props)

**Checkpoint**: User Story 1 functional, types passing, JSON is camelCase

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

[Same structure as Phase 3]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX Verify all API responses use camelCase (contract tests)
- [ ] TXXX Run mypy --strict on entire backend
- [ ] TXXX Run tsc --noEmit on entire frontend
- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
  - CRITICAL: camelCase base model must be complete before any API work
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### Constitution Verification Points

- After Phase 2: Run mypy/tsc to verify type infrastructure
- After each User Story: Verify camelCase JSON output
- Before merge: Full type check (mypy --strict + tsc --noEmit)

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- Backend Pydantic models and Frontend TypeScript types can be developed in parallel
- Different user stories can be worked on in parallel by different team members

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All Pydantic models MUST use the camelCase base model
- All TypeScript MUST pass strict mode checks
- No authentication code should be added
- Commit after each task or logical group
