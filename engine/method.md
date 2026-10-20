# How the evidence was gathered

So anyone with the game can repeat it.

## Reading the code

- Both binaries are unstripped, so functions have their C++ names. Build
  and checksums are in [README.md](README.md).
- `nm -C` and `objdump -d --no-show-raw-insn -C` give addresses and
  disassembly. Addresses in this repository are objdump's.
- Ghidra 12.1.4, headless, decompiled the functions. The first server
  analysis (2026-10-19) used the default analysers, which mark `memcpy`,
  `free`, `operator new[]` and others as non-returning and so truncate any
  function calling them; the later analyses ("v2", 2026-10-20) turn the
  "Non-Returning Functions - Discovered" analyser off. Wherever a
  decompile was garbled (mislabelled locals, wrong signatures, dropped
  return values), the finding was re-derived from the disassembly; the
  findings say which.
- The decompiles are shared, not copied here:
  - server, pathfinding: `~/dev/nwn/nwserver-analysis/decompiled/pathfinding/`
    (`raw/` from the first analysis, `clean/` hand-cleaned, `spec-intertile/`
    and `spec-intratile/` made for the research notes, `asm/` objdump
    listings);
  - client, edge tiles: `~/dev/nwn/nwmain-analysis/decompiled/edge-tiles/`
    (v2 analysis; `notes.md` lists each function with both address forms).
- The research notes these findings were condensed from are Layonara
  Landscaper's `research/SPEC_INTERTILE.md`, `SPEC_INTRATILE.md`,
  `SPEC_EDGE.md` and `FINDINGS.md`. `SPEC_INTERTILE.md` gives Ghidra
  addresses except where marked `nm`; the other two give objdump
  addresses. All were converted and checked against `nm` for this
  repository.

## gdb on the running server

Landscaper's `research/*_gdb.py` scripts run `nwserver-linux` under gdb:

- `dump_pathnodes_gdb.py` calls
  `CNWTileSetManager::ComputePathNodeInformation` (0x3f3ea0) for every
  letter `A`-`Z`, `a`-`x` and orientation 0-3 and writes the result
  ([tables/pathnodes.json](../tables/pathnodes.json));
- `sim_gdb.py` logs the request fields of a scripted move and the
  arguments and results of the planner's calls (radius, height, budget,
  coarse flag, call counts);
- `trace_*_gdb.py` trace tiles, regions, the tile route and waypoints.

## Recording routes

Layonara Landscaper's `oracle` command generates an area, writes a test
script that walks one creature per route, runs the module on a local
server and reads the positions back from the log. The setup is in
[conformance/README.md](../conformance/README.md). Two things matter:

- A creature in an area with no player runs at a low AI level, and its
  scripted moves then only walk straight. The script sets
  `SetAILevel(o, AI_LEVEL_HIGH)` on each creature.
- Each creature is a cutscene ghost, so the creatures of other routes do
  not block it.

## The simulator

Landscaper's `src/sim/` ports `CNWSModule::PlotPathInArea` for NPCs from
the findings, and runs the same routes offline. A finding marked
"confirmed (simulator)" was read in code and is part of a port that agrees
with the server on whether the creature arrived for every recorded route.
That checks the behaviour as a whole; it does not check every branch.
