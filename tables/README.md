# Tables

Machine-readable data for implementations. All CC0 1.0. Generate your
tables from these rather than copying them by hand; each file names its
build, binary and the addresses it was read at.

| File | What | Rules |
|---|---|---|
| [pathnodes.json](pathnodes.json) | The engine's built-in path-node layouts: for each of 48 letters and path-node orientations 0-3, node positions, exit points and each exit's owner, in the canonical tile frame. Dumped from the running server (T15). | SET-NODE-001..004, SET-FILE-012 |
| [constants.yaml](constants.yaml) | Named constants and unnamed literals of the pathfinder, with addresses; call caps and budgets. | spec/route.md, spec/intra.md |
| [exit_candidates.yaml](exit_candidates.yaml) | The crossing candidate table, weights and scores of `GenerateBestIntraTileExit`. | SET-INTRA-040..043 |
| [set_slots.yaml](set_slots.yaml) | `.set` corner and edge keys and their slots; how edge tiles build their keys and rotations. | SET-FILE-020, SET-FILE-021, SET-EDGE-020..040 |

## pathnodes.json

```json
{
  "letters": "ABCDEFGHIJKLMNOQRSUVWXYZabcdefghijklmnopqrstuvwx",
  "edge_points": [[0.0, 1.0], ...],
  "layouts": {
    "A": {
      "0": {"nodes": [[5.0, 5.0]],
            "exits": [[5.0, 10.0], [0.0, 5.0], [10.0, 5.0], [5.0, 0.0]],
            "exit_node": [0, 0, 0, 0]},
      "1": {...}, "2": {...}, "3": {...}
    },
    ...
  }
}
```

- The orientation key is the path-node orientation: the `.set`
  `Orientation` in degrees divided by 90 (SET-FILE-010).
- Coordinates are metres in the canonical tile frame, x east, y north,
  0..10, as the server's `ComputePathNodeInformation` returns them (single
  precision values, all exactly representable).
- A node's region number is its index in `nodes`. Exit order matters: it
  is the order successors are generated in (SET-ROUTE-023) and the exit
  numbers denials use (SET-NODE-020).
- `P` and `T` are absent: the engine returns no nodes and no exits for
  them.

The file was produced by Layonara Landscaper's
`research/dump_pathnodes_gdb.py`, which calls
`CNWTileSetManager::ComputePathNodeInformation` (0x3f3ea0) in the running
server for every letter and orientation; the numbers are the engine's
output, not a copy of a game file.
