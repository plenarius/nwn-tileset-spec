# Edge tiles (`SET-EDGE`)

The scenery the game client draws outside an area's tiles: a ring of
models five cells deep, chosen from the tileset's `_edge` 2da by the
boundary tiles' corner and edge keys. This is client code
(`CNWCArea::LoadBorder`); all addresses in this file are `nwmain-linux`.

## When

**SET-EDGE-001** The client loads the 2da `<tileset resref>_Edge`. If it
does not load, no edge tiles are drawn at all. *Confirmed: T41.*

**SET-EDGE-002** The client draws edge tiles only when its first client
option is on and the area's border-disabled flag (area +0x10c) is 0.
*Confirmed: T49 (`CNWCArea::LoadArea` 0x70e010).* What the option and the
flag are called in the game is inferred (unknown.md).

## Cells

**SET-EDGE-010** With the area W × H tiles, one model is placed in each
10 × 10 m cell of a ring 5 cells deep: the west strip x = -5..-1 and the
east strip x = W..W+4, each for y = -5..H+4 (which includes the four 5 × 5
corner blocks); the south strip y = -5..-1 and the north strip
y = H..H+4, each for x = 0..W-1. That is 10W + 10H + 100 cells. *Confirmed:
T43.*

**SET-EDGE-011** A strip cell is keyed by the area tile beside it: west
(0, y), east (W-1, y), south (x, 0), north (x, H-1). A corner block is
keyed by the area's corner tile. The key never depends on the depth, so
the same model repeats five deep, and all 25 cells of a corner block show
one model. *Confirmed: T43.*

## Keys

**SET-EDGE-020** A tile's corner c (0 NE, 1 SE, 2 SW, 3 NW) and edge s
(0 N, 1 E, 2 S, 3 W) as seen in the area are read from its `.set` data at
index `(c + o) & 3` and `(s + o) & 3`, o being its `Tile_Orientation`. The
data slots are filled as SET-FILE-020 and SET-FILE-021 say. *Confirmed:
T42, T4, T5.*

**SET-EDGE-021** Each cell's key is (C1, E, C2):

| Cells | C1 | E | C2 |
|---|---|---|---|
| west strip, 0 <= y < H | NW corner of (0, y) | W edge | SW corner |
| SW block (west loop, y < 0) | "" | "" | SW corner of (0, 0) |
| NW block (west loop, y >= H) | NW corner of (0, H-1) | "" | "" |
| east strip, 0 <= y < H | NE corner of (W-1, y) | E edge | SE corner |
| SE block (east loop, y < 0) | SE corner of (W-1, 0) | "" | "" |
| NE block (east loop, y >= H) | "" | "" | NE corner of (W-1, H-1) |
| south strip | SW corner of (x, 0) | S edge | SE corner |
| north strip | NW corner of (x, H-1) | N edge | NE corner |

On the strips C1 is the north end (west, east) or the west end (south,
north). *Confirmed: T44.*

## Matching rows

**SET-EDGE-030** Rows are scanned in file order. A row matches when its
`Edge` equals E and either its (`Corner1`, `Corner2`) equals (C1, C2)
(direct) or (C2, C1) (swapped). For each row direct is tried before
swapped. The first matching row wins. *Confirmed: T45.*

**SET-EDGE-031** Strings are compared whole and case-insensitively, with
no trimming, wildcards or prefixes. A `****` cell is an empty string and
matches only an empty key part. *Confirmed: T45.*

**SET-EDGE-032** When no row matches, the cell gets no model. A writer
MUST provide a row for every boundary edge key and every corner block key
it wants filled; missing rows leave holes. *Confirmed: T46 (the model
string is empty; that an empty model draws nothing is inferred).*

## Rotation and placement

**SET-EDGE-040** The model's rotation is 0 for a direct match and 2 for a
swapped match on the west and east strips (and their corner blocks), 1
and 3 on the south and north strips. *Confirmed: T46.* After a miss the
rotation keeps the previous match's value; it does not matter, as no model
is drawn.

**SET-EDGE-041** A rotation r turns the model exactly as `Tile_Orientation
= r` turns an area tile (the same call, `Scene::SpawnTile` 0x474470, the
same argument, a yaw of r × 90°). *Confirmed: T47.*

**SET-EDGE-042** A writer SHOULD write every row in direct order (Corner1
= C1, Corner2 = C2 of SET-EDGE-021), so the rotation is known: 0 on the
west and east strips, 1 on the south and north. When C1 equals C2 a
swapped match can never happen. With a row `T **** ****`, the NW and SE
blocks match direct (rotation 0) and the SW and NE blocks swapped
(rotation 2). *Confirmed: T45, T46.*

**SET-EDGE-043** With the same row on the west and east strips (rotation
0 on both), a model's local +x points outward on the east and inward on
the west; likewise on the north and south with rotation 1. A model shared
between opposite strips SHOULD therefore be symmetric across its local y
axis. *Confirmed: T46, T47 (follows from the rotation values; that stock
edge models are symmetric is inferred).*

**SET-EDGE-050** A cell's model is placed at `(x × 10 + 5, y × 10 + 5,
Transition × (Tile_Height + Height))`: the cell centre, with
`Tile_Height` of the keying tile and `Height` from the matched row (0 on a
miss). Height is in transition steps, added as an integer. The model's
origin is the cell centre, as for an area tile. *Confirmed: T48.*

## Models

**SET-EDGE-060** Edge models need no walkmesh: the client draws an edge
model that has no `.wok`, and a writer MAY ship edge models without one.
*Confirmed: T50.*

Name lengths (the 2da name `<tileset>_edge`, model resrefs) are in
[unknown.md](unknown.md).
