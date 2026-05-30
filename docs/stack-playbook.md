---
title: Stack Playbook (yose-chat patterns)
status: reference
date: 2026-05-30
---

> **Reference menu, not a contract.** Adopt the patterns that fit a given project; deviate where the project needs something different and record the deviation. The Asset Library Stack Rebuild plan, for example, deviates on the Neon driver (it needs interactive transactions).

A portable cheat sheet of the techniques, so you can apply the same patterns in a fresh project. Assumes you already know React, Vercel, and Neon DB.

---

## 1. High-level architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (React 19 + TanStack Router + TanStack Query)      │
│        │                                                     │
│        │ typed tRPC calls (superjson)                        │
│        ▼                                                     │
│  TanStack Start (SSR) ── Nitro/H3 (server runtime) ── Vercel│
│                       │                                      │
│                       ▼                                      │
│         tRPC routers ── better-auth ── Drizzle ── Neon       │
└─────────────────────────────────────────────────────────────┘
```

- One **monorepo** (pnpm workspaces) with `apps/web`, `packages/server`, `packages/shared`.
- Strict dependency direction: `web → server → shared`. `shared` must stay pure TS (no React, no Node-only APIs).
- All runtime deps live in `apps/web/package.json`. `packages/*` only declare workspace deps. This works because `.npmrc` sets `node-linker=hoisted`.

---

## 2. Stack at a glance

| Layer            | Library                                                                  |
| ---------------- | ------------------------------------------------------------------------ |
| Framework        | TanStack Start (SSR) + TanStack Router + Vite 7                          |
| Server runtime   | Nitro (`vercel` preset) + H3                                             |
| API              | tRPC v11 + `@trpc/tanstack-react-query` + superjson                      |
| Auth             | better-auth (plugins: admin, phoneNumber, emailOTP)                      |
| DB               | Drizzle ORM + drizzle-kit + drizzle-zod, Postgres via Neon serverless    |
| Validation       | Zod v4 (single source of truth, derive types from schema)                |
| State (client)   | Zustand + `combine` + `immer`; `use-immer` for local; `nuqs` for URL     |
| Forms            | react-hook-form + `@hookform/resolvers/zod`                              |
| UI               | Tailwind v4 + Base UI + Radix Slot + **coss UI** (NOT shadcn)            |
| AI               | Vercel AI SDK v6 + provider packages (anthropic, openai, deepseek, etc.) |
| Lint/format      | Biome 2 (replaces ESLint + Prettier)                                     |
| Tests            | Vitest 4 with `test.projects` split + PGlite for server tests            |
| Env              | `@t3-oss/env-core` with Zod schema                                       |
| Utility          | `lodash-es` (prefer over hand-rolled), `ts-pattern` for exhaustive match |
| Hooks/git        | husky + lint-staged                                                      |

---

## 3. The architectural rules that matter

These are the rules that prevent the project from rotting. Carry them over.

### Type discipline
- **Single source of truth.** DB schema → drizzle-zod → derived types. Never redefine the same shape in two places.
- **No `index.ts` barrel files.** Import directly from the defining file. Barrels cause circular imports and slow builds.
- **No `as any`, `@ts-ignore`, `@ts-expect-error`.** Fix the type.
- `noUncheckedIndexedAccess: true` in tsconfig.
- Path aliases (`@/lib/*`, `@/server/*`, `@/constant/*`, `@/env`, `@/*`) declared identically in `tsconfig.json` and `vitest.config.ts`.

### State management
- **Zustand pattern:** `create(immer(combine({ state }, (set, get) => ({ actions }))))`.
- Standard action: `update: set` exposed so callers can patch state freely.
- Inside an action calling another action → `this.someAction()` (because `combine`'s `get()` returns state only).
- After `await` in an async action → switch to `useStore.getState().someAction()` (avoids `this` loss).
- **Never use selector pattern for updates**, only for reads. Use `useStore.setState(updater)` for writes — keeps `useCallback` deps clean.

### API boundary
- **Always tRPC, never TanStack Start server functions.** tRPC gives you isomorphic client + vanilla caller in one type system.
- Use `createClientCaller()` (vanilla tRPC) outside React components — including inside zustand actions.
- All inputs validated with Zod. Never trust raw input even on internal RPC.
- **Cursor-based pagination only.** Never offset.

### Database
- Schema lives in one file. Never hand-write SQL or migrations.
- Workflow: edit `db/schema.ts` → `pnpm db:gen` → `pnpm db:migrate`.
- Use Drizzle transactions for any multi-row write that must stay consistent (esp. payments). Interactive transactions require the WebSocket Pool driver — the HTTP driver only supports non-interactive batches.

### Serverless safety (Vercel)
- No process-affinity assumptions. Every request may hit a fresh process.
- No in-memory event buses, no module-level `Set`s for idempotency.
- Idempotency = persisted state in DB with transactions.
- Subscription/feature-flag expiry = **lazy refresh on read** (e.g., `getUserBalance()` refreshes if expired). Avoid cron.

### File and folder conventions
- `kebab-case` for files and folders.
- Co-located tests in `__tests__/*.test.ts` next to the code.
- UI text in Chinese (project-specific — drop if not applicable).

---

## 4. Monorepo skeleton to copy

```
your-project/
├── apps/
│   └── web/                # TanStack Start + Vite app
├── packages/
│   ├── server/             # tRPC, auth, db, services
│   └── shared/             # Zod schemas, constants, pure utils, env
├── pnpm-workspace.yaml
├── .npmrc                  # node-linker=hoisted
├── tsconfig.base.json
├── biome.json
├── vitest.config.ts        # root-level, test.projects splits
└── .husky/pre-commit       # pnpm lint-staged
```

Minimal `pnpm-workspace.yaml`:

```yaml
packages:
  - apps/*
  - packages/*
```

Minimal `.npmrc`:

```
node-linker=hoisted
```

---

## 5. Setup recipes (per technique)

### 5.1 TanStack Start + Nitro + Vercel

`vite.config.ts` plugin order matters:

```ts
plugins: [
  tsConfigPaths({ projects: [/* all tsconfigs */] }),
  tanstackStart(),
  nitro(),            // after Start
  viteReact(),        // after Start
  tailwindcss(),
]

nitro: {
  preset: 'vercel',
}
```

Key insight: **the server has no standalone listener.** You mount `apiHandler` from your server package via a catch-all route at `src/routes/api/$.ts`.

### 5.2 tRPC isomorphic call sites

- Inside React: `const { data } = trpc.foo.bar.useQuery(input)` via `@trpc/tanstack-react-query`.
- Anywhere else (zustand action, util, etc.): `await trpcClient.foo.bar.query(input)` — same router type, no React deps.
- Export `AppRouter` type from `packages/server/src/index.ts` — that's the only thing the client imports from server.
- Use `superjson` as the transformer so Dates, Maps, Sets cross the wire intact.

### 5.3 Drizzle + Neon

- Default driver: `@neondatabase/serverless` (HTTP-based, fits Vercel).
- **Caveat:** the HTTP driver only supports non-interactive (batched) transactions. If you need interactive transactions — read a row mid-transaction and branch on it — use the WebSocket **Pool** driver (`Pool` + `drizzle-orm/neon-serverless`) instead. Pick per project.
- One `db/schema.ts` file, one `db/index.ts` that exports the configured client.
- For tests, swap the same import for **PGlite** (embedded Postgres in WASM) — see §5.7.

### 5.4 better-auth

- Configure in `packages/server/src/auth/index.ts`.
- Run `npx @better-auth/cli generate` to emit Drizzle schema additions into `db/auth.gen.ts`.
- Never hand-edit the generated file.
- Plugins compose: `admin()`, `phoneNumber()`, `emailOTP({ sendOTP })`, etc. — add only the ones a project needs.
- Reference: https://better-auth.com/llms.txt

### 5.5 Vercel AI SDK v6

- Each provider is its own package: `@ai-sdk/anthropic`, `@ai-sdk/openai`, `@ai-sdk/deepseek`, `@openrouter/ai-sdk-provider`.
- Build a unified model catalog in `packages/shared/src/lib/models/` so client and server agree.
- Streaming endpoint: SSE `data: <json>\n\n`, terminate with `data: [DONE]\n\n`.
- For malformed tool-call JSON from model outputs, use `jsonrepair` before parsing.
- Use `ai-retry` for transient provider errors; `tokenx` for token counting.

### 5.6 Coss UI (the shadcn alternative)

- Read https://coss.com/ui/llms.txt before generating components.
- Migration guide: https://coss.com/ui/docs/radix-shadcn-migration — APIs differ from shadcn even when components look the same.
- `pnpm dlx shadcn@latest add` is still the CLI used to scaffold; pipeline is configured via `components.json`.
- Built on Base UI + Radix Slot underneath.
- Don't modify `components/ui/*` unless explicitly asked — treat as generated.

### 5.7 Testing with Vitest projects + PGlite

Root `vitest.config.ts` splits projects so test cost is isolated:

```ts
test: {
  projects: [
    { name: 'web',    include: ['apps/web/src/**/*.test.*'] },
    { name: 'server', include: ['packages/server/src/**/*.test.*'],
      setupFiles: ['packages/server/src/mock/setup.ts'] },
    { name: 'shared', include: ['packages/shared/src/**/*.test.*'] },
  ],
}
```

- Server `setup.ts` mocks `@/env`, swaps the real Drizzle client for one bound to PGlite, and mocks `resend`.
- Migrations run once on PGlite at boot.
- Web/shared projects boot instantly because they skip that setup.
- Co-locate tests in `__tests__/*.test.ts`. Mock `@/env` per-file in web/shared.

### 5.8 Environment variables

`packages/shared/src/env.ts` using `@t3-oss/env-core`:

```ts
export const env = createEnv({
  server: { DATABASE_URL: z.string().url(), OPENAI_API_KEY: z.string() },
  client: { /* must be prefixed (VITE_, NEXT_PUBLIC_, etc.) */ },
  runtimeEnv: process.env,
})
```

Both server and client read from `@/env`. Tests mock `@/env`, never `process.env`.

### 5.9 Biome

One `biome.json` at root. Rules:
- 2-space indent, 100 col width, single quotes, asNeeded semicolons, no trailing commas.
- Husky pre-commit runs `pnpm lint-staged` → `biome format --write` on staged files.
- CI/CLI: `pnpm lint` (errors only).

### 5.10 Zustand + immer + combine recipe

```ts
import { create } from 'zustand'
import { combine } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

export const useChatStore = create(
  immer(
    combine(
      { messages: [] as Message[], pending: false },
      (set, get) => ({
        update: set,
        async send(text: string) {
          set((s) => { s.pending = true })
          const reply = await trpcClient.chat.send.mutate({ text })
          useChatStore.getState().appendMessage(reply) // post-await: getState
        },
        appendMessage(m: Message) {
          set((s) => { s.messages.push(m) })
        },
      }),
    ),
  ),
)
```

Persistence: wrap with `persist()` middleware only when the data needs to survive reloads.

---

## 6. Anti-patterns to refuse

- `useState` for global/cross-component state → zustand.
- Selector functions inside `setState` calls → use `useStore.setState(updater)` directly.
- `index.ts` re-exports → import from the source file.
- Re-defining the same Zod schema or type in two places.
- Server functions (TanStack Start `createServerFn`) → tRPC procedure.
- Shadcn component patterns when project is on coss UI.
- Cron jobs for "expiring" data → lazy refresh on read.
- Module-level `Map`/`Set` for idempotency on Vercel.
- Hand-rolled utility when `lodash-es` has it.
- Inline styles → Tailwind classes.
- Empty catch blocks.

---

## 7. The minimum viable copy-paste

If you bootstrap a new project tomorrow, the smallest useful subset is:

1. pnpm workspaces + Biome + husky/lint-staged.
2. TanStack Start app with Nitro `vercel` preset.
3. tRPC + superjson + `@trpc/tanstack-react-query`.
4. Drizzle + Neon driver + drizzle-zod, schema-derived types.
5. better-auth wired into the same Drizzle instance.
6. Zod env via `@t3-oss/env-core`.
7. Zustand + immer + combine pattern.
8. Vitest with `test.projects` (split immediately even if only one project, so PGlite swap-in stays easy later).
9. Tailwind v4 via `@tailwindcss/vite`.
10. coss UI (or your preferred design system) — pick once and forbid the other.

Everything else (AI SDK, payments, virtualization, markdown rendering) layers on cleanly once the above is in place.

---

## 8. Reference docs to bookmark

- TanStack Start — https://tanstack.com/start
- TanStack Router — https://tanstack.com/router
- TanStack Query — https://tanstack.com/query
- tRPC v11 — https://trpc.io
- Drizzle ORM — https://orm.drizzle.team
- better-auth — https://better-auth.com/llms.txt
- Vercel AI SDK — https://sdk.vercel.ai
- Nitro — https://nitro.build
- Vite — https://vite.dev
- Biome — https://biomejs.dev
- Zustand — https://zustand.docs.pmnd.rs
- Zod v4 — https://zod.dev
- t3-env — https://env.t3.gg
- coss UI — https://coss.com/ui/llms.txt
- Neon serverless driver — https://neon.tech/docs/serverless/serverless-driver
