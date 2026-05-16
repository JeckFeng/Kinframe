# KinFrame v0.5 Delete System Issues

## Overview

6 vertical-slice issues covering user showcase hiding, admin visibility operations, permanent delete job execution, admin delete controls, audit/trash readiness, and end-to-end acceptance.

## Dependency Graph

```text
v0.5-delete-01 (User Hide/Unhide) ───────┐
                                          ├── v0.5-delete-05 (Audit + Trash Readiness) ──┐
v0.5-delete-02 (Admin Visibility Ops) ───┘                                                │
                                                                                           ├── v0.5-delete-06 (Playwright + Acceptance)
v0.5-delete-03 (Permanent Delete Job) ─── v0.5-delete-04 (Admin Delete Controls) ─────────┘
```

## Issue List

| ID | Title | Type | Blocked By |
|----|-------|------|------------|
| [01](v0.5-delete-01-user-hide-unhide.md) | User Hide / Unhide From Showcase | AFK | None |
| [02](v0.5-delete-02-admin-visibility-operations.md) | Admin Visibility Operations | AFK | 01 |
| [03](v0.5-delete-03-photo-purge-job.md) | Permanent Photo Purge Job Pipeline | AFK | None |
| [04](v0.5-delete-04-admin-permanent-delete-controls.md) | Admin Permanent Delete Controls | AFK | 03 |
| [05](v0.5-delete-05-delete-audit-trash-readiness.md) | Delete Audit + Trash Readiness | AFK | 01, 03 |
| [06](v0.5-delete-06-e2e-acceptance.md) | Playwright E2E + v0.5 Delete Acceptance | AFK | 01–05 |

## Suggested Sprint Order

**Sprint 1** (safe user-facing control): 01, 03  
**Sprint 2** (admin operations): 02, 04  
**Sprint 3** (governance): 05  
**Sprint 4** (validation): 06

Issues 01 and 03 can be developed in parallel. Issue 02 should reuse the semantics delivered by 01 rather than invent a second visibility model.
