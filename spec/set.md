# The .set file (`SET-FILE`)

What the engine requires of a tileset's `.set` file, and what the keys this
repository covers mean. The `.set` holds much more (terrain and crosser
types, rules, groups, lights, doors, sounds); those keys are described for
builders on [nwn.wiki](https://nwn.wiki) and are only covered here where
they reach pathing or edge tiles.

## Text

**SET-FILE-001** A writer MUST end every line of a `.set` with CRLF. The
server crashes loading a `.set` with LF-only line ends. *Confirmed: T1 (in
game).*

**SET-FILE-002** The file is INI-like: `[SECTION]` lines, then `Key=Value`
lines. A tileset the server accepted is shown below. *Confirmed: in game
(Landscaper's generated tilesets, every corpus area); the parser itself
(`CResSET::GetSectionEntryValue`, `nwserver-linux` 0x43ec40) was not read
for this repository.*

```ini
[GENERAL]
Name=LSP01
Type=SET
Version=V1.0
Interior=0
HasHeightTransition=1
EnvMap=ttr01__ref01
Transition=5
DisplayName=-1
UnlocalizedName=Landscaper Spike
Border=Ground
Default=Ground
Floor=Ground

[GRASS]
Grass=0

[TERRAIN TYPES]
Count=1

[TERRAIN0]
Name=Ground
StrRef=63635

[CROSSER TYPES]
Count=0

[PRIMARY RULES]
Count=0

[SECONDARY RULES]
Count=0

[TILES]
Count=16

[TILE0]
Model=lsp01_x0y0
WalkMesh=msb01
TopLeft=Ground
TopLeftHeight=0
TopRight=Ground
TopRightHeight=0
BottomLeft=Ground
BottomLeftHeight=0
BottomRight=Ground
BottomRightHeight=0
Top=
Right=
Bottom=
Left=
MainLight1=1
MainLight2=1
SourceLight1=0
SourceLight2=0
AnimLoop1=0
AnimLoop2=0
AnimLoop3=0
Doors=0
Sounds=0
PathNode=B
Orientation=90
VisibilityNode=A
VisibilityOrientation=0
ImageMap2D=mitr01_A01

...

[GROUPS]
Count=0
```

(This is the file Landscaper wrote for the corpus areas, revision
cd4b0e1. `lsp01_x0y0` is a generated tile model; `ttr01__ref01` and
`mitr01_A01` are a stock environment map and minimap, named only. Every tile
has its own model, its own walkmesh of the same resref, and its own
`PathNode` and `Orientation`; the area places each tile once, unrotated.)

## Path-node letter and orientation

**SET-FILE-010** A tile's `Orientation` is in degrees. A writer MUST write
0, 90, 180 or 270. The server converts it with
`CNWTileSurfaceMesh::ConvertToTileOrientation` (`nwserver-linux` 0x441770):

| Orientation | Path-node orientation |
|---|---|
| 0, 360, -360 | 0 |
| 90, -270 | 1 |
| 180, -180 | 2 |
| 270, -90 | 3 |
| anything else | 4 (invalid) |

With 4, `GetTilePathNode` returns no layout and the server crashes when it
paths on the tile. 1, 2 and 3 are "anything else". *Confirmed: T2 (code;
in game: 1, 2, 3 crash).*

**SET-FILE-011** `Orientation` turns the tile's **path-node layout**
only. It is independent of the area's `Tile_Orientation`, which places the
tile (SET-TILE-003): the layout is used in the walkmesh's canonical frame,
pre-rotated by `Orientation`, and the area's rotation then applies to
both. *Confirmed: T2, T3, T11 (code).*

**SET-FILE-012** `PathNode` is one letter. It and the converted
orientation select the tile's layout from the engine's built-in table
([tables/pathnodes.json](../tables/pathnodes.json); SET-NODE-001). A
writer MUST use a letter that has a layout: `A`-`Z` except `P` and `T`, or
`a`-`x`. *Confirmed: T3, T15 (gdb: `P` and `T` give 0 nodes and 0 exits).*
What the server does with `P`, `T` or another character is not known
(unknown.md).

**SET-FILE-013** A writer SHOULD choose each tile's letter and orientation
from its walkmesh (SET-NODE-031). The engine does not check that a layout
fits a walkmesh: the tile route uses the layout alone. *Confirmed: T16,
T17.*

## Corners and edges

These keys key the client's edge tiles (edge.md); they are read by the
client's `CNWTileSet::LoadTileSet` (`nwmain-linux` 0x5e1190).

**SET-FILE-020** The corner keys fill the tile's corner slots 0-3 and the
edge keys its edge slots 0-3, clockwise from north:

| Key | Slot |
|---|---|
| `TopRight` (with `TopRightHeight`) | corner 0 (NE) |
| `BottomRight` (with `BottomRightHeight`) | corner 1 (SE) |
| `BottomLeft` (with `BottomLeftHeight`) | corner 2 (SW) |
| `TopLeft` (with `TopLeftHeight`) | corner 3 (NW) |
| `Top` | edge 0 (N) |
| `Right` | edge 1 (E) |
| `Bottom` | edge 2 (S) |
| `Left` | edge 3 (W) |

Corner i follows edge i clockwise. *Confirmed: T4 (asm).* Also in
[tables/set_slots.yaml](../tables/set_slots.yaml).

**SET-FILE-021** A corner whose `<Corner>Height` is non-zero is stored as
its terrain name followed by one `+` (`Grass+`), whatever the height (1,
2, -1, …). Height 0 stores the name as it is. A reader that matches corner
names as the client does MUST apply this. *Confirmed: T5 (asm).*

**SET-FILE-022** An empty edge key (`Top=`) stores an empty string. A
tile with no crosser on a side has an empty edge there. *Confirmed: T44,
T45 (an empty edge part matches only `****`).*

## Heights

**SET-FILE-030** `Transition` is the tileset's height step in metres. The
client places edge tiles at `Transition × (Tile_Height + Height)`
(SET-EDGE-050). *Confirmed: T48 (`CNWTileSet::GetHeightTransition`,
tileset +0x44, `nwmain-linux`).* That the server places a tile's walkmesh
at `Tile_Height × Transition` is inferred (SET-TILE-050, unknown.md).
