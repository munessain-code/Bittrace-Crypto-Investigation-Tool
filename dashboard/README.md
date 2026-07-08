# BitTrace Dashboard

Next.js Graph Explorer for interactive money-flow tracing on Elliptic++.

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Start the dev server (port 3000)
npm run dev
```

The dashboard connects to the FastAPI backend at `http://localhost:8000` by default.
Set `NEXT_PUBLIC_API_URL` in `.env.local` to override.

## Tabs

| Tab | Description |
|---|---|
| **Explorer** | Force-directed graph. Click nodes to inspect, trace upstream/downstream, expand neighbors. |
| **Macro** | Class distribution, timestep heatmap (click to filter), class-to-class flow. |
| **Story Mode** | Step-through investigation stories synced with graph highlights. |

## Components

- `GraphExplorer/` — Cytoscape canvas (react-force-graph-2d) with trace + expand controls
- `MacroOverview/` — Stats cards + timestep heatmap
- `StoryPanel/` — Story carousel synced with graph highlights
- `NodeInspector/` — Side panel with attributes, class, trace actions
- `lib/graph-api.ts` — Typed fetch client for all 6 API endpoints
