<!--
SYNC IMPACT REPORT
==================
Version change: N/A → 1.0.0 (Initial adoption)
Added sections:
  - Core Principles (5 principles)
  - Technology Stack
  - Development Workflow
  - Governance
Modified principles: N/A (initial)
Removed sections: N/A (initial)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ created
  - .specify/templates/spec-template.md ✅ created
  - .specify/templates/tasks-template.md ✅ created
Follow-up TODOs: None
-->

# DB Query Constitution

## Core Principles

### I. Ergonomic Python Backend

All backend code MUST be written in idiomatic, readable Python following
Ergonomic Python principles:

- Code MUST favor clarity over cleverness
- Functions MUST have single, well-defined responsibilities
- Variable and function names MUST be descriptive and self-documenting
- Complex logic MUST be broken into composable, testable units
- List comprehensions and generators SHOULD be preferred over explicit loops
  when they improve readability

**Rationale**: Ergonomic code reduces cognitive load, accelerates onboarding,
and minimizes bugs caused by misunderstanding intent.

### II. TypeScript Frontend

All frontend code MUST be written in TypeScript with strict compiler settings:

- `strict: true` MUST be enabled in tsconfig.json
- `noImplicitAny: true` MUST be enforced
- All component props MUST have explicit type definitions
- API response types MUST be defined and match backend contracts
- Generic types SHOULD be used to ensure type safety across data flows

**Rationale**: TypeScript catches errors at compile time, provides superior
IDE support, and documents intent through types.

### III. Strict Type Annotations

Both backend and frontend MUST maintain complete type coverage:

- **Python**: All function parameters and return types MUST have type hints
- **Python**: All class attributes MUST be typed
- **TypeScript**: No `any` types unless explicitly justified and documented
- Type definitions MUST be kept in sync between frontend and backend
- CI/CD pipelines SHOULD enforce type checking (mypy for Python, tsc for TS)

**Rationale**: Strict typing prevents runtime errors, enables refactoring with
confidence, and serves as living documentation.

### IV. Pydantic Data Models

All backend data models MUST use Pydantic for definition and validation:

- Request/response schemas MUST be Pydantic models
- Database models SHOULD use Pydantic for serialization
- Validation rules MUST be encoded in model definitions, not scattered in code
- Field descriptions SHOULD be provided for API documentation generation
- Model inheritance SHOULD be used to reduce duplication

**Rationale**: Pydantic provides automatic validation, serialization, and
OpenAPI schema generation, reducing boilerplate and ensuring consistency.

### V. CamelCase JSON Serialization

All backend-generated JSON MUST use camelCase field naming:

- Pydantic models MUST configure `alias_generator = to_camel` or equivalent
- API responses MUST serialize with `by_alias=True`
- Frontend TypeScript interfaces MUST match the camelCase API contract
- Internal Python code uses snake_case; conversion happens at serialization
- Test fixtures SHOULD verify camelCase output

**Rationale**: camelCase aligns with JavaScript/TypeScript conventions, making
frontend integration seamless and reducing field name mapping errors.

## Technology Stack

**Backend**:
- Language: Python 3.11+
- Framework: FastAPI (recommended) or equivalent async framework
- Data Models: Pydantic v2
- Type Checking: mypy with strict mode

**Frontend**:
- Language: TypeScript 5.0+
- Framework: TBD (React, Vue, or equivalent)
- Build Tool: TBD (Vite, Next.js, or equivalent)

**Storage**: TBD (to be determined based on feature requirements)

**Authentication**: Not required - open access for all users

## Development Workflow

### Code Review Requirements

- All PRs MUST pass type checking (mypy + tsc) before merge
- All PRs MUST include type annotations for new code
- Pydantic model changes MUST update corresponding TypeScript types
- Breaking API changes MUST update both backend and frontend types atomically

### Testing Expectations

- Unit tests SHOULD cover business logic
- Contract tests SHOULD verify API schema compliance
- Integration tests SHOULD cover end-to-end user flows

### Documentation

- API documentation auto-generated from Pydantic models via OpenAPI
- Complex business logic SHOULD include docstrings
- Type definitions serve as primary interface documentation

## Governance

This constitution establishes the non-negotiable architectural principles for
the DB Query project. All implementation decisions MUST align with these
principles.

### Amendment Procedure

1. Propose changes via pull request modifying this file
2. Document rationale for each principle change
3. Update version following semantic versioning:
   - MAJOR: Principle removal or backward-incompatible redefinition
   - MINOR: New principle or materially expanded guidance
   - PATCH: Clarifications, typo fixes, non-semantic refinements
4. Update dependent templates if principles affect their content
5. Obtain team consensus before merge

### Compliance Review

- Code reviews MUST verify adherence to these principles
- Exceptions require documented justification in the PR description
- Repeated violations warrant process improvement discussion

**Version**: 1.0.0 | **Ratified**: 2025-12-13 | **Last Amended**: 2025-12-13
