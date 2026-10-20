# Engine

What the game's code does with tilesets, tiles and area pathing, finding by
finding, written without reference to any one tool. The spec's rules cite
these.

- **Build:** NWN:EE 89.8193.37-17, Linux, git commit 26c6e573 (the
  install's `bin/linux-x86/build.txt`: `26c6e57364a45246e3b58e4f2c49366df72d15db`,
  built Mon Oct 6 2025).
- **Binaries** (both unstripped x86-64 PIE, from the Steam install's
  `bin/linux-x86/`):

  | Binary | sha256 | Used for |
  |---|---|---|
  | `nwserver-linux` | `d6d952826b671fc62c376dca912e87f1aa45d4aa81c620e912ceb4d8e051111d` | the server: `.set` loading, walkmeshes, path nodes, pathfinding |
  | `nwmain-linux` | `6d19c39bc646af5ddbc333ff31797a4acd9019506bcb45ef1b93b1bd5925e700` | the client: edge tiles, the client's `.set` parser |

  `nwmain-linux` is the same file nwn-mdl-spec was read on.
- **Addresses** are objdump/nm addresses (file virtual addresses), and
  each one says its binary unless the section says it for all. Ghidra loads
  these PIEs at 0x100000, so its addresses are 0x100000 higher
  (`CNWSArea::PlotPath` is 0x649b70 here, 0x749b70 in Ghidra). Every
  function address here was checked against `nm -C` of its binary.
- **Status:** **confirmed** (read in code and checked against the
  disassembly, under gdb, or by the simulator agreeing with recorded server
  runs; or shown by a server run or in game), **inferred** (follows from
  code or data, not shown), **untested**.
- **Numbering:** T1 onwards, this repository's own.

| File | What |
|---|---|
| [behaviour.md](behaviour.md) | The findings |
| [method.md](method.md) | How the code was read and the routes recorded, so others can repeat it |

Some findings cite files that are not in this repository: the shared
decompiles (cited by path, see method.md), NWN Landscaper's sources
and commits, and the game's own tilesets (by resref). They are named so the
observation can be repeated; decompiles and game files are never copied
here.
