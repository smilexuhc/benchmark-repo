---
title: feat: Add benchmark item management page
type: feat
status: completed
date: 2026-05-25
---

# feat: Add benchmark item management page

## Summary

Add a new frontend tab named “题目” for managing video benchmark item records through the existing `/api/video-benchmark-items` CRUD API. The page should support listing, searching, filtering, pagination, creating, and editing records, while staying visually consistent with the current React + Ant Design asset-library UI.

---

## Problem Frame

The backend now exposes a dedicated video benchmark item data domain, but the application still only has UI surfaces for “角色资产库” and “场景资产库”. Users need a first-class page to create and update benchmark questions without calling the API manually.

---

## Requirements

- R1. Add a top-level “题目” navigation option beside the existing角色/场景 tabs.
- R2. Display benchmark item records from `/api/video-benchmark-items` with pagination, loading, empty, and error states.
- R3. Support `q` search plus filters for `shot_type`, `task_type`, `question_type`, `scene`, `screen_size`, and `score`.
- R4. Support creating benchmark item records with all fields from the backend contract.
- R5. Support editing existing benchmark item records with full-field update behavior.
- R6. Preserve existing角色/场景 asset-library behavior and avoid coupling benchmark items to image generation, asset package export, or TOS image galleries.

---

## Scope Boundaries

- No import/export for benchmark items in this plan.
- No delete action unless the user explicitly asks for it later; this plan covers create and edit only.
- No AI prompt generation, image generation, upload, or asset-library batch generation on the “题目” page.
- No backend schema/API changes unless implementation discovers a contract mismatch in the already-added CRUD API.
- No new frontend test framework dependency unless the implementer confirms the repo already has one available.

### Deferred to Follow-Up Work

- CSV/XLSX import/export for题目 records.
- Selecting existing角色/场景 assets from the asset libraries instead of typing text references.
- Dashboard/statistics views for score distribution or task coverage.

---

## Context & Research

### Relevant Code and Patterns

- `frontend/src/App.tsx` owns the top-level Segmented navigation and currently switches between角色 and场景 pages.
- `frontend/src/api.ts` centralizes typed fetch helpers and API-specific wrappers.
- `frontend/src/types.ts` centralizes shared TypeScript interfaces, field labels, filter fields, and empty input objects.
- `frontend/src/components/CharacterDrawer.tsx` and `frontend/src/components/SceneDrawer.tsx` show the local drawer form pattern: local form state, save loading state, AntD messages, and footer actions.
- `frontend/src/components/AssetLibrary.tsx` is useful as layout inspiration, but it is tightly coupled to images, prompt generation, export, and batch generation, so the题目 page should use a dedicated component.
- `backend/main.py` already exposes `/api/video-benchmark-items` list/get/create/update/delete routes with score validation.

### Institutional Learnings

- No relevant `docs/solutions/` or existing brainstorm/plan docs were present in this repo.
- Memory for this repo concerns remote data sync and Neon/TOS migration, not benchmark-item frontend management.

### External References

- External research is not needed; the repo already uses a clear local React + Ant Design pattern.

---

## Key Technical Decisions

- Build a dedicated `BenchmarkItemsPage` instead of adapting `AssetLibrary`: benchmark items are tabular records, not image assets, and should not inherit unrelated export/generation controls.
- Keep API and type additions in `api.ts` and `types.ts`: this matches the existing frontend contract organization and avoids scattering fetch details across components.
- Use an AntD `Table` with server-side pagination and filters/search parameters: this matches the backend API shape and avoids loading all题目 records into the browser.
- Use a right-side `Drawer` for create/edit: this matches the existing editing experience for角色/场景 and keeps the main list visible.
- Treat score as `number | null` in frontend state: `null` represents未评分 and maps directly to the backend contract.

---

## Open Questions

### Resolved During Planning

- Should this reuse `AssetLibrary`? No. The existing component is image/prompt-generation specific; use a dedicated题目 component while reusing visual conventions.
- Should delete be included? No. The user asked for修改 and创建 only, so delete remains out of scope.
- Should option lists come from backend? No. The current backend does not expose benchmark options; derive filter choices from the loaded page initially or use text/search controls, and defer richer options.

### Deferred to Implementation

- Exact column widths and responsive wrapping: choose during UI implementation based on real viewport behavior.
- Whether long media-reference fields should render as copied text, truncated text, or tooltips: decide during implementation while checking readability.

---

## Implementation Units

- U1. **Add frontend benchmark item API and types**

**Goal:** Define the TypeScript contract and API wrapper for `/api/video-benchmark-items` so UI code can call list/get/create/update with typed inputs and paginated responses.

**Requirements:** R2, R3, R4, R5

**Dependencies:** Backend CRUD API from the prior implementation.

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Test: none -- this repo has no frontend test runner; verify through TypeScript build and browser smoke scenarios.

**Approach:**
- Add `VideoBenchmarkItem`, `VideoBenchmarkItemInput`, and `VideoBenchmarkItemListResponse` types.
- Add field label constants for all题目 fields, including `Score（0-5分）`.
- Add an `emptyVideoBenchmarkItem` input object.
- Add `videoBenchmarkApi` with list/get/create/update methods.
- Ensure list serializes `limit`, `offset`, `q`, filter fields, and `score` using URL query params compatible with the backend.

**Patterns to follow:**
- `frontend/src/api.ts` `req<T>()` and existing API object style.
- `frontend/src/types.ts` existing `CharacterInput`, `SceneInput`, `FIELD_LABELS`, and empty-input patterns.

**Test scenarios:**
- Happy path: list call with default pagination builds a request that returns `{ items, total, limit, offset }`.
- Happy path: create/update calls send all input fields without `id`, `created_at`, or `updated_at`.
- Edge case: `score: null` is preserved as an unscored value in request state.
- Error path: backend non-OK responses still surface `detail` through the existing `req<T>()` helper.

**Verification:**
- TypeScript accepts all new API/type usage.
- Existing角色/场景 API exports remain unchanged.

---

- U2. **Create the “题目” list page**

**Goal:** Build the page-level list UI for benchmark items with search, filters, pagination, and edit entrypoints.

**Requirements:** R1, R2, R3, R6

**Dependencies:** U1

**Files:**
- Create: `frontend/src/components/BenchmarkItemsPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: none -- this repo has no frontend test runner; verify through TypeScript build and browser smoke scenarios.

**Approach:**
- Add a new `topic` tab value in `App.tsx` with label “题目”.
- Render `BenchmarkItemsPage` when the tab is selected.
- Use an AntD `Table` for records, with concise columns for ID,镜头类型,任务类型,题目类型,场景,屏幕尺寸,Score, and更新时间.
- Show longer fields such as素材引用、音频/视频输入、文字提示词、视频输出 with truncation/tooltip or expandable detail inside the row/list design.
- Add top toolbar with search input and “新建题目” primary button.
- Use server-side pagination from the backend response; table page changes update `limit`/`offset` and reload data.
- Implement filters for the planned fields without inventing a backend options endpoint: use text controls/selects based on currently loaded values where practical, and keep search as the primary broad query path.

**Patterns to follow:**
- `frontend/src/components/AssetLibrary.tsx` for top toolbar, loading/empty/error message behavior, and full-height layout.
- `frontend/src/App.tsx` current Segmented navigation style.

**Test scenarios:**
- Happy path: selecting “题目” loads the first page and shows rows returned by the API.
- Happy path: typing search text updates `q` and reloads records.
- Happy path: changing table pagination updates `limit`/`offset` and displays the new page.
- Edge case: empty API response shows a clear empty state rather than a blank table.
- Error path: failed list request shows the backend error via AntD message and leaves the page usable.
- Regression: switching between “角色资产库”, “场景资产库”, and “题目” does not break the existing two asset pages.

**Verification:**
- “题目” appears in the top navigation.
- Existing角色/场景 tabs still render their original pages.
- The题目 page does not show asset-specific buttons like导出资产包、批量生成、生成图片.

---

- U3. **Add create/edit drawer for benchmark items**

**Goal:** Allow users to create and modify benchmark item records through a drawer form covering every backend field.

**Requirements:** R4, R5

**Dependencies:** U1, U2

**Files:**
- Create: `frontend/src/components/BenchmarkItemDrawer.tsx`
- Modify: `frontend/src/components/BenchmarkItemsPage.tsx`
- Test: none -- this repo has no frontend test runner; verify through TypeScript build and browser smoke scenarios.

**Approach:**
- Follow the existing drawer pattern: local `form` state, `saving` state, AntD message feedback, and footer buttons.
- Title should be “新建题目” for create and “编辑题目” for edit.
- Include all fields in a structured form:
  - Basic classification:镜头类型、任务类型、题目类型、场景、屏幕尺寸、Score.
  - Material/input/output references:人物图片素材、场景图片素材、道具图片素材、音频输入、视频输入、文字提示词、视频输出.
- Use text inputs for short fields, text areas for long references/prompts/outputs, and numeric/select control for score with a nullable未评分 state.
- On successful create/update, refresh the table and keep the drawer in a predictable state: created records become the current edit target or the drawer closes, following whichever feels closest to existing drawer behavior during implementation.

**Patterns to follow:**
- `frontend/src/components/CharacterDrawer.tsx` and `frontend/src/components/SceneDrawer.tsx` for form state, drawer footer, save loading, and message handling.

**Test scenarios:**
- Happy path: clicking “新建题目”, filling fields, and saving calls create and refreshes the list.
- Happy path: clicking an existing row/action opens the drawer populated with that record.
- Happy path: editing fields and saving calls update and refreshes the row/list.
- Edge case: leaving optional text fields blank sends empty strings.
- Edge case: selecting未评分 sends `score: null`.
- Error path: score values outside 0-5 are blocked in the UI or rejected cleanly with backend error text.
- Error path: failed create/update keeps the drawer open and preserves user input.

**Verification:**
- Every backend field is visible and editable in the drawer.
- Create and update both round-trip through the API wrapper.
- No delete UI is introduced.

---

- U4. **Polish layout and run acceptance verification**

**Goal:** Ensure the new题目 page feels coherent with the existing app and that the full feature works without regressing current asset pages.

**Requirements:** R1, R2, R3, R4, R5, R6

**Dependencies:** U1, U2, U3

**Files:**
- Modify: `frontend/src/index.css` if reusable small utility styles are needed.
- Test: none -- this repo has no frontend test runner; verify through TypeScript build and browser smoke scenarios.

**Approach:**
- Keep the page quiet and operational: dense table/list layout, restrained styling, no landing-page treatment.
- Ensure long text does not overflow table cells or drawer fields.
- Confirm loading, empty, error, and saved states are visually legible.
- Run TypeScript build verification and browser smoke verification against the local Vite app.

**Patterns to follow:**
- Existing AntD theme and spacing in `frontend/src/main.tsx`, `frontend/src/App.tsx`, and `frontend/src/components/AssetLibrary.tsx`.

**Test scenarios:**
- Integration: create a record through the drawer, confirm it appears in the list.
- Integration: edit the created record, confirm updated values appear after refresh.
- Integration: search/filter finds the created record by prompt/classification fields.
- Regression:角色 and场景 pages still load, edit drawers still open, and no benchmark-specific controls appear there.
- Responsive smoke: desktop-width page keeps toolbar/table/drawer readable without text overlap.

**Verification:**
- `frontend` build passes.
- Browser smoke test confirms the “题目” flow can create and edit records.
- Existing backend migration requirement remains documented: the database must have `video_benchmark_items` before the page can load real data.

---

## System-Wide Impact

- **Interaction graph:** The new page calls the existing FastAPI CRUD endpoints through the same frontend fetch helper used by other pages.
- **Error propagation:** Backend `detail` errors should surface via the existing `req<T>()` helper and AntD messages.
- **State lifecycle risks:** Create/update must refresh list state after success; failed saves should not discard local drawer input.
- **API surface parity:** This plan uses the already-created backend API only; it does not change role/scene asset APIs.
- **Integration coverage:** Browser smoke is required because the feature crosses frontend state, API calls, and backend persistence.
- **Unchanged invariants:** Existing角色/场景 asset-library image generation, upload, cover, export, and batch generation behavior must remain unchanged.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Backend migration not applied in the target environment | Treat `/api/video-benchmark-items` failures as visible errors; ensure deployment runs existing migrations before frontend use. |
| Existing `AssetLibrary` is tempting to reuse but carries unrelated behavior | Use a dedicated题目 page and drawer while copying only layout conventions. |
| Long prompt/media-reference text harms table readability | Use truncation, wrapping, and drawer detail editing rather than forcing all text into narrow cells. |
| No frontend test framework exists | Use TypeScript build plus browser smoke scenarios; defer test framework introduction to a separate decision. |

---

## Documentation / Operational Notes

- Update `README.md` only if the implementation wants the功能 section to mention the new “题目” tab.
- No new environment variables are required.
- Deployment depends on the existing migration path applying `backend/migrations/0002_create_video_benchmark_items.sql`.

---

## Sources & References

- Related backend API: `backend/main.py`
- Related backend storage helpers: `backend/db.py`
- Related migration: `backend/migrations/0002_create_video_benchmark_items.sql`
- Frontend entrypoint: `frontend/src/App.tsx`
- Frontend API/types: `frontend/src/api.ts`, `frontend/src/types.ts`
- Existing drawer patterns: `frontend/src/components/CharacterDrawer.tsx`, `frontend/src/components/SceneDrawer.tsx`
- Existing list layout reference: `frontend/src/components/AssetLibrary.tsx`
