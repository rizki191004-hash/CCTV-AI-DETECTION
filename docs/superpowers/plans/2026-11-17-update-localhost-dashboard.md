# Update Localhost Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the React localhost dashboard (`dashboard/src/App.tsx`) with resilient live camera auto-reconnection, dynamic backend online/offline connection state indicator, and compile the fresh production build to `dashboard/dist`.

**Architecture:**
1. **Dynamic Connection State (`dashboard/src/App.tsx`)**: Replace the static "Backend Connected" indicator with a real polling hook checking `GET /api/status`, showing connected (green) vs disconnected/reconnecting (yellow/red).
2. **Resilient Camera Stream Component (`dashboard/src/App.tsx`)**: Introduce a `CameraStream` player component with error detection, loading spinners, and automatic reconnect retries with cache-busting query timestamps, preventing streams from permanently disappearing when connection fluctuates.
3. **Frontend Compilation (`dashboard/dist`)**: Run `npm run build` using PowerShell with `$env:ComSpec = "C:\Windows\system32\cmd.exe"` to generate optimized static bundles served by FastAPI at `http://localhost:8000`.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS, Lucide React, FastAPI.

**Spec:** User requested "update juga dashbaord local host nya" — ensuring the localhost web view (`http://localhost:8000`) has all up-to-date features, robust stream reconnection, real-time connection state, and a fresh production build.

## Global Constraints

- Must compile cleanly with `npm run build` (zero TypeScript or ESLint errors).
- No new external npm packages.
- All existing 36 Python unit tests must continue to PASS.
- Stream player must never permanently hide on temporary disconnection.

## Review Focus

1. **Transient stream network drop**: Backend or RTSP stream temporarily buffers. Expected: UI displays "Menghubungkan ulang..." and automatically resumes once stream frames arrive without requiring manual page reload.
2. **Backend down or restart**: Backend is offline. Expected: Header badge updates from "Backend Connected" to "Terputus - Menghubungkan..." and stream cards show reconnect state.
3. **Fullscreen stream exit and retry**: ESC key or double-click exits fullscreen cleanly, preserving playback state.
4. **Vite production bundle hashing**: Clean asset filenames generated in `dashboard/dist/assets`.
5. **Static file serving**: FastAPI SPA fallback serves the newly compiled `index.html` and assets.

---

### Task 1: Enhance `dashboard/src/App.tsx` with Dynamic Connection State & Stream Auto-Reconnect

**Files:**
- Modify: `dashboard/src/App.tsx`

**Interfaces:**
- Produces: `CameraStream` component with auto-retry.
- Produces: `isBackendOnline` reactive status in header.

- [x] **Step 1: Implement `CameraStream` component and dynamic connection state in `App.tsx`**
- [x] **Step 2: Add auto-reconnect timer and cache-busting stream URL retry**
- [x] **Step 3: Update Header to display live backend status**

---

### Task 2: Build Production Frontend (`npm run build`)

**Files:**
- Build: `dashboard/dist/index.html`
- Build: `dashboard/dist/assets/*`

**Interfaces:**
- Produces: Bundled JS and CSS in `dashboard/dist/`.

- [x] **Step 1: Execute `npm run build` in `dashboard` directory**
- [x] **Step 2: Verify `dashboard/dist` assets exist and are freshly generated**

---

### Task 3: Verification & Test Suite

- [x] **Step 1: Run full Python unit test suite (`python -m unittest discover -s tests -v`)** — 37/37 PASS
- [x] **Step 2: Verify FastAPI test client serves new dashboard bundle on `/`**

