---
description: Perform deep code review for Python and TypeScript code focusing on architecture, design principles, and code quality.
handoffs:
  - label: Fix Critical Issues
    prompt: Fix the critical issues identified in the code review
  - label: Refactor for SOLID
    prompt: Refactor the reviewed code to better follow SOLID principles
  - label: Apply Builder Pattern
    prompt: Apply the builder pattern to the classes identified in the review
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Perform a deep, structured code review for Python and/or TypeScript code, focusing on architecture, design patterns, code quality principles, and language-specific best practices. This review produces actionable findings with severity ratings and concrete recommendations.

## Operating Constraints

- **READ-ONLY Analysis**: Do not modify any files unless explicitly requested
- **Language-Aware**: Apply Python-specific and TypeScript-specific best practices appropriately
- **Actionable Output**: Every finding must include a concrete recommendation
- **Builder Pattern Focus**: Identify opportunities to apply builder pattern for complex object construction

## Execution Steps

### 1. Determine Review Scope

Parse `$ARGUMENTS` to determine:

a. **Target specification**:
   - If path provided: Review that specific file/directory
   - If empty: Review recently modified files (`git diff --name-only HEAD~5` for Python/TypeScript files)
   - If pattern provided (e.g., `src/**/*.py`): Use glob to find matching files

b. **Language detection**:
   - `.py` files → Python review mode
   - `.ts`, `.tsx` files → TypeScript review mode
   - Mixed → Apply both rule sets appropriately

c. **Review depth** (inferred from scope size):
   - Single file: Deep review (all checks)
   - Module/directory: Standard review (critical + high checks)
   - Large codebase: Surface review (critical checks + sampling)

### 2. Load Review Targets

```bash
# For git-based scope
git diff --name-only HEAD~5 | grep -E '\.(py|ts|tsx)$'

# Or use provided path/pattern
```

Read each target file. For large files (>500 lines), note this as a potential issue.

### 3. Architecture & Design Analysis

#### 3.1 Python Architecture Checks

| Check ID | Check | Severity | Criteria |
|----------|-------|----------|----------|
| PY-ARCH-001 | Module Structure | HIGH | Each module should have clear, single responsibility |
| PY-ARCH-002 | Package Organization | MEDIUM | `__init__.py` should expose public API clearly |
| PY-ARCH-003 | Dependency Direction | HIGH | No circular imports; dependencies flow one direction |
| PY-ARCH-004 | Interface Abstraction | HIGH | Use ABC/Protocol for interfaces; depend on abstractions |
| PY-ARCH-005 | Configuration Separation | MEDIUM | Config separate from logic; use environment/config files |
| PY-ARCH-006 | Error Hierarchy | MEDIUM | Custom exceptions inherit from appropriate base classes |

#### 3.2 TypeScript Architecture Checks

| Check ID | Check | Severity | Criteria |
|----------|-------|----------|----------|
| TS-ARCH-001 | Module Boundaries | HIGH | Clear exports; barrel files (`index.ts`) for public API |
| TS-ARCH-002 | Type Definitions | HIGH | Interfaces/types in dedicated files or co-located logically |
| TS-ARCH-003 | Dependency Injection | MEDIUM | Dependencies injected, not hardcoded |
| TS-ARCH-004 | State Management | HIGH | Clear state ownership; immutable where appropriate |
| TS-ARCH-005 | API Layer Separation | HIGH | API calls isolated in service layer |
| TS-ARCH-006 | Component Architecture | MEDIUM | (React/Vue) Smart vs dumb component separation |

#### 3.3 Cross-Language Architecture

| Check ID | Check | Severity | Criteria |
|----------|-------|----------|----------|
| XL-ARCH-001 | Layer Separation | CRITICAL | Clear separation: presentation/business/data layers |
| XL-ARCH-002 | Interface Contracts | HIGH | Public interfaces are explicit and documented |
| XL-ARCH-003 | Extensibility Points | MEDIUM | Strategy/plugin points for future extension |
| XL-ARCH-004 | Coupling Assessment | HIGH | Low coupling between modules; high cohesion within |

### 4. KISS Principle Analysis

| Check ID | Check | Severity | Detection Pattern |
|----------|-------|----------|-------------------|
| KISS-001 | Over-Engineering | HIGH | Abstractions without multiple implementations |
| KISS-002 | Premature Generalization | MEDIUM | Generic solutions for single use case |
| KISS-003 | Unnecessary Complexity | HIGH | Nested conditionals >3 levels deep |
| KISS-004 | Clever Code | MEDIUM | One-liners that sacrifice readability |
| KISS-005 | Redundant Abstraction | MEDIUM | Wrapper classes that add no value |
| KISS-006 | Configuration Overload | LOW | Excessive configurability for simple features |

**KISS Violation Indicators**:
- Abstract factory for single concrete type
- Generic type parameters never varied
- Builder pattern for objects with <4 properties
- Strategy pattern with single strategy
- Multiple inheritance levels without clear benefit

### 5. Code Quality Analysis

#### 5.1 DRY (Don't Repeat Yourself)

| Check ID | Severity | Detection |
|----------|----------|-----------|
| DRY-001 | HIGH | Duplicate code blocks >10 lines |
| DRY-002 | MEDIUM | Similar logic patterns (70%+ similarity) |
| DRY-003 | MEDIUM | Repeated magic numbers/strings |
| DRY-004 | LOW | Copy-paste comments |

#### 5.2 YAGNI (You Aren't Gonna Need It)

| Check ID | Severity | Detection |
|----------|----------|-----------|
| YAGNI-001 | MEDIUM | Unused public methods/functions |
| YAGNI-002 | LOW | Commented-out code blocks |
| YAGNI-003 | MEDIUM | TODO features implemented but unused |
| YAGNI-004 | HIGH | Dead code paths (unreachable) |

#### 5.3 SOLID Principles

| Principle | Check ID | Severity | Detection |
|-----------|----------|----------|-----------|
| **S**ingle Responsibility | SOLID-S-001 | HIGH | Class/module handles multiple unrelated concerns |
| **S**ingle Responsibility | SOLID-S-002 | MEDIUM | Function does more than its name suggests |
| **O**pen/Closed | SOLID-O-001 | MEDIUM | Modification required for extension (missing abstraction) |
| **L**iskov Substitution | SOLID-L-001 | HIGH | Subclass changes parent behavior unexpectedly |
| **I**nterface Segregation | SOLID-I-001 | MEDIUM | Interface forces unused method implementations |
| **D**ependency Inversion | SOLID-D-001 | HIGH | High-level module depends on concrete low-level module |
| **D**ependency Inversion | SOLID-D-002 | MEDIUM | Constructor creates its own dependencies |

#### 5.4 Function/Method Quality

| Check ID | Threshold | Severity | Metric |
|----------|-----------|----------|--------|
| FN-001 | >150 lines | CRITICAL | Function length |
| FN-002 | >7 params | HIGH | Parameter count |
| FN-003 | >4 levels | MEDIUM | Nesting depth |
| FN-004 | >10 | HIGH | Cyclomatic complexity |
| FN-005 | >5 returns | MEDIUM | Return statements count |
| FN-006 | Boolean | LOW | Flag argument (suggests function does too much) |

### 6. Builder Pattern Analysis

#### 6.1 Builder Pattern Candidates

Identify classes/functions that would benefit from builder pattern:

**Positive Indicators** (suggest builder):
- Constructor with >4 parameters
- Multiple optional parameters with defaults
- Object construction with conditional logic
- Immutable objects with complex initialization
- Fluent API potential

**Negative Indicators** (builder not appropriate):
- Simple value objects (<4 fields)
- Objects always constructed identically
- Mutable objects with setters
- Single required parameter

#### 6.2 Existing Builder Review

If builder pattern detected, verify:

| Check ID | Check | Severity |
|----------|-------|----------|
| BUILD-001 | Builder returns immutable product | MEDIUM |
| BUILD-002 | Build method validates required fields | HIGH |
| BUILD-003 | Method chaining returns `self`/`this` | LOW |
| BUILD-004 | Clear separation: Builder vs Product | MEDIUM |
| BUILD-005 | Optional: Director class for complex builds | LOW |

#### 6.3 Python Builder Pattern Example

```python
# Good Builder Pattern
class QueryBuilder:
    def __init__(self):
        self._select: list[str] = []
        self._from: str = ""
        self._where: list[str] = []

    def select(self, *columns: str) -> "QueryBuilder":
        self._select.extend(columns)
        return self

    def from_table(self, table: str) -> "QueryBuilder":
        self._from = table
        return self

    def where(self, condition: str) -> "QueryBuilder":
        self._where.append(condition)
        return self

    def build(self) -> str:
        if not self._from:
            raise ValueError("FROM clause required")
        # Build and return immutable query string
```

#### 6.4 TypeScript Builder Pattern Example

```typescript
// Good Builder Pattern
class RequestBuilder {
    private method: string = 'GET';
    private url: string = '';
    private headers: Record<string, string> = {};
    private body?: unknown;

    setMethod(method: string): this {
        this.method = method;
        return this;
    }

    setUrl(url: string): this {
        this.url = url;
        return this;
    }

    addHeader(key: string, value: string): this {
        this.headers[key] = value;
        return this;
    }

    setBody(body: unknown): this {
        this.body = body;
        return this;
    }

    build(): Request {
        if (!this.url) throw new Error('URL required');
        return new Request(this.url, {
            method: this.method,
            headers: this.headers,
            body: this.body ? JSON.stringify(this.body) : undefined
        });
    }
}
```

### 7. Language-Specific Quality Checks

#### 7.1 Python-Specific

| Check ID | Check | Severity | Best Practice |
|----------|-------|----------|---------------|
| PY-001 | Type Hints | MEDIUM | All public functions should have type hints |
| PY-002 | Docstrings | LOW | Public API should have docstrings |
| PY-003 | Context Managers | MEDIUM | Use `with` for resource management |
| PY-004 | List Comprehensions | LOW | Prefer over `map`/`filter` for simple cases |
| PY-005 | f-strings | LOW | Prefer over `.format()` or `%` |
| PY-006 | Dataclasses | MEDIUM | Use for simple data containers |
| PY-007 | Async Consistency | HIGH | Don't mix sync/async in same call chain |
| PY-008 | Exception Specificity | MEDIUM | Catch specific exceptions, not bare `except` |

#### 7.2 TypeScript-Specific

| Check ID | Check | Severity | Best Practice |
|----------|-------|----------|---------------|
| TS-001 | Strict Mode | HIGH | `strict: true` in tsconfig |
| TS-002 | Explicit Types | MEDIUM | Avoid implicit `any` |
| TS-003 | Null Safety | HIGH | Use optional chaining (`?.`) and nullish coalescing (`??`) |
| TS-004 | Enum vs Union | LOW | Prefer string unions over enums for simple cases |
| TS-005 | Interface vs Type | LOW | Interface for objects, type for unions/intersections |
| TS-006 | Readonly | MEDIUM | Use `readonly` for immutable properties |
| TS-007 | Async/Await | MEDIUM | Prefer over raw Promises for readability |
| TS-008 | Type Guards | MEDIUM | Use type predicates for runtime type checking |

### 8. Severity Classification

| Severity | Criteria | Action Required |
|----------|----------|-----------------|
| CRITICAL | Security risk, data loss potential, guaranteed runtime error | Must fix before merge |
| HIGH | Significant maintainability/reliability impact, likely bugs | Should fix before merge |
| MEDIUM | Code smell, minor maintainability concern | Fix in next iteration |
| LOW | Style/convention, minor improvement | Optional, nice-to-have |

### 9. Generate Review Report

Output a structured Markdown report:

```markdown
# Code Review Report

**Reviewed**: [DATE]
**Scope**: [FILES/PATHS]
**Languages**: [Python/TypeScript/Both]
**Depth**: [Deep/Standard/Surface]

## Executive Summary

- **Critical Issues**: [COUNT]
- **High Issues**: [COUNT]
- **Medium Issues**: [COUNT]
- **Low Issues**: [COUNT]
- **Builder Pattern Candidates**: [COUNT]

## Critical & High Priority Findings

| ID | File:Line | Category | Issue | Recommendation |
|----|-----------|----------|-------|----------------|
| ... | ... | ... | ... | ... |

## Architecture & Design

### Strengths
- [List architectural positives]

### Concerns
| ID | Issue | Impact | Recommendation |
|----|-------|--------|----------------|
| ... | ... | ... | ... |

## SOLID Violations

| Principle | Location | Issue | Refactoring Suggestion |
|-----------|----------|-------|------------------------|
| ... | ... | ... | ... |

## KISS Violations

| Location | Issue | Simplification |
|----------|-------|----------------|
| ... | ... | ... |

## Function Quality Issues

| Function | File:Line | Issue | Threshold | Actual |
|----------|-----------|-------|-----------|--------|
| ... | ... | >150 lines | 150 | [N] |

## Builder Pattern Opportunities

| Class/Function | File:Line | Current State | Recommendation |
|----------------|-----------|---------------|----------------|
| ... | ... | [Constructor with N params] | Apply builder pattern |

## Language-Specific Issues

### Python
| ID | Location | Issue | Fix |
|----|----------|-------|-----|

### TypeScript
| ID | Location | Issue | Fix |
|----|----------|-------|-----|

## DRY Violations

| Locations | Similarity | Suggested Extraction |
|-----------|------------|---------------------|
| file1:L10-20, file2:L30-40 | 85% | Extract to shared utility |

## Metrics Summary

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Avg Function Length | [N] | <150 | [PASS/FAIL] |
| Max Parameters | [N] | <7 | [PASS/FAIL] |
| Cyclomatic Complexity (avg) | [N] | <10 | [PASS/FAIL] |
| Type Coverage | [N]% | >80% | [PASS/FAIL] |

## Recommended Actions

### Immediate (Critical/High)
1. [Action item with specific location]

### Short-term (Medium)
1. [Action item]

### Long-term (Architectural)
1. [Action item]
```

### 10. Interactive Follow-up

After presenting the report, offer:

1. **"Would you like me to fix the critical issues?"** - Apply fixes for CRITICAL severity items
2. **"Show me the builder pattern refactoring for [class]?"** - Demonstrate specific refactoring
3. **"Explain the SOLID violation in [location]?"** - Deep-dive on specific finding

## Review Guidelines

### What Makes a Good Review Finding

- **Specific**: Points to exact file and line
- **Actionable**: Includes concrete recommendation
- **Justified**: Explains why it matters
- **Proportional**: Severity matches actual impact

### What to Avoid

- Generic advice without specific location
- Stylistic nitpicks in critical review
- Findings without recommendations
- Over-flagging minor issues

### Builder Pattern Decision Tree

```
Constructor has >4 parameters?
├── Yes → Consider builder
│   ├── Multiple optional params? → Strong candidate
│   ├── Conditional construction logic? → Strong candidate
│   └── Simple required params only? → Maybe not needed
└── No → Probably not needed
    └── Complex initialization logic? → Still consider builder
```

## Examples

### Example: Function Too Long

```python
# ❌ Found: src/processor.py:45 - Function `process_data` is 180 lines
# Severity: CRITICAL (FN-001)
# Recommendation: Split into smaller functions:
#   - validate_input()
#   - transform_data()
#   - persist_results()
```

### Example: Builder Pattern Candidate

```typescript
// ❌ Found: src/api/client.ts:23 - Constructor with 8 parameters
// class ApiClient(baseUrl, timeout, retries, headers, auth, logger, cache, interceptors)
// Severity: HIGH (BUILD candidate)
// Recommendation: Apply builder pattern:
//   new ApiClientBuilder()
//     .baseUrl("https://api.example.com")
//     .timeout(5000)
//     .withAuth(authConfig)
//     .build()
```

### Example: SOLID-D Violation

```python
# ❌ Found: src/service.py:12 - Direct dependency on concrete class
# class OrderService:
#     def __init__(self):
#         self.repo = PostgresRepository()  # Concrete dependency
# Severity: HIGH (SOLID-D-002)
# Recommendation: Inject repository interface:
#   def __init__(self, repo: RepositoryProtocol):
#       self.repo = repo
```
