# BitTrace Graph Explorer — JSON Schema

## Subgraph file (e.g., `easy_case.json`)

```json
{
  "metadata": {
    "difficulty": "easy|average|hard",
    "seed_node": 272145560,
    "seed_class": 1,
    "seed_timestep": 1,
    "depth": 3,
    "budget": 500,
    "node_count": 234,
    "edge_count": 233,
    "description": "..."
  },
  "nodes": [
    {
      "data": {
        "id": "272145560",
        "label": "272145560",
        "class": 1,
        "class_label": "illicit",
        "color": "#ef4444",
        "hop": 0,
        "timestep": 1
      }
    }
  ],
  "edges": [
    {
      "data": {
        "id": "e_272145560_11747137",
        "source": "272145560",
        "target": "11747137"
      }
    }
  ]
}
```

## Cytoscape.js integration

The `nodes` and `edges` arrays are Cytoscape.js-compatible and can be
passed directly to `cy.add()`. The `data` keys map to Cytoscape element
properties:

| Key | Type | Description |
|---|---|---|
| `id` | string | Unique identifier |
| `class` | int | 1=illicit, 2=licit, 3=unknown |
| `class_label` | string | Human-readable label |
| `color` | string | Hex color for visualization |
| `hop` | int | BFS distance from seed (trace only) |
| `timestep` | int | Time bucket (1-20) |

## Phase 8 frontend requirements

1. Load JSON via `fetch()` or pre-bundle
2. Render with Cytoscape.js or D3 force layout
3. Color nodes by `data.color`
4. Filter by class, timestep, hop depth
5. Click node → show metadata panel with class, timestep, hop
6. Animated trace: reveal nodes hop-by-hop
