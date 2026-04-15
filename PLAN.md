# Attribute Authority - PLAN.md

## 🎯 The Vision
*A Python-based RESTful API serving as an "Attribute Authority" (AA) that manages user attributes and privileges. It features a robust privilege model for authorization in OIDC/SAML-based federated infrastructures, and a clean separation between machine-facing JSON APIs and a human-facing Bootstrap-based UI.*

---

## 🚀 Doing (Current Focus)
*Keep this to 1 or 2 items maximum. Do not move on until these are checked off.*
- [ ] Review the recent UI and routing refactor (API vs UI separation).
- [ ] Perform a live browser verification pass across all new Bootstrap pages.

## 📋 To Do (Next Up)
*Actionable, small tasks you need to tackle in the near future.*
- [ ] Full redesign of any remaining older templates to match the new Bootstrap shell.
- [ ] Full deprecation cleanup across the whole project.
- [ ] Expand test suite coverage beyond the current repository tests for hidden/manual flows.

## 🐛 Bugs & Tech Debt
*Annoying things that are broken or code that needs to be cleaned up.*
- [ ] Fix `pytest-asyncio` config warning about loop scope.
- [ ] Resolve remaining Pydantic class-based config warnings in older code.
- [ ] Address SQLAlchemy deprecation warning related to `as_declarative()`.
- [ ] Re-enable proper token cache lifetime and full access token verification in `flaat` integration (`core/security.py`).

## 💡 Brainstorming & "Someday"
*Wild ideas, future features, or "maybe one day" thoughts. Dump them here so you can forget about them for now.*
- Should invitation management have a true global admin view, or remain creator-owned?
- Should the admin UI eventually move toward a fully API-driven frontend (e.g., React/Vue) instead of server-rendered forms?

* * * ---

## ✅ Done (Recent Wins)
*Move your finished tasks down here. It is a great morale booster to see this list grow!*

**Recent UI & Routing Refactor**
- [x] Separated server-rendered UI routes from the `/api/v1` JSON API namespace.
- [x] Moved the UI to a Bootstrap-first shared layout with browser light/dark theme support.
- [x] Removed legacy custom CSS and JavaScript where no longer needed.
- [x] Added new CRUD-style admin pages for attribute definitions and privileges.
- [x] Built invitation management pages and moved HTML invitation logic out of the API.
- [x] Excluded UI routes from the generated OpenAPI schema.

**Core Data & Authorization Model**
- [x] Defined and implemented core data models (Users, Attribute Definitions, Attribute Values).
- [x] Implemented a comprehensive Privilege Model (Grantee, Action, Attribute, Value Restrictions, Target Restrictions, Passable flag).
- [x] Supported multiple actions on attributes (`create`, `delete`, `update`, `read`) and values (`set`, `add`, `remove`, `delete`, `read`).
- [x] Implemented constraint evaluation (Regex, enums, prefix constraints) for Value Restrictions.
- [x] Implemented Target Restrictions based on user attributes (e.g., eduPersonAffiliation matches).
- [x] OIDC Authentication flow integration (`/login`, `/auth/authorize`, `/auth/callback`).
- [x] Added SQLAlchemy ORM integrations with PostgreSQL and Alembic database migrations.

**Security, Infrastructure & Services**
- [x] Integrated `flaat` for OIDC access token validation and extraction of user claims.
- [x] Implemented SMTP-based email notification service for user invitations.
- [x] Established robust configuration management via `pydantic-settings` with environment variable support.
- [x] Built comprehensive CI/testing matrix via `tox` supporting Python 3.7 - 3.12.
- [x] Enforced code quality standards with `pytest`, `pytest-cov`, `black` (formatting), `pylint` (linting), and `pyright` (static typing).
- [x] Configured documentation generation via `Sphinx`.