# Precomputed Subgraphs

These subgraph files are Cytoscape.js-compatible JSON exports of case-study transactions from the Elliptic++ dataset.

## Files

- **easy_case.json** — Easy difficulty case
- **average_case.json** — Average difficulty case
- **hard_case.json** — Hard difficulty case

## Selection Criteria

| Difficulty | Criteria |
|---|---|
| Easy | Illicit tx with clear peel chain (>3 hops) and few branches |
| Average | Illicit tx with moderate fan-out and mixed class neighbors |
| Hard | Illicit tx deeply embedded in unknown-class nodes with high connectivity |

## Schema

Each file contains:
- `metadata`: difficulty, seed_node, seed_class, depth, node_count, edge_count
- `nodes`: [{data: {id, label, class, class_label, color, hop, timestep}}]
- `edges`: [{data: {id, source, target}}]

## Generation

```python
from src.viz.precompute import precompute_subgraphs
precompute_subgraphs(depth=3, budget=500)
```
