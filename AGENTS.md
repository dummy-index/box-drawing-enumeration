# AGENTS Guidance

- Run a full enumeration with:
  ```bash
  python explore.py --rows 4 --cols 8 --tiles jis32.json --max 0
  ```
  (`--max 0` means no limit; omit to get the default single solution.)
- The `--tiles` JSON must contain exactly `rows*cols` entries. If the count mismatches, the script exits with an error.
- For experiments with different board sizes, create a new subdirectory and run the enumeration inside it to keep results isolated.
- Prefer horizontal boards (rows ≤ cols) to match typical usage patterns.
- If `--tiles` is omitted, `explore.py` falls back to a placeholder `DEFAULT_TILES` (32 binary‑sided tiles) and prints a warning. Never rely on this for real results.
- Tile orientation is **fixed**; individual tiles are **not** rotated. Board rotations are handled internally during canonicalisation.
- Canonicalisation steps (hard‑to‑guess):
  1. Apply the 8 dihedral (D4) transforms to the board.
  2. For each transform, verify that every rotated side tuple exists in the tile set.
  3. If valid, also apply the thin↔thick label swap (1↔2).
  4. Keep the lexicographically smallest signature; all others are considered duplicates.
- Blank tiles are identified by IDs starting with `BLANK`. The minimal bounding‑box removal strips empty rows/cols before signature generation.
- To render a solution as ASCII art use:
  ```bash
  python render_solution.py
  ```
  It reads all `solution_*.json` files, verifies border/neighbor consistency, and prints a 3×3 per‑tile canvas.
- To generate an HTML gallery and a text summary run:
  ```bash
  python gallery_generator.py
  ```
  This creates `gallery.html` (interactive) and `solutions_summary.txt` (ASCII list) in the current directory.
- For larger boards (e.g., 9×4, 10×4) you can still use `jis32.json`; the solver now automatically adds the required number of blank tiles (ID `BLANK<n>`, sides `[0,0,0,0]`) to match `rows*cols`. No separate `jis32_with_blank.json` is needed. Adjust `--rows`/`--cols` as desired.
- CP437 exploration (`cp437.json`) uses the same format but the search space (40! permutations) is infeasible without aggressive pruning. The repository notes that a full run took >22 h with no solutions; avoid running it unless you implement custom pruning.
- The `check_json.py` utility simply prints the count and IDs of entries in `jis32.json`; useful for sanity checks.
- All scripts require **Python 3.7+** and have a shebang (`#!/usr/bin/env python3`). Ensure the environment uses the correct interpreter.
