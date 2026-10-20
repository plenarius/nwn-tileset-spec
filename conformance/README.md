# Route corpus

Routes walked by a creature on the real server over generated areas, and
what happened. All CC0: the areas are our own generated terrain, the
results our own measurements.

| Path | What |
|---|---|
| [routes/v1/](routes/v1/), [v2/](routes/v2/), [v3/](routes/v3/) | One JSON file per case: 40 routes each, as the server walked them |
| [manifest.json](manifest.json) | Each case: terrain, seed, generator revision and settings, how to regenerate the area and re-record the routes, counts, and the simulator's recorded agreement |
| [tools/compare.py](tools/compare.py) | Compares your predictions with the recorded results (standard-library Python) |

25 cases, 1,000 routes: 998 reachable on the ground truth, 897 arrived on
the server. Build 89.8193.37-17, `nwserver-linux`.

## What a case is

A case is one generated area and 40 random routes over it. Each route
file is a list of:

```json
{"from": [x, y], "to": [x, y], "reachable": true, "end": [x, y], "arrived": true}
```

- `from`, `to`: the start and goal, world metres (x east, y north, origin
  at the area's south-west corner), rounded to 0.1 m and stored as f32;
- `reachable`: whether start and goal are connected on the generator's
  ground truth: the terrain sampled every 0.5 m, a sample walkable when no
  4-neighbour rises more than the slope limit (face normal z >= 0.64) and
  it is not blocked, connected through 4-neighbours. It is not the
  engine's view, and it is approximate (one rugged route the grid called
  unreachable arrived);
- `end`: where the creature stood after 40 s;
- `arrived`: `end` within 1.5 m of `to`.

### The creature and the order

For each route, one module script (Landscaper `src/oracle.rs`, `script`)
did:

```
o = CreateObject(OBJECT_TYPE_CREATURE, "nw_dog", Location(area, from, 0.0))
ApplyEffectToObject(DURATION_TYPE_PERMANENT, SupernaturalEffect(EffectCutsceneGhost()), o)
SetAILevel(o, AI_LEVEL_HIGH)
AssignCommand(o, ActionMoveToLocation(Location(area, to, 0.0), TRUE))
DelayCommand(40.0, <log GetPosition(o)>)
```

All 40 routes of a case start at once in one server run. The creatures are
ghosts, so they do not block each other. `SetAILevel` matters: with no
player in the area a creature's scripted moves run at a low AI level and
only walk straight (engine/method.md). `nw_dog` is a stock blueprint, named
only; under gdb its requests had radius 0.4, height 1.0, no goal range, no
flip, and a budget of 1000 µs a call. `CreateObject` may move the start
(SET-ROUTE-050): two v1 starts within about 0.4 m of non-walkable ground
were moved.

### The areas

All areas come from Layonara Landscaper's generator (to be published).
Area coordinates are metres from the south-west corner; tiles are 10 m.

- **cliff\<h\>** (4 × 4 tiles, 40 × 40 m). Height:
  ```
  hill  = 2.5 * exp(-((x - 10)^2 + (y - 30)^2) / 40)
  ramp  = smoothstep(2, 4, y) * (1 - smoothstep(8, 10, y))
  cliff = smoothstep(24, 24.6, x)
  slope = smoothstep(14, 26, x)
  s     = cliff + (slope - cliff) * ramp
  z     = hill * (1 - s) + h * s
  ```
  with `smoothstep(e0, e1, x)` = t²(3 - 2t), t = clamp((x - e0)/(e1 - e0),
  0, 1). A hill in the north-west, a plateau of height h east of x = 24
  behind a cliff, and a ramp up to it between y = 3 and y = 9. Set with
  `LS_CLIFF=<h>`.
- **flat** (4 × 4 tiles). z = 0; ground with x in [24, 25) and y >= 10 is
  blocked (non-walkable): the cliff's layout without height. Set with
  `LS_FLAT=1`.
- **rugged** (8 × 8 tiles, 80 × 80 m). Terraced fractal noise:
  ```
  n = sum over o = 0..3 of 0.5^o * value_noise(x * f_o, y * f_o, 7 + o),  f_o = 2^o / 22
  t = n / 1.875 * 12 / 3
  z = 3 * (floor(t) + smoothstep(0.82, 1, t - floor(t)))
  ```
  where `value_noise` is smoothly interpolated lattice noise in [0, 1) with
  the integer hash of Landscaper `src/main.rs` `value_noise`. 3 m terraces
  whose edges are cliffs where the noise is steep. Set with `LS_RUGGED=1`.

For every variant:
- ground is walkable where its slope stays under the limit (a rise per
  sample step equivalent to a face normal z of 0.64, about 50°) and it is
  not blocked; how samples become walkable and non-walkable faces differs
  by revision (Landscaper `src/main.rs`, `walkmesh` / `walkmesh_raw`).
  Walkable faces get `surfacemat.2da` row 3, others row 7;
- each tile's `Tile_Height` is the mean ground height over an 11 × 11 grid
  at 1 m spacing, divided by the `.set` `Transition` (5 m) and rounded;
  walkmesh z is written relative to `Tile_Height × 5`;
- every tile is unique (its own model and `.wok`) and placed with
  `Tile_Orientation` 0;
- each tile's `PathNode` and `Orientation` are chosen from its walkmesh by
  Landscaper's `src/pathnode.rs` (SET-NODE-031);
- the walkmesh is an RTIN simplification of a sample grid, by revision:

| Corpus | Landscaper revision | Walkmesh |
|---|---|---|
| v1 | cd4b0e1 (recorded 0b689ce to cd4b0e1; generator unchanged between) | RTIN over 9 × 9 samples a tile, 0.25 m height error; each tile on its own |
| v2 | 72205ca | as v1, plus shared tile borders, edge walkability reconciled across tiles, pieces under 2 m² pruned, components no layout node owns made non-walkable |
| v3 | 5b72e9a | 17 × 17 samples; as v2, plus a morphological opening, interior holes under 4 m² filled, strict exits, badly landing crossings removed where connectivity allows, unrepresentable crossings made non-walkable |

v1 shows the failures (seam disagreement, T13); v2 and v3 the fixes; the
rugged cases the region-shape failures (T39).

### Pairs

`oracle.rs` `pairs`: points uniform over the area from a `fastrand`
generator seeded with the case's seed, kept only if at least 0.75 m from
every tile border and on solid ground (every 0.5 m sample within 1 m in
one component); pairs closer than 5 m are redrawn. The recorded files hold
the pairs, so an implementation does not need to regenerate them.

## Regenerating an area

```sh
git -C landscaper checkout <revision>          # from the manifest
cd landscaper && cargo build --release
<env> target/release/landscaper generate out/  # e.g. LS_CLIFF=4.0
```

`generate` writes the hak (tile models, `.wok` walkmeshes, the `.set`;
it goes to the game's user `hak/` folder) and the module (the `.are` with each tile's `Tile_ID`, `Tile_Height`,
`Tile_Orientation`). From those an implementation takes each tile's
walkmesh, `PathNode`, `Orientation` and `Tile_Height`. To re-record the
routes on a server, `<env> landscaper oracle 40 <seed>`; it needs the game
and Moonglow's `mg test` to run the module.

Later Landscaper revisions changed the generator. Its notes give
environment switches that restore older behaviour (v1: `LS_OLD_SEAMS=1`;
v2: `LS_SAMPLES=9 LS_NO_OPENING=1 LS_KEEP_HOLES=1`), but whether they
reproduce the corpus areas exactly at later revisions was not checked:
use the pinned revision.

## Checking an implementation

1. For each case, build the area as above and load it into your
   implementation: walkmeshes (SET-TILE-010..033), layouts
   (SET-NODE-001), tile heights (SET-TILE-050).
2. For each route, run the request as the server would for this creature
   (radius 0.4, height 1.0, NPC budgets): the direct line, the tile route,
   the in-tile searches, the fallbacks (spec/route.md, spec/intra.md),
   including where `CreateObject` puts the start (SET-ROUTE-050).
3. Predict `arrived` (and, if you can, `end`), and write the predictions
   in a directory laid out like `routes/`, one list per case in route
   order: `[{"arrived": true, "end": [x, y]}, ...]`.
4. Run:
   ```sh
   python3 conformance/tools/compare.py --predictions <dir> [--verbose]
   ```

An implementation of the spec MUST agree on `arrived` for every route.
Agreement on `end` within 0.5 m is reported but not required: the grid
path's end depends on time slices (SET-ROUTE-014), and the reference
simulator itself agreed within 0.5 m on 519 of the first 520 v1 routes,
the miss being such a case.

The reference implementation, Layonara Landscaper's simulator, agreed on
`arrived` for every route at the time each corpus was recorded
(`landscaper sim-check routes/<corpus>/<case>.json`); the manifest says
where each agreement was recorded.
