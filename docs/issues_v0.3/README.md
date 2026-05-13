# KinFrame v0.3 Issues

## Overview

14 vertical-slice issues covering template expansion, layer system enhancement, AI quality improvement, viewing experience polish, and infrastructure upgrades.

## Dependency Graph

```
v0.3-01 (Templates) ─────────────────────┐
                                          ├── v0.3-09 (AI Prompt & Quality)
v0.3-02 (Fill & Shadow) ──┬── v0.3-03 (Texture/Vignette) ──┐
                          │                                  ├── v0.3-08 (Scoped CSS) [HITL]
                          └──────────────────────────────────┘

v0.3-04 (Preloading) ──── independent
v0.3-05 (Transitions) ─── independent
v0.3-06 (Empty State) ─── independent
v0.3-07 (Presets) ─────── independent ──────── v0.3-09 (AI Prompt)
v0.3-10 (User Editing) ── independent
v0.3-11 (Admin Regen) ─── independent
v0.3-12 (Schema Share) ── independent
v0.3-13 (Mobile) ──────── independent

all ─────────────────────────────────────── v0.3-14 (Playwright + Acceptance)
```

## Issue List

| ID | Title | Type | Blocked By |
|----|-------|------|------------|
| [01](v0.3-01-5-new-slide-templates.md) | 5 New Slide Templates | AFK | None |
| [02](v0.3-02-fill-shadow-models.md) | Fill & Shadow Models + layer_primitives.json | AFK | None |
| [03](v0.3-03-texture-vignette-layers.md) | Texture + Vignette Layers | AFK | 02 |
| [04](v0.3-04-image-preloading.md) | Image Preloading | AFK | None |
| [05](v0.3-05-slide-transitions.md) | Slide Transitions & Animations | AFK | None |
| [06](v0.3-06-empty-category-ux.md) | Empty Category State + Photo Position | AFK | None |
| [07](v0.3-07-design-presets.md) | design_presets.json | AFK | None |
| [08](v0.3-08-scoped-css.md) | Scoped CSS Support | **HITL** | 02 |
| [09](v0.3-09-ai-prompt-quality.md) | AI Prompt & Quality Enhancement | AFK | 01, 02, 07 |
| [10](v0.3-10-user-self-service.md) | User Self-Service Editing | AFK | None |
| [11](v0.3-11-admin-granular-regeneration.md) | Admin Granular Regeneration | AFK | None |
| [12](v0.3-12-schema-sharing.md) | Schema Sharing | AFK | None |
| [13](v0.3-13-mobile-responsive.md) | Mobile Responsiveness | AFK | None |
| [14](v0.3-14-playwright-e2e-acceptance.md) | Playwright E2E + v0.3 Acceptance | AFK | 01–13 |

## Suggested Sprint Order

**Sprint 1** (foundation): 01, 02, 07 — Templates, Fill/Shadow, Presets
**Sprint 2** (rendering): 03, 04, 05, 06 — Texture/Vignette, Preloading, Transitions, Empty State
**Sprint 3** (AI): 08, 09 — Scoped CSS (needs security review), AI Prompt/Quality
**Sprint 4** (user-facing): 10, 11, 12, 13 — User Editing, Admin Regen, Schema, Mobile
**Sprint 5** (validation): 14 — Playwright E2E + Acceptance

Independent issues (04, 05, 06, 10, 11, 12, 13) can be developed in parallel within their sprints.
