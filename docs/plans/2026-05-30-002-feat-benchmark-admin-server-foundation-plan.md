---
title: Benchmark Admin — Server Foundation (Scaffold, Data Layer, Server)
status: active
type: feat
date: 2026-05-30
origin: docs/plans/2026-05-30-001-refactor-asset-library-stack-rebuild-plan.md
---

# Benchmark Admin — Server Foundation

**Target location:** a new project under `benchmark-admin/`. Every path in this plan is relative to that directory (e.g. `packages/server/src/db/schema.ts` means `benchmark-admin/packages/server/src/db/schema.ts`), not the existing `backend/` + `frontend/` app.

**Origin:** this is a focused, implementer-ready expansion of the parent plan `docs/plans/2026-05-30-001-refactor-asset-library-stack-rebuild-plan.md`. The parent fixes the stack (its M1 table + KTD-1…KTD-11), the requirements (R1–R25), and the full unit sequence (U1–U22). This document deepens **only the server foundation** — the parent's Phase 1 (Foundation), Phase 2 (Data layer), and Phase 3 (Server layer), i.e. units **U1–U14**. It does not re-plan the frontend (parent U15–U19), data migration (U20), or deployment/cutover (U21–U22); those remain owned by the parent.

Where this plan makes a decision the parent left open or stated loosely, it is called out explicitly as a **refinement** with a back-reference to the parent KTD/unit. Nothing here contradicts the parent; it sharpens it against the *actual* legacy schema (`backend/migrations/0001`–`0013`, `backend/db.py`, `backend/main.py`, `backend/ai.py`, `backend/storage.py`), which was inventoried during planning.

---

## Scope

**In scope (three ordered areas, exactly as requested):**

1. **Project initialization & folder structure** — the pnpm monorepo scaffold, cross-cutting tooling (Biome, Husky+lint-staged, TypeScript project config, Vitest projects, drizzle-kit, t3-env), and the exact server-relevant directory tree.
2. **Data structures** — the full Drizzle DB schema (grounded row-for-row in the legacy migrations), the drizzle-zod / Zod input-output schemas (the discriminated union on `data` and the per-router I/O contracts), and the tRPC/API schema surface (every procedure's input and output shape).
3. **Server-side implementation** — the Fastify host, tRPC wiring, the three services (storage, AI, auth) and the export service, and the six routers, with per-unit goals, files, approach, test scenarios, and verification.

**Explicitly out of scope (owned by the parent plan, do not build here):**

- Frontend / React SPA / TanStack Router / Zustand / coss UI (parent U15–U19).
- The one-shot data migration script (parent U20).
- China-host deployment, nginx, systemd, DNS, cutover runbook (parent U21–U22).

The frontend appears in the directory tree below only as stub folders, so the monorepo is laid out correctly from day one; their *contents* are the parent's job.

---

## Coverage map (this plan ⇄ parent units)

| This plan | Parent unit | Area |
| --- | --- | --- |
| Part 1 — §1.1 Monorepo skeleton | U1 | Project init |
| Part 1 — §1.2 App shell (Fastify + Vite stub) | U2 | Project init |
| Part 1 — §1.3 tRPC + superjson wiring | U3 | Project init |
| Part 1 — §1.4 Env validation + Neon driver | U4 | Project init |
| Part 2 — §2A assets/asset_images schema | U5 | Data |
| Part 2 — §2A benchmark schema | U6 | Data |
| Part 2 — §2B drizzle-zod / Zod surface | U5, U6 | Data |
| Part 2 — §2C tRPC/API schema surface | U10–U14 (contracts only) | Data |
| Part 3 — §3.1 Storage service | U7 | Server |
| Part 3 — §3.2 Auth service | U8 | Server |
| Part 3 — §3.3 AI service | U9 | Server |
| Part 3 — §3.4 assetsRouter | U10 | Server |
| Part 3 — §3.5 scenesRouter | U11 | Server |
| Part 3 — §3.6 benchmarkRouter | U12 | Server |
| Part 3 — §3.7 mediaAssets / ai / exports routers | U13 | Server |
| Part 3 — §3.8 batchRegenerate subscription | U14 | Server |

---

## Refinements over the parent plan

Three decisions sharpen the parent against the legacy schema. Each is within the latitude the parent already granted.

- **RF-1 — Promoted columns are net-new, and `name` is *kind-specific* to derive.** Verified: the legacy `assets` table has **no** `name` / `era` / `genre` columns — every one of those lives inside `data` JSONB today (`backend/db.py` reads `data->>'era'`, etc.). The parent's KTD-1 "promote `kind, name, era, genre` to columns" therefore *creates* three new columns whose values are derived from `data` at migration time (parent U20 lifts them). **The `name` source differs by kind (verified against `backend/db.py`):** scenes and props carry a `name` key in `data`, but characters do **not** — a character's display name is resolved legacy-side via the fallback chain `data.title or data.persona`. So the promotion rule the parent U20 migration must apply is per-kind: characters lift `COALESCE(data->>'title', data->>'persona', <object-key fallback>)`; scenes/props lift `data->>'name'`. For this plan that means: the Drizzle schema declares the promoted columns as the source of truth going forward, and the Zod `data` variants **omit** `era`/`genre` and the kind-specific name source (they're columns now, not duplicated JSONB keys) to avoid double-storage drift. No contradiction with KTD-1 — it just records that the promotion is a real, per-kind transformation, not a uniform rename.

- **RF-2 — `video_benchmark_media_links` is the *single* canonical media store; collapse all three legacy representations.** Verified triple storage in legacy `video_benchmark_items`: (a) plain-TEXT object-key columns (`character_image_asset`, `scene_image_asset`, `prop_image_asset`, `audio_input`, `video_input`, `video_output`), (b) per-role FK id columns — **`character_image_id` / `scene_image_id` / `prop_image_id` / `audio_input_id` added in migration 0003, `video_input_id` / `video_output_id` added in 0007** — all → `asset_images.id`, **and** (c) the normalized `video_benchmark_media_links` table (0005 + 0007). The parent U6 kept `video_input_id`/`video_output_id` as direct columns "or decide explicitly to collapse them." This plan **takes the collapse**: the rebuilt `video_benchmark_items` carries **no** media columns at all — every media association (character/scene/prop images, audio input, video input, video output) is a `media_links` row keyed by `role`. Single-cardinality roles (audio_input, video_input, video_output — "one" per R14) are enforced at the Zod/service boundary *and* by a partial unique index (see §2A) so direct-SQL writers (the migration) can't violate them. Rationale: KTD-2 says build a clean schema and migrate once; carrying three parallel representations of the same fact into a greenfield schema is exactly the quirk KTD-2 exists to drop.
  - **This collapse is within parent U6's granted latitude** ("or decide explicitly to collapse them"), but it is a **deliberate deviation from parent U6's default ("keep the columns for a verbatim copy") and from parent U20 as currently written** — U20 today copies only `video_input_id`/`video_output_id` verbatim and materializes links from the legacy link table; it does **not** yet coalesce the four 0003 FK columns. **Hard migration input for parent U20 (must be reflected there before cutover):** for every item and every one of the six roles, if no link row exists, synthesize a link from the per-role FK-id column, and from the TEXT object-key column if neither exists. Legacy reads media with exactly this COALESCE (`backend/db.py`: `item_links.get(role) or [single FK media]`), so an item whose media lives only in a FK-id column (no link row) loses all that media under a links-only copy unless U20 backfills. The link-count parity check (parent U20) must additionally assert ≤1 link per single-cardinality role per item. This plan flags the requirement; it does not implement the migration. **Open item:** parent U20 needs an edit to add the four-column backfill — tracked in this plan's Open Questions.

- **RF-3 — App-level auth is net-new capability, not a port.** Verified: the legacy app has **zero** application-level auth — HTTP Basic Auth is enforced entirely at nginx (`htpasswd`), and `backend/main.py` has no auth code. So U8's single-admin login (env creds + HMAC signed cookie, parent KTD-3/R19) is new code with no legacy reference to mirror. This plan treats `auth/` as a from-scratch module and leans on the parent's explicit token/cookie/CSRF/rate-limit spec (parent U8) rather than any legacy pattern.

- **RF-4 — `assets.kind` drops legacy `audio` and `video`; the asset library is character/scene/prop only.** Verified: the legacy `assets.kind` CHECK allows five values (`character`,`scene`,`prop`,`audio`,`video`), but the rebuilt product treats audio and video purely as *benchmark media* (rows in `asset_images` with `media_type` in `audio`/`video`, linked to items via `media_links`), never as first-class library assets. So the rebuilt `assets.kind` CHECK is narrowed to the three real asset kinds. **This is a deliberate scope decision, not an oversight.** Migration disposition of any legacy rows with `kind` in (`audio`,`video`) is parent U20's responsibility — see Open Questions for whether such rows exist and where they land (most likely re-homed as `asset_images` or dropped if orphaned). The narrowed CHECK and the three-way `kind` discriminated union (§2B) both depend on this decision holding.

---

# Part 1 — Project Initialization & Folder Structure

## 1.0 Exact directory tree (server foundation)

The full target tree is in the parent plan's "Output Structure." Reproduced here with the **server-foundation portion fully expanded** and the frontend/migration/deploy portions shown as stubs (owned elsewhere). This is the tree the scaffold units (§1.1–1.4) must produce, minus the source files that later units fill in.

```
benchmark-admin/
├── apps/
│   ├── web/                              # STUB in this plan — contents = parent U15–U19
│   │   ├── index.html
│   │   ├── src/main.tsx                  # placeholder SPA entry (U2 smoke only)
│   │   ├── src/routes/__root.tsx
│   │   ├── src/routes/index.tsx
│   │   ├── src/lib/trpc.ts               # client wiring (U3)
│   │   ├── src/styles/tailwind.css
│   │   ├── components.json
│   │   ├── vite.config.ts
│   │   └── package.json
│   └── server/                           # Fastify host (this plan)
│       ├── src/
│       │   └── index.ts                  # bootstrap: Fastify + cors + cookie + fastifyTRPCPlugin
│       │                                 #   + raw routes (auth login/logout, multipart upload, export zip)
│       └── package.json
├── packages/
│   ├── server/                           # domain code (this plan owns all of it)
│   │   ├── src/
│   │   │   ├── db/
│   │   │   │   ├── index.ts              # Drizzle client (Neon WebSocket Pool) — §1.4
│   │   │   │   ├── schema.ts             # all tables + relations — §2A
│   │   │   │   └── __tests__/pglite.ts   # PGlite test harness (migrations at boot)
│   │   │   ├── trpc/
│   │   │   │   ├── index.ts              # appRouter export + AppRouter type
│   │   │   │   ├── context.ts            # reads + verifies session cookie — §3.2
│   │   │   │   └── procedures.ts         # publicProcedure / protectedProcedure — §3.2
│   │   │   ├── auth/
│   │   │   │   ├── index.ts              # credential verify + HMAC sign/verify — §3.2
│   │   │   │   └── __tests__/auth.test.ts
│   │   │   ├── services/
│   │   │   │   ├── storage/
│   │   │   │   │   ├── index.ts          # TOS via @aws-sdk/client-s3 — §3.1
│   │   │   │   │   └── __tests__/storage.test.ts
│   │   │   │   ├── ai/
│   │   │   │   │   ├── index.ts          # generatePrompt/Image/extractFields — §3.3
│   │   │   │   │   ├── openrouter.ts     # one openai client + parseJson port
│   │   │   │   │   └── __tests__/ai.test.ts
│   │   │   │   └── exports/
│   │   │   │       └── index.ts          # archiver + exceljs assembly — §3.7
│   │   │   └── routers/
│   │   │       ├── assets.ts             # §3.4
│   │   │       ├── scenes.ts             # §3.5
│   │   │       ├── benchmark.ts          # §3.6
│   │   │       ├── media-assets.ts       # §3.7
│   │   │       ├── ai.ts                 # §3.7 + §3.8
│   │   │       ├── exports.ts            # §3.7 (router shim; raw route lives in apps/server)
│   │   │       └── __tests__/*.test.ts
│   │   └── package.json
│   └── shared/                           # cross-cut: env + schemas + constants + prompts
│       ├── src/
│       │   ├── env.ts                    # @t3-oss/env-core — §1.4
│       │   ├── schemas/
│       │   │   ├── assets.ts             # discriminated union on data — §2B
│       │   │   ├── benchmark.ts          # item + media-link + comment I/O — §2B
│       │   │   └── prompts.ts            # AI procedure I/O — §2B
│       │   ├── constants/
│       │   │   ├── orderings.ts          # TYPE_ORDER, GENRE_ORDER, AGE_ORDER (from backend/db.py)
│       │   │   └── question-types.ts     # shot→task→question hierarchy
│       │   └── lib/
│       │       ├── prompts/              # character (4 variants) + scene + prop + extract
│       │       └── exports/headers.ts    # EN→ZH column map for XLSX
│       └── package.json
├── drizzle/
│   └── migrations/                       # generated by drizzle-kit (db:gen)
├── tools/migrate-from-legacy/            # STUB in this plan — parent U20
├── deploy/                               # STUB in this plan — parent U21
├── pnpm-workspace.yaml
├── .npmrc                                # node-linker=hoisted
├── tsconfig.base.json
├── biome.json
├── vitest.config.ts                      # test.projects: web | server | shared
├── drizzle.config.ts
├── .env.example
├── .husky/pre-commit
└── package.json                          # root scripts + lint-staged
```

## 1.1 Monorepo skeleton and tooling (parent U1)

- **Goal:** an empty, installable monorepo with all cross-cutting tooling, so every later unit lands into a working dev loop (`install`/`lint`/`typecheck` green).
- **Requirements:** R24.
- **Dependencies:** none.
- **Files:** `pnpm-workspace.yaml`, `.npmrc`, `tsconfig.base.json`, `biome.json`, `.husky/pre-commit`, root `package.json` (with lint-staged config), workspace `package.json` for `apps/web`, `apps/server`, `packages/server`, `packages/shared` (declarations only, no source).
- **Approach:**
  - `pnpm-workspace.yaml` globs `apps/*` and `packages/*`. `.npmrc` sets `node-linker=hoisted` (playbook §4 reference).
  - `tsconfig.base.json`: `strict: true`, `noUncheckedIndexedAccess: true`, `moduleResolution: "bundler"`, `verbatimModuleSyntax: true`, path aliases `@server/*`, `@shared/*`, `@env`. Each package extends it with its own `composite`/`references` for project builds.
  - `biome.json` at root: 2-space, 100-col, single quotes (playbook §5.9). Husky `pre-commit` runs `lint-staged`; lint-staged runs `biome format --write` + `biome lint` on staged files.
  - Root `package.json` scripts: `lint`, `typecheck`, `test`, `db:gen`, `db:migrate`, `dev` (concurrently runs server + web).
- **Test scenarios:** none — pure scaffolding, exercised by every later unit.
- **Verification:** `pnpm install`, `pnpm lint`, `pnpm typecheck` all succeed at the root.

## 1.2 App shell — Fastify server + Vite SPA stub (parent U2)

- **Goal:** a Fastify API process and a hello-world Vite React SPA that reaches it; Vitest `test.projects` declared for `web`/`server`/`shared`. No SSR, no Vercel.
- **Requirements:** R23, R24.
- **Dependencies:** §1.1.
- **Files:** `apps/server/src/index.ts` (Fastify bootstrap, `@fastify/cors`, plain `/health`), `apps/web/index.html`, `apps/web/vite.config.ts` (`@vitejs/plugin-react`, `vite-tsconfig-paths`, `@tailwindcss/vite`, dev proxy `/api`→Fastify), `apps/web/src/main.tsx`, `apps/web/src/routes/__root.tsx`, `apps/web/src/routes/index.tsx`, `apps/web/src/styles/tailwind.css`, `apps/web/components.json`, root `vitest.config.ts`.
- **Approach:** Fastify with `@fastify/cors` allowing the SPA origin; a plain `/health` route (tRPC mounts in §1.3). Vite SPA with React + Tailwind v4 plugin + tsconfig-paths; in dev Vite proxies `/api` to the Fastify port (nginx does the same in prod, parent U21). coss UI initialized per playbook §5.6 (read `coss.com/ui/llms.txt` first). One dummy button proves the design system. **Frontend contents stay minimal** — just enough to smoke-test; the real SPA is parent U15–U19.
- **Test scenarios:** `pnpm --filter server dev` serves `/health`; `pnpm --filter web dev` serves the SPA root; vitest `web` project boots a smoke test asserting `__root.tsx` renders.
- **Verification:** SPA root renders and reaches Fastify `/health`; smoke test passes.

## 1.3 tRPC v11 + TanStack Query + superjson wiring (parent U3)

- **Goal:** an end-to-end typed RPC call from the SPA to Fastify with superjson transport, mounted via the tRPC Fastify adapter; the `health` procedure round-trips a `Date`.
- **Requirements:** baseline for every server-side R.
- **Dependencies:** §1.2.
- **Files:** `packages/server/src/trpc/index.ts` (`appRouter` with one `health` procedure + `AppRouter` type export), `packages/server/src/trpc/context.ts`, `packages/server/src/trpc/procedures.ts` (`publicProcedure`, `protectedProcedure` stubs), `apps/server/src/index.ts` (register `fastifyTRPCPlugin` at `/api/trpc`), `apps/web/src/lib/trpc.ts` (client + vanilla caller, `httpBatchLink`→`/api/trpc`).
- **Approach:** Per playbook §5.2 + KTD-6. Transport mounted via `@trpc/server/adapters/fastify` (`fastifyTRPCPlugin`), not a TanStack-Start catch-all. `superjson` transformer on both ends. Export `AppRouter` *type* from the server entry; the client imports the type only. A vanilla `trpcClient` caller is created for use inside Zustand actions later (parent U19). `health` returns `{ ok: true, ts: new Date() }` so the `Date` confirms superjson.
- **Test scenarios:** server — `appRouter.createCaller(ctx).health()` returns `{ ok: true, ts: <Date> }`; integration — a component using `trpc.health.useQuery()` renders the timestamp (no DB needed).
- **Verification:** RPC works in the browser; `Date` arrives as a `Date`.

## 1.4 Env validation + Neon driver (parent U4)

- **Goal:** every env var validated at boot via `@t3-oss/env-core`; the Neon WebSocket Pool client connected.
- **Requirements:** baseline for R10, R19.
- **Dependencies:** §1.1.
- **Files:** `packages/shared/src/env.ts`, `packages/server/src/db/index.ts` (Drizzle client, Neon WebSocket Pool, no schema import yet), `.env.example`.
- **Approach:**
  - **Env (server-only):** `DATABASE_URL`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `TEXT_MODEL`, `IMAGE_MODEL`, `IMAGE_ASPECT_RATIO` (default `3:2`), `IMAGE_SIZE` (default `2K`), `TOS_BUCKET`, `TOS_REGION`, `TOS_ENDPOINT`, `TOS_ACCESS_KEY_ID`, `TOS_SECRET_ACCESS_KEY`, `SESSION_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`. The four AI vars and all TOS vars carry over verbatim from legacy `backend/ai.py` / `backend/storage.py`, so behavior stays config-driven (KTD-7). `runtimeEnv: process.env`. No client env vars yet. **`SESSION_SECRET` carries a length refinement** (`.min(64)` hex chars / 256-bit) so a short or empty HMAC key fails at boot, not at first forged cookie (§3.2). `.env.example` documents it with `# openssl rand -hex 32`.
  - **Driver (deviation from playbook §5.3, recorded in parent KTD/U4):** Neon `@neondatabase/serverless` **WebSocket Pool** (`Pool` + `drizzle-orm/neon-serverless`), **not** the HTTP/fetch driver — U12/§3.6 needs an interactive `db.transaction()` (upsert item → read id → insert links). On a non-serverless Node host set `neonConfig.webSocketConstructor = ws` at module load. Modest pool size + idle timeout for one long-lived process. This single Pool client is the one authoritative DB handle for the whole app.
- **Migration-authoring caveat (feasibility):** two §2A constraints cannot be expressed in drizzle-kit's column/table DSL and must be **hand-appended to the generated migration SQL** after `db:gen`, then kept in sync by convention: (a) the `assets.cover_image_id` FK as `DEFERRABLE INITIALLY DEFERRED` (drizzle emits a plain FK; the deferral is required so the asset↔cover-image insert can happen in one tx, §2A); (b) the partial unique index `UNIQUE(item_id, role) WHERE role IN ('audio_input','video_input','video_output')` on `media_links` (drizzle-kit has no partial-unique DSL, §2A). The PGlite test harness (`__tests__/pglite.ts`) runs the same migration SQL, so both land in tests too — but see Open Questions on PGlite's DEFERRABLE/partial-index parity.
- **Test scenarios:** happy — env loads, `db.execute(sql\`select 1\`)` returns 1; error — missing `DATABASE_URL` throws at module-load before any handler runs; `SESSION_SECRET` <64 hex chars throws at boot.
- **Verification:** boot fails fast on missing/short env; `db` connects to Neon; the generated migration includes the hand-appended DEFERRABLE FK and partial unique index.

---

# Part 2 — Data Structures

This part is the contract the whole server is built on. It has three layers: **2A** the Drizzle tables (DB truth), **2B** the drizzle-zod / Zod schemas (validation truth, KTD-8: schemas derive from tables), **2C** the tRPC procedure I/O surface (wire truth). Each layer derives from the one above it.

## 2A — Drizzle DB schema (parent U5, U6)

All tables live in `packages/server/src/db/schema.ts`. The schema is a **clean rebuild** (KTD-2) grounded in the cumulative legacy shape from `backend/migrations/0001`–`0013`, with RF-1/RF-2 applied.

### Table: `assets` (parent U5)

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `bigserial` PK | |
| `kind` | `text NOT NULL` | CHECK in (`character`,`scene`,`prop`). **Legacy also allowed `audio`,`video` as asset kinds — dropping them is decision RF-4 (see Refinements); migration disposition of any legacy `audio`/`video` rows is parent U20.** |
| `name` | `text NOT NULL` | **net-new column (RF-1)** — per-kind derivation at migration: characters `COALESCE(data->>'title', data->>'persona', '(unnamed)')`, scenes/props `data->>'name'`. Never read from a `data->>'name'` key for characters (no such key in legacy `CHARACTER_FIELDS`). |
| `era` | `text NULL` | **net-new (RF-1)** — promoted filter dimension. |
| `genre` | `text NULL` | **net-new (RF-1)** — promoted filter dimension. |
| `data` | `jsonb NOT NULL DEFAULT '{}'` | variant fields per kind (see 2B); **excludes** `name`/`era`/`genre` post-promotion. |
| `cover_image_id` | `bigint NULL` | FK → `asset_images.id` `ON DELETE SET NULL`, **DEFERRABLE** (legacy 0003 pattern — assets and images reference each other, so the FK must defer within a tx). |
| `created_at` | `timestamptz NOT NULL DEFAULT now()` | |
| `updated_at` | `timestamptz NOT NULL DEFAULT now()` | bump on update in the service layer. |
| `deleted_at` | `timestamptz NULL` | soft-delete (legacy pattern). |

**Indexes:** GIN on `data` (legacy `idx_assets_data`); btree `(kind, deleted_at)` (default list filter); btree `(kind, era)`; btree `(kind, genre)`. The kind-prefixed composites replace legacy's single-column `idx_assets_kind` because every list query is scoped by `kind` first.

### Table: `asset_images` (parent U5)

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `bigserial` PK | |
| `asset_id` | `bigint NOT NULL` | FK → `assets.id` `ON DELETE CASCADE`. |
| `object_key` | `text NOT NULL` | TOS path; reused verbatim from legacy at migration. |
| `source` | `text NOT NULL DEFAULT 'generated'` | `generated`/`uploaded`/`reverse`/`multiview`. |
| `media_type` | `text NOT NULL DEFAULT 'image'` | CHECK in (`image`,`audio`,`video`) (legacy 0009). |
| `created_at` | `timestamptz NOT NULL DEFAULT now()` | |

**Indexes:** `(asset_id)`, `(media_type)`, `(object_key)` — all carried from legacy (the `object_key` index backs the `mediaAssets` dedup query, §3.7).

### Table: `video_benchmark_items` (parent U6, RF-2 applied)

Scalar fields only — **no media columns** (RF-2 collapses all media into `media_links`).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `bigserial` PK | |
| `shot_type` | `text NOT NULL DEFAULT ''` | |
| `task_type` | `text NOT NULL DEFAULT ''` | |
| `question_type` | `text NOT NULL DEFAULT ''` | cascading hierarchy (2B constant). |
| `manual_tag` | `text NOT NULL DEFAULT ''` | |
| `scene` | `text NOT NULL DEFAULT ''` | |
| `screen_size` | `text NOT NULL DEFAULT ''` | |
| `text_prompt` | `text NOT NULL DEFAULT ''` | |
| `judging_criteria` | `text NOT NULL DEFAULT ''` | |
| `score` | `smallint NULL` | CHECK (`score IS NULL OR score BETWEEN 0 AND 5`) (legacy). |
| `needs_revision` | `boolean NOT NULL DEFAULT false` | |
| `created_at` | `timestamptz NOT NULL DEFAULT now()` | |
| `updated_at` | `timestamptz NOT NULL DEFAULT now()` | |
| `deleted_at` | `timestamptz NULL` | soft-delete. |

**Dropped vs legacy (RF-2):** the six TEXT object-key columns (`character_image_asset`…`video_output`) and the six per-role FK-id columns (`character_image_id`…`video_output_id`). All become `media_links` rows.

**Indexes:** `(shot_type, question_type)` (stats dashboard, R16); partial `(id) WHERE deleted_at IS NULL` (active-list, legacy `idx_..._active`).

### Table: `video_benchmark_media_links` (parent U6 — the single canonical media store, RF-2)

Carried verbatim from legacy 0005+0007 shape (the part of legacy that was *already* normalized).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `bigserial` PK | surrogate (legacy used a surrogate, not a compound PK). |
| `item_id` | `bigint NOT NULL` | FK → `video_benchmark_items.id` `ON DELETE CASCADE`. |
| `media_id` | `bigint NOT NULL` | FK → `asset_images.id` `ON DELETE CASCADE`. **Column is `media_id`, not `asset_image_id`** — matches legacy so parent U20 maps 1:1. |
| `role` | `text NOT NULL` | CHECK in the 6-value union: `character_image`,`scene_image`,`prop_image`,`audio_input`,`video_input`,`video_output`. |
| `sort_order` | `integer NOT NULL DEFAULT 0` | ordering within a role. |
| `created_at` | `timestamptz NOT NULL DEFAULT now()` | |

**Constraints (RF-2):**
- `UNIQUE(item_id, role, media_id)` — the same image can fill two different roles on one item, but the same image cannot fill the same role twice.
- **Single-cardinality roles enforced in the DB** via a partial unique index `UNIQUE(item_id, role) WHERE role IN ('audio_input','video_input','video_output')`. These three roles are "one"; the three image roles (`character_image`,`scene_image`,`prop_image`) are "many" and are intentionally excluded from the partial index. The Zod input + service still validate cardinality for a clean error message, but the DB is the backstop so a concurrent double-insert cannot violate the invariant. drizzle-kit does not emit partial unique indexes from the column DSL — hand-author this index in the generated migration (see §1.4 / Feasibility note on DEFERRABLE).
**Indexes:** `(item_id, role)`, `(media_id)`.

### Table: `benchmark_item_comments` (parent U6)

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `bigserial` PK | |
| `item_id` | `bigint NOT NULL` | FK → `video_benchmark_items.id` `ON DELETE CASCADE`. |
| `author` | `text NOT NULL DEFAULT ''` | the authenticated admin email at insert time (§3.2). |
| `body` | `text NOT NULL` | |
| `created_at` | `timestamptz NOT NULL DEFAULT now()` | |

### Relations (Drizzle `relations()`)

- `assets` → many `asset_images`; `assets.cover_image_id` → one `asset_images`.
- `video_benchmark_items` → many `video_benchmark_media_links`; → many `benchmark_item_comments`.
- `video_benchmark_media_links.media_id` → one `asset_images`.

```ts
// packages/server/src/db/schema.ts — directional, not the final file
export const assets = pgTable('assets', {
  id: bigserial('id', { mode: 'number' }).primaryKey(),
  kind: text('kind').$type<'character' | 'scene' | 'prop'>().notNull(),
  name: text('name').notNull(),                       // net-new (RF-1)
  era: text('era'),
  genre: text('genre'),
  data: jsonb('data').$type<AssetData>().notNull().default({}),
  coverImageId: bigint('cover_image_id', { mode: 'number' }),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp('deleted_at', { withTimezone: true }),
}, (t) => ({
  dataGin: index('idx_assets_data').using('gin', t.data),
  kindDeleted: index('idx_assets_kind_deleted').on(t.kind, t.deletedAt),
}))
```

## 2B — drizzle-zod / Zod schema surface (parent U5, U6; KTD-8)

Every schema in `packages/shared/src/schemas/` is `createInsertSchema()` / `createSelectSchema()` on a Drizzle table, or extends one (KTD-8 — no hand-written shapes mirroring a column). The one place we layer hand-authored Zod is the **`data` JSONB variant union**, because the DB type is opaque `jsonb`.

### `schemas/assets.ts`

JSONB `data` variants (grounded in the verified legacy `data` keys, minus the promoted `name`/`era`/`genre` per RF-1):

- `CharacterDataSchema` — `{ type, gender, age, persona, body, features, prompt, description, title }` (legacy character keys; `era`/`genre` promoted out).
- `SceneDataSchema` — `{ scene_type, mood, elements, prompt, description, title }` (`era`/`genre` promoted out; `name` promoted out).
- `PropDataSchema` — `{ category, prompt, description, title }`.

Composition:

```ts
const AssetBase = createSelectSchema(assets)            // id, kind, name, era, genre, coverImageId, timestamps…
export const CharacterAsset = AssetBase.extend({ kind: z.literal('character'), data: CharacterDataSchema })
export const SceneAsset     = AssetBase.extend({ kind: z.literal('scene'),     data: SceneDataSchema })
export const PropAsset       = AssetBase.extend({ kind: z.literal('prop'),      data: PropDataSchema })
export const AssetSchema = z.discriminatedUnion('kind', [CharacterAsset, SceneAsset, PropAsset])

// Outbound row adds the presigned image array (computed at query time, KTD-5):
export const AssetWithImages = <T extends z.ZodTypeAny>(v: T) =>
  v.and(z.object({ images: z.array(AssetImageOut), coverImageId: z.number().nullable() }))
```

`AssetImageOut = createSelectSchema(assetImages).extend({ url: z.string().url() })` — the `url` is the presigned TOS URL injected by the service (it is **not** a DB column).

Insert/update inputs are a **separate** insert-side discriminated union, not the select union above (the select union carries generated `id`/timestamps that a create input must not accept):

```ts
const AssetInsertBase = createInsertSchema(assets).omit({
  id: true, createdAt: true, updatedAt: true, deletedAt: true,
})  // leaves kind, name, era, genre, coverImageId, data
const CharacterInsert = AssetInsertBase.extend({ kind: z.literal('character'), data: CharacterDataSchema })
const SceneInsert     = AssetInsertBase.extend({ kind: z.literal('scene'),     data: SceneDataSchema })
const PropInsert      = AssetInsertBase.extend({ kind: z.literal('prop'),      data: PropDataSchema })
export const AssetInsert = z.discriminatedUnion('kind', [CharacterInsert, SceneInsert, PropInsert])
// AssetUpdate = each member .partial() except kind (kind is immutable post-create)
export const AssetUpdate = z.discriminatedUnion('kind', [
  CharacterInsert.partial().required({ kind: true }),
  SceneInsert.partial().required({ kind: true }),
  PropInsert.partial().required({ kind: true }),
])
```

`AssetInsert` / `AssetUpdate` are the exact types the §2C `assetsRouter.create` / `update` reference. Filters/search params live in the router input schema (2C), not here.

### `schemas/benchmark.ts`

- `VideoBenchmarkItem = createSelectSchema(videoBenchmarkItems)`.
- `MediaLink = createSelectSchema(videoBenchmarkMediaLinks)`; `MediaLinkOut = MediaLink.extend({ url: z.string().url() })`.
- `BenchmarkComment = createSelectSchema(benchmarkItemComments)`.
- **Media bundle input** (the RF-2 cardinality enforcement point):
  ```ts
  export const MediaBundleInput = z.object({
    characterImageIds: z.array(z.number()).default([]),
    sceneImageIds: z.array(z.number()).default([]),
    propImageIds: z.array(z.number()).default([]),
    audioInputId: z.number().nullable().default(null),   // single
    videoInputId: z.number().nullable().default(null),    // single
    videoOutputId: z.number().nullable().default(null),   // single
  })
  ```
  The service explodes this bundle into `media_links` rows; single-cardinality roles map to at most one row. The outbound item groups links back by role (`BenchmarkItemOut = VideoBenchmarkItem.extend({ media: MediaByRole, comments: z.array(BenchmarkComment) })`).

### `schemas/prompts.ts`

AI procedure I/O (2C `aiRouter`): `GeneratePromptInput`, `ExtractFieldsInput` (`{ kind, description, options? }` where `options` is `z.record(z.array(z.string())).optional()` — per-field candidate value-lists fed to the extract prompt), `GenerateImageInput`, and the result shapes. These reference the asset variant schemas so an extracted-fields result validates against `CharacterDataSchema` etc.

## 2C — tRPC / API schema surface (contracts for parent U10–U14)

The complete procedure surface, grouped by router. Inputs/outputs are the Zod schemas above. This is the **API schema** the frontend (parent U15–U19) will type against, and it is the parity target for the legacy 56 routes (parent U22 owns the diff). Cursor pagination replaces legacy LIMIT/OFFSET (KTD, playbook §3 "never offset").

**`assetsRouter`** (kind ∈ character|scene|prop, one router for all three):
| Procedure | Kind | Input | Output |
| --- | --- | --- | --- |
| `list` | query | `{ kind, filters?, search?, deletedOnly?, cursor? }` | `{ items: AssetWithImages[], nextCursor: number \| null }` |
| `get` | query | `{ id }` | `AssetWithImages` |
| `create` | mutation | `AssetInsert` (variant) | `AssetWithImages` |
| `update` | mutation | `{ id, ...AssetUpdate }` | `AssetWithImages` |
| `delete` | mutation | `{ id }` | `{ id }` (soft-delete) |
| `restore` | mutation | `{ id }` | `AssetWithImages` |
| `attachImage` | mutation | `{ id, objectKey, source }` | `AssetImageOut` |
| `deleteImage` | mutation | `{ imageId }` | `{ imageId }` |
| `setCover` | mutation | `{ id, imageId }` | `AssetWithImages` |

`filters` is a discriminated record by kind: character → `{ era?, type?, gender?, age?, genre? }`, scene → `{ era?, scene_type?, genre?, mood? }`, prop → `{ category? }` (each value an array, applied as `data->>key = ANY(...)` for JSONB keys or column `= ANY(...)` for promoted columns). `search` is free-text ILIKE over `name` + `data` (300 ms debounce client-side, R2).

**`scenesRouter`** (scene-only extension): `generateView` mutation — `{ id, mode: 'reverse'|'multiview' }` → `AssetImageOut`. **No `propsRouter`** (parent: props fully served by `assetsRouter`; YAGNI).

**`benchmarkRouter`:**
| Procedure | Kind | Input | Output |
| --- | --- | --- | --- |
| `list` | query | `{ filters?, search?, deletedOnly?, cursor? }` | `{ items: BenchmarkItemOut[], total, nextCursor }` |
| `get` | query | `{ id }` | `BenchmarkItemOut` |
| `create` | mutation | `{ ...itemScalars, media: MediaBundleInput }` | `BenchmarkItemOut` |
| `update` | mutation | `{ id, ...itemScalars, media: MediaBundleInput }` | `BenchmarkItemOut` |
| `delete` / `restore` | mutation | `{ id }` | `{ id }` / `BenchmarkItemOut` |
| `setNeedsRevision` | mutation | `{ id, needsRevision }` | `BenchmarkItemOut` |
| `stats` | query | `{}` | `{ groups: {shotType, questionType, count}[], todayNew }` |
| `comments.list` | query | `{ itemId }` | `BenchmarkComment[]` |
| `comments.add` | mutation | `{ itemId, body }` | `BenchmarkComment` |
| `comments.delete` | mutation | `{ commentId }` | `{ commentId }` |

**`mediaAssetsRouter`:** `list` query — `{ kind?, mediaType?, dedup? }` → `AssetImageOut[]` (joins `asset_images`→`assets`, optional dedup by `object_key`, R12).

**`aiRouter`:** `generatePrompt` `{ kind, input }`→`{ prompt }`; `extractFields` `{ kind, description, options? }`→ matching `*DataSchema` (the optional `options` carries per-field candidate value-lists — e.g. allowed `type`/`gender`/`age` enums — that legacy `backend/ai.py` injects into the extract prompt so the model picks from a closed set; the service passes them through to the user message, §3.3); `generateImage` `{ kind, id, prompt, refImage?, aspectRatio? }`→`AssetImageOut`; `batchRegenerate` **subscription** `{ ids }`→ yields `{ id, status, imageKey?, error? }` (parent U14, §3.8).

**`exportsRouter`:** a tRPC `getDownloadUrl` query `{ kind, filters?, search? }`→`{ url }` is the typed handle, but the actual ZIP bytes stream over a **raw Fastify route** `GET /api/export/:kind.zip` (tRPC has no byte-stream response — parent U13). Documented here so the contract is explicit: the typed surface returns a URL, the raw route streams.

**`authRouter` is intentionally absent from tRPC.** Login/logout are raw Fastify routes (`POST /api/auth/login`, `POST /api/auth/logout`) because they set/clear cookies and must run before the tRPC context exists (§3.2). All tRPC procedures except `health` use `protectedProcedure`.

---

# Part 3 — Server-Side Implementation

Build order within the server layer: **services first** (storage → auth → AI), then **routers** (assets → scenes → benchmark → media/ai/exports), then the **subscription**. Routers depend on services; services depend only on the data layer (Part 2) and env (§1.4).

## 3.1 Storage service (parent U7)

- **Goal:** the TS equivalent of `backend/storage.py`: `putObject`, `getPresignedUrl`, `deleteObject`, `newObjectKey`, `healthCheck`.
- **Requirements:** R10, R11.
- **Dependencies:** §1.4.
- **Files:** `packages/server/src/services/storage/index.ts`, `…/__tests__/storage.test.ts`.
- **Approach:** `@aws-sdk/client-s3` configured against the TOS endpoint (Volcengine is S3-compatible, sigv4, `forcePathStyle` as legacy uses). `getPresignedUrl(key, expires=3600)` via `@aws-sdk/s3-request-presigner` (1-hour TTL, KTD-5). `newObjectKey(ext='.png', prefix='images')` mirrors legacy: `{prefix}/{uuid4hex}{ext.toLowerCase()}`; prefixes `images/`, `audios/`, `videos/`. `putObject(key, bytes, contentType)`, `deleteObject(key)`, `getBytes(key)` (used by scene image-to-image, §3.5). For non-image presigned downloads, accept `ResponseContentDisposition: 'attachment'` (parent U13).
- **Test scenarios:** happy — `putObject` then `getPresignedUrl` GET returns the same bytes; edge — `getPresignedUrl` for a missing key still returns a signed URL (S3 contract); error — invalid bucket → `putObject` rejects with a typed error the AI router maps to a user message.
- **Verification:** integration test against a TOS staging bucket passes; unit tests mock the S3 client via `aws-sdk-client-mock`.

## 3.2 Auth service (parent U8; RF-3 — net-new)

- **Goal:** single-admin login with no auth library and no DB tables: verify env credentials, set a signed http-only cookie; `protectedProcedure` checks it.
- **Requirements:** R19.
- **Dependencies:** §1.3.
- **Files:** `packages/server/src/auth/index.ts` (credential verify; HMAC sign/verify), `apps/server/src/index.ts` (`@fastify/cookie`, `POST /api/auth/login`, `POST /api/auth/logout`, `@fastify/rate-limit` scoped to login), `packages/server/src/trpc/context.ts` (read+verify cookie), `packages/server/src/trpc/procedures.ts` (`protectedProcedure`), `…/auth/__tests__/auth.test.ts`.
- **Approach:** Login constant-time-compares posted email/password against `ADMIN_EMAIL`/`ADMIN_PASSWORD`; on success sets an http-only, `SameSite=Strict`, `Secure` cookie. **Token (explicit, parent U8):** `base64url(payload).base64url(HMAC-SHA256(payload, SESSION_SECRET))`, `payload = { jti, iat, exp }`, `jti` a random 128-bit nonce, TTL ~4h (tightened from 12h — see Accepted risks). Verify recomputes the HMAC constant-time, rejects on mismatch or expiry. **Logout/revocation:** `POST /api/auth/logout` clears the cookie and adds `jti` to a bounded in-memory revocation set (entries auto-expire at `exp`; single-process state is fine — one long-lived host, KTD-4). **CSRF:** `SameSite=Strict` plus an `x-trpc-source` header check on mutations as defense-in-depth. **Rate-limit (in scope):** per-IP attempt cap with backoff on `/api/auth/login`. Context reads the cookie, verifies, populates `session`; `protectedProcedure` throws `UNAUTHORIZED` when absent/forged/expired/revoked.
  - **`SESSION_SECRET` entropy (env boot-check, §1.4):** the `@t3-oss/env-core` schema requires `SESSION_SECRET` to be ≥64 hex chars (256-bit). `.env.example` ships the placeholder with a generation hint (`# openssl rand -hex 32`). Boot fails fast if it is short or unset — a guessable HMAC key defeats the whole cookie scheme.
  - **Shared `requireSession` preHandler:** the cookie verify+populate logic is factored into one named Fastify preHandler (`requireSession`) exported from `auth/`, reused by every session-gated raw route (logout, multipart upload, export zip) **and** mirrored by the tRPC `protectedProcedure`. One implementation, one place to audit — raw routes must not hand-roll their own cookie check.
- **Raw-route auth matrix** (the routes that bypass tRPC context — each must declare its guard):

  | Raw route | Guard |
  | --- | --- |
  | `POST /api/auth/login` | **public** (the only unauthenticated mutation; rate-limited) |
  | `POST /api/auth/logout` | `requireSession` |
  | `POST /api/upload` (multipart) | `requireSession` |
  | `GET /api/export/:kind.zip` | `requireSession` |
  | `GET /health` | public (no secrets in payload — §3.7) |

- **Accepted risks (documented, not fixed here):**
  - **`ADMIN_PASSWORD` is compared as plaintext from env, not a hash.** This is intentional per parent KTD-3 (constant-time compare of the env-supplied value); a single hard-wired admin with no user table has no enrollment step to hash against. Mitigation is operational: the env file is host-private and not committed. Not changed in this plan because hashing would contradict KTD-3 and add no real protection for a single static credential.
  - **Revocation set is in-memory and lost on restart.** A logged-out-then-leaked cookie becomes valid again if the process restarts before `exp`. Accepted because the host is single-process and long-lived (KTD-4) and the TTL is tightened to ~4h to bound the window. Promoting revocation to a durable store is deferred with pg-boss (parent KTD-4).
- **Test scenarios:** happy — login → cookie → `protectedProcedure` succeeds; error — wrong password → 401 no cookie; missing/forged/expired cookie → `UNAUTHORIZED`; rate-limit — N rapid failures throttle; revocation — login→logout→same cookie now fails even though HMAC still verifies; env — boot throws when `SESSION_SECRET` is missing or <64 hex chars; raw-route guard — `requireSession` rejects an unauthenticated `POST /api/upload`.
- **Verification:** auth tests cover sign/verify, happy, unauthorized, tampered-cookie, post-logout revocation, the `SESSION_SECRET` boot-check, and a guarded raw route rejecting an anonymous request.

## 3.3 AI service (parent U9; KTD-7 — port `backend/ai.py` verbatim)

- **Goal:** one AI module wrapping the `openai` client with `generatePrompt`, `generateImage`, `extractFields`, callable from any procedure; system prompts centralized.
- **Requirements:** R6, R7, R8, R9.
- **Dependencies:** §3.1.
- **Files:** `packages/server/src/services/ai/index.ts`, `…/ai/openrouter.ts` (one `openai` client + `parseJson` port of legacy `_parse_json`), `packages/shared/src/lib/prompts/{character,scene,prop,extract-fields}.ts`, `…/ai/__tests__/ai.test.ts`.
- **Approach:** Port `backend/ai.py` shape-for-shape — the only proven path against this OpenRouter proxy; do not invent a cleaner surface (KTD-7).
  - Client: `new OpenAI({ apiKey: env.OPENROUTER_API_KEY, baseURL: env.OPENROUTER_BASE_URL, timeout: 600_000 })`.
  - **Text:** `chat.completions.create({ model: env.TEXT_MODEL, messages: [{role:'system',content:system},{role:'user',content:prompt}], temperature: 0.7 })` → `choices[0].message.content`.
  - **Image:** `chat.completions.create({ model: env.IMAGE_MODEL, messages:[{role:'user',content}], ...{ modalities:['image','text'], image_config:{ aspect_ratio: env.IMAGE_ASPECT_RATIO ?? '3:2', image_size: env.IMAGE_SIZE ?? '2K' } } as extra_body })`; read bytes from `choices[0].message.images[0].image_url.url`, branch `data:` (base64-decode) vs `http` (fetch), pipe to `storage.putObject()`. **Image-to-image** (scene reverse/multiview): `content` is `[{type:'text',text:prompt},{type:'image_url',image_url:{url:'data:image/png;base64,'+b64}}]`.
  - **Extract:** plain prompt with candidate `options` in the user message; tolerant brace-extraction parse (`parseJson`, tolerate markdown fences); **no** `response_format: json_schema`; validate against the Zod variant afterward.
  - **Prompts:** the 4 character variants (human/animal/creature/anthro), one scene, one prop, in `packages/shared/src/lib/prompts/`, mirroring legacy verbatim. Variant selection by `data.type` for characters.
- **Test scenarios:** happy (mocked provider) — each of 4 character variants returns non-empty; `extractFields` returns a `CharacterDataSchema`-shaped object; error — provider rate-limit surfaces as a typed `AI_RATE_LIMITED` the router maps to 429.
- **Verification:** AI tests pass with the mocked client; manual smoke against staging OpenRouter returns real content.

## 3.4 assetsRouter (parent U10)

- **Goal:** one router powering list/get/create/update/delete/restore for all three kinds, plus attach/detach/set-cover.
- **Requirements:** R1, R2, R3, R4, R5.
- **Dependencies:** §2A, §3.1, §3.2.
- **Files:** `packages/server/src/routers/assets.ts`, `…/__tests__/assets.test.ts`.
- **Approach:** Inputs per 2C. **Cursor pagination** (cursor = `id` of last row, order `id desc`; replaces legacy LIMIT/OFFSET). Every asset response includes an `images[]` array with each image's presigned `url` computed at query time (KTD-5). Filters applied dynamically per kind — promoted columns (`era`,`genre`) as column `= ANY(...)`, JSONB keys (`type`,`gender`,`age`,`scene_type`,`mood`,`category`) as `data->>key = ANY(...)`. Ordering honors `TYPE_ORDER`/`GENRE_ORDER`/`AGE_ORDER` constants where legacy did. All procedures are `protectedProcedure`.
- **Test scenarios:** create character → list → get returns variant `data` typed; filters — 5 mixed-`era` chars, `{era:['古代']}` returns the subset; pagination — 25 rows → page 1 (20+cursor), page 2 (5); soft-delete → default list excludes, `deletedOnly` includes, restore returns to default; cover — attach 2, set 2nd, response `coverImageId` matches.
- **Verification:** all scenarios pass against PGlite; cursor semantics match the client.

## 3.5 scenesRouter (parent U11)

- **Goal:** scene `generateView` (reverse-shot, 4-view).
- **Requirements:** R9.
- **Dependencies:** §3.3, §3.4.
- **Files:** `packages/server/src/routers/scenes.ts`, `…/__tests__/scenes.test.ts`.
- **Approach:** `generateView({ id, mode })` reads the cover image bytes from TOS (`storage.getBytes`), calls the AI image path with those bytes inlined as the `data:` reference part (same `chat.completions`+`modalities` call as §3.3, not a separate edit endpoint), uploads the result with `source: mode`, attaches it. No `propsRouter` (YAGNI).
- **Test scenarios:** happy (mocked) — `generateView({mode:'reverse'})` calls AI with cover bytes, persists with `source:'reverse'`; error — scene without a cover image → `BAD_REQUEST` "Set a cover image first."
- **Verification:** tests pass with mocked AI + storage.

## 3.6 benchmarkRouter (parent U12)

- **Goal:** all benchmark item operations including stats and comments.
- **Requirements:** R13, R14, R15, R16.
- **Dependencies:** §2A (benchmark tables), §3.2, §3.4.
- **Files:** `packages/server/src/routers/benchmark.ts`, `…/__tests__/benchmark.test.ts`.
- **Approach:** Procedures per 2C. **Create/update accept `MediaBundleInput`** and explode it into `media_links` rows inside an **interactive `db.transaction()`** (requires the WebSocket Pool driver, §1.4): upsert the item, read its id, insert links keyed on that id, roll back the item if any link fails. Single-cardinality roles (audio/video in/out) insert at most one link (RF-2 enforcement). `stats` returns `GROUP BY (shot_type, question_type)` counts plus `todayNew`. Comments use the authenticated admin email as `author`.
- **Test scenarios:** create with 3 character + 1 scene + 1 video → load → all 5 links present grouped by role; stats — 10 items across 2 shot × 2 question → 4 rows correct counts; comment delete — admin can delete; transaction — link-insert failure rolls back item creation.
- **Verification:** tests pass; rollback leaves the item un-created.

## 3.7 mediaAssetsRouter + aiRouter + exportsRouter (parent U13)

- **Goal:** unified media listing, AI procedures wired to the AI service, the export endpoint, and the connectivity-reporting health check.
- **Requirements:** R6, R7, R8, R12, R17, R25.
- **Dependencies:** §3.1, §3.3, §3.4, §3.5, §3.6.
- **Files:** `packages/server/src/routers/{media-assets,ai,exports}.ts`, `packages/server/src/services/exports/index.ts`, `…/__tests__/exports.test.ts`, plus the raw routes in `apps/server/src/index.ts`.
- **Approach:**
  - **Health (R25):** the §1.2 `/health` route is upgraded here to actually probe dependencies — `storage.healthCheck()` (TOS), `db.execute(select 1)` (Neon), and a cheap AI reachability check — returning `{ ok, db, tos, ai }` with a non-200 when any dependency is down. R25 was unassigned in the parent; it lands here because the storage/AI/db services it must probe all exist by this unit. Stays a **public** raw route (no secrets in the payload — booleans only).
  - `mediaAssetsRouter.list({ kind?, mediaType?, dedup })` joins `asset_images`→`assets`, optionally dedups by `object_key`, returns presigned URLs (R12).
  - **Upload** — a Fastify multipart route (`@fastify/multipart`) streams the file to storage and returns the `object_key`; tRPC `assets.attachImage` then inserts the row. TOS write first; on insert failure schedule a deferred delete (Risk). **Upload size cap (in scope, parent U13):** enforce a hard `Content-Length`/multipart byte limit before buffering, so one upload can't exhaust host memory.
  - `aiRouter.generatePrompt/extractFields/generateImage` delegate to §3.3; `generateImage` handles `refImage` by fetching the referenced bytes from TOS and inlining them as a `data:` part (no separate edit endpoint).
  - **Export** — `exportsRouter` exposes a typed `getDownloadUrl`, but ZIP bytes stream over a **raw Fastify route** `GET /api/export/:kind.zip` (`requireSession` preHandler). `archiver` is piped into the Fastify `reply` **before** appends/`finalize()` (attach the drain target first — finalize-then-yield deadlocks). `exceljs` builds the XLSX manifest (EN→ZH headers from `shared/lib/exports/headers.ts`); entries append as bytes are fetched. `Content-Disposition: attachment`.
- **Test scenarios:** media list — shared images dedup to fewer rows; without dedup all rows; export ZIP — 5 assets → ZIP has XLSX + 1 image/row + correct count; AI procedures — each delegates to the mocked service; health — all deps up → `{ ok: true, db: true, tos: true, ai: true }` 200; one dep down (mocked storage throw) → `ok: false` + non-200.
- **Verification:** ZIP opens in a real tool; XLSX opens in Excel; images intact; `/health` returns per-dependency booleans and flips to non-200 when a probe fails.

## 3.8 batchRegenerate subscription (parent U14)

- **Goal:** batch-regenerate exposes an SSE subscription streaming per-item progress.
- **Requirements:** R18.
- **Dependencies:** §3.7.
- **Files:** `packages/server/src/routers/ai.ts` (extended), `…/__tests__/ai-batch.test.ts`. The client subscription wiring (`apps/web/src/lib/trpc.ts`, `httpSubscriptionLink`) is **parent U19 — out of scope here**; this plan delivers and tests the server-side `async function*` subscription procedure only.
- **Approach:** **Batch regenerate only** (export is a one-shot raw-route download, §3.7 — no subscription). Subscription emits `{ id, status: 'pending'|'done'|'failed', imageKey?, error? }` per item; each item's DB write happens **before** the yield so a dropped connection just means re-subscribe for unfinished IDs. **Resumption is the client-Set model only** (not `lastEventId`) — mixing the two double-counts (parent U14).
- **Test scenarios:** server subscription via `appRouter.createCaller(ctx)` (or the tRPC subscription test util) drives the `async function*` directly: 3 IDs → 3 `done` + `complete`; resumption — 5 IDs fail after 2 → re-subscribe with 3 → complete; per-item failure — 1 of 3 `failed`, other 2 succeed, no throw; ordering — each item's DB write is observable before its yield.
- **Verification:** server-side subscription test passes (no browser); the iterator yields one event per input id and persists before yielding. End-to-end UI consumption is verified in parent U19.

---

## Sequencing

Three phases, gated by dependency (matches the parent's Phase 1→2→3):

```
Phase 1 (Project init):   §1.1 → §1.2 → §1.3
                          §1.1 → §1.4              (env+DB, parallel to §1.2/§1.3)
Phase 2 (Data layer):     §1.4 → §2A(assets) → §2A(benchmark)
                          §2A → §2B → §2C          (schemas derive from tables)
                          §1.4 → §3.1 (storage)    (no schema dep)
Phase 3 (Server layer):   §3.1 → §3.3 (AI)
                          §1.3 → §3.2 (auth)
                          §2A,§3.1,§3.2 → §3.4 (assets)
                          §3.3,§3.4 → §3.5 (scenes)
                          §2A,§3.2,§3.4 → §3.6 (benchmark)
                          §3.3,§3.4,§3.5,§3.6 → §3.7 (media/ai/exports)
                          §3.7 → §3.8 (subscription)
```

Each phase lands and is tested before the next begins; later phases assume earlier ones are wired.

## Test strategy (this plan's surface)

- **Vitest projects from day one** (§1.2): `server` (PGlite-backed integration for routers + services), `shared` (pure-TS unit for Zod schemas + prompt builders). The `web` project exists but its tests are the parent's frontend units.
- **PGlite for server tests** (playbook §5.7): migrations run once at boot via `setupFiles`; the harness lives at `packages/server/src/db/__tests__/pglite.ts`. Swap is mechanical — same Drizzle interface.
- **Integration > unit for routers** — the router contract is what ships. Unit-test prompt selection and Zod parsers. Mock `openai` and the S3 client at their boundaries.

## Open questions (server-foundation only)

These don't block this plan; resolve before the dependent unit fires. The parent's full Open Questions list still applies for migration/deploy.

- **`audio`/`video` asset-kind disposition (blocks §2A schema freeze).** Legacy `assets.kind` allowed 5 values; this plan models 3 (decision RF-4). The *schema* call (narrow the CHECK / three-way union) is settled here as a deliberate decision. The remaining open item is purely a migration question for parent U20: **do any legacy rows with `kind` in (`audio`,`video`) actually exist**, and if so are they re-homed as `asset_images` or dropped as orphans? Confirm the row count before §2A lands — if a large population exists, RF-4 needs a re-home path, not just a drop.
- **Parent U20 needs the four-column FK backfill (RF-2).** As written, parent U20 copies only `video_input_id`/`video_output_id` verbatim and materializes links from the legacy link table; it does **not** coalesce the four 0003 FK-id columns (`character_image_id`/`scene_image_id`/`prop_image_id`/`audio_input_id`) or the six TEXT object-key columns into `media_links`. Under this plan's links-only `video_benchmark_items`, any item whose media lives only in a FK-id/TEXT column (no link row) loses that media. **Parent U20 must be edited** to add the six-role coalesce (link row → else FK-id column → else TEXT column) and a ≤1-link-per-single-cardinality-role parity assert. Tracked here; the edit lands in the parent.
- **Promoted-column nullability (§2A).** `name` is `NOT NULL` (per-kind derivation, RF-1: characters `COALESCE(title, persona, fallback)`, scenes/props `data->>'name'`); `era`/`genre` are nullable (not every kind has them — props have neither). Flag during U20 if any legacy row lacks every liftable `name` source.
- **AI procedure concurrency cap (§3.3/§3.7/§3.8).** `generateImage` and especially `batchRegenerate` can fan out many concurrent OpenRouter calls against a single long-lived host (KTD-4, no job queue). No per-host concurrency/rate cap is specified yet. Likely a small `p-limit` around the AI client. Decide the cap before §3.8 ships so a large batch can't exhaust sockets or trip provider rate limits.
- **PGlite parity for DEFERRABLE FK + partial unique index (§1.4 test harness).** The hand-appended `DEFERRABLE INITIALLY DEFERRED` FK and partial unique index (§2A) must behave identically under PGlite as under Neon Postgres for the transaction (§3.6) and cardinality tests to be meaningful. Verify PGlite's version supports both before relying on those tests; if not, those two invariants need a Neon-only integration check.
- **TOS credential compartmentalization (§1.4/§3.1).** `TOS_ACCESS_KEY_ID`/`TOS_SECRET_ACCESS_KEY` are full bucket credentials in env. Consider a least-privilege key scoped to the single bucket/prefix before production, so a host compromise can't reach unrelated TOS resources. Operational, not blocking M1.
- **Comment-author attribution under single-admin.** All comments are `admin@…` (RF-3). Acceptable for M1; revisit if multi-user lands.

## Sources

- Parent plan `docs/plans/2026-05-30-001-refactor-asset-library-stack-rebuild-plan.md` (origin — KTDs, requirements, full unit sequence).
- `backend/migrations/0001`–`0013` — the cumulative legacy schema this rebuild is grounded in (RF-1, RF-2).
- `backend/db.py` — legacy query/filter/ordering logic + the `data`-JSONB `name`/`era`/`genre` reads that establish RF-1; `TYPE_ORDER`/`GENRE_ORDER`/`AGE_ORDER`.
- `backend/main.py` — the 56-route legacy surface (parity target for 2C; the route diff itself is parent U22).
- `backend/ai.py` — the verbatim AI call shape ported in §3.3 (KTD-7).
- `backend/storage.py` — the TOS helper shapes mirrored in §3.1.
- nginx Basic-Auth config (legacy) — establishes RF-3 (app-level auth is net-new).
- Fastify + tRPC adapter — https://trpc.io/docs/server/adapters/fastify; tRPC v11 — https://trpc.io; Drizzle — https://orm.drizzle.team; drizzle-zod — https://orm.drizzle.team/docs/zod; Neon serverless driver — https://neon.tech/docs/serverless/serverless-driver; OpenAI Node SDK — https://github.com/openai/openai-node.
