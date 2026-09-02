#!/usr/bin/env python3
"""
Tile-placement enumerator for an R x C grid using a given multiset of tiles.
This version models per-side connector TYPES (0 = none, 1 = thin, 2 = thick).

Features:
- Backtracking placement with adjacency checks
- Rotation of tiles by 90deg increments (side-level rotation)
- Canonicalization under D4 (rot/reflect) and under label-permutation (swap thin/thick)
- Pluggable tile set (JSON with 'sides': [N,E,S,W])

Note: Full enumeration is expensive; use --max to limit unique solutions.
"""

import argparse
import json
import sys
from collections import namedtuple
from copy import deepcopy

Tile = namedtuple('Tile', ['id', 'sides'])  # sides: tuple/list of 4 ints (N,E,S,W)

# Utility functions for side-tuples
def rotate_sides_cw(sides):
    """Rotate sides (N,E,S,W) 90deg clockwise -> new (N,E,S,W)"""
    n,e,s,w = sides
    # After CW rotation: new N = W, new E = N, new S = E, new W = S
    return (w, n, e, s)

def rotate_sides_k(sides, k):
    m = sides
    for _ in range(k % 4):
        m = rotate_sides_cw(m)
    return m

def flip_horizontal(sides):
    n,e,s,w = sides
    # horizontal mirror: swap E<->W
    return (n, w, s, e)

def flip_vertical(sides):
    n,e,s,w = sides
    # vertical mirror: swap N<->S
    return (s, e, n, w)

# diagonal transpose implemented as rotate90 then flip_horizontal (matches earlier derivation)
def transpose_main_diag(sides):
    return flip_horizontal(rotate_sides_cw(sides))

# anti-diagonal: rotate270 then flip_horizontal
def transpose_anti_diag(sides):
    return flip_horizontal(rotate_sides_k(sides, 3))


def sides_to_signature(sides):
    return ','.join(str(int(x)) for x in sides)

# Board transforms for canonicalization
# Implement the 8 dihedral symmetries for the rectangular grid.

def transform_board(board, rows, cols, transform):
    """Apply a transform to the board (list of rows of (id,sides)).
    Returns (new_board, new_rows, new_cols)
    """
    if transform == 'identity':
        return deepcopy(board), rows, cols
    if transform == 'rot90':
        new_rows, new_cols = cols, rows
        out = [[None for _ in range(new_cols)] for _ in range(new_rows)]
        for r in range(rows):
            for c in range(cols):
                tid, sides = board[r][c]
                nr, nc = c, rows - 1 - r
                out[nr][nc] = (tid, rotate_sides_k(sides, 1))
        return out, new_rows, new_cols
    if transform == 'rot180':
        new_rows, new_cols = rows, cols
        out = [[None for _ in range(new_cols)] for _ in range(new_rows)]
        for r in range(rows):
            for c in range(cols):
                tid, sides = board[r][c]
                nr, nc = rows - 1 - r, cols - 1 - c
                out[nr][nc] = (tid, rotate_sides_k(sides, 2))
        return out, new_rows, new_cols
    if transform == 'rot270':
        new_rows, new_cols = cols, rows
        out = [[None for _ in range(new_cols)] for _ in range(new_rows)]
        for r in range(rows):
            for c in range(cols):
                tid, sides = board[r][c]
                nr, nc = cols - 1 - c, r
                out[nr][nc] = (tid, rotate_sides_k(sides, 3))
        return out, new_rows, new_cols
    if transform == 'fliph':
        # horizontal flip
        out = [[None for _ in range(cols)] for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                tid, sides = board[r][c]
                nr, nc = r, cols - 1 - c
                out[nr][nc] = (tid, flip_horizontal(sides))
        return out, rows, cols
    if transform == 'flipv':
        out = [[None for _ in range(cols)] for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                tid, sides = board[r][c]
                nr, nc = rows - 1 - r, c
                out[nr][nc] = (tid, flip_vertical(sides))
        return out, rows, cols
    if transform == 'diag':
        new_rows, new_cols = cols, rows
        out = [[None for _ in range(new_cols)] for _ in range(new_rows)]
        for r in range(rows):
            for c in range(cols):
                tid, sides = board[r][c]
                nr, nc = c, r
                out[nr][nc] = (tid, transpose_main_diag(sides))
        return out, new_rows, new_cols
    if transform == 'adiag':
        new_rows, new_cols = cols, rows
        out = [[None for _ in range(new_cols)] for _ in range(new_rows)]
        for r in range(rows):
            for c in range(cols):
                tid, sides = board[r][c]
                nr, nc = cols - 1 - c, rows - 1 - r
                out[nr][nc] = (tid, transpose_anti_diag(sides))
        return out, new_rows, new_cols
    raise ValueError(transform)


def board_signature(board, rows, cols):
    """Create a compact string signature of board: concatenated "id:N,E,S,W" row-major"""
    parts = []
    for r in range(rows):
        for c in range(cols):
            tid, sides = board[r][c]
            parts.append(f"{tid}:{sides_to_signature(sides)}")
    return '|'.join(parts)


def swap_types_on_board(board, rows, cols, mapping):
    """Return a new board where side values are remapped according to mapping dict."""
    out = [[None for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            tid, sides = board[r][c]
            new_sides = tuple(mapping.get(x, x) for x in sides)
            out[r][c] = (tid, new_sides)
    return out


def canonical_signature(board, rows, cols, sides_map):
    """DEPRECATED: Do not use. Use Solver.canonical_signature_checked instead."""
    raise NotImplementedError("Use Solver.canonical_signature_checked()")


# Backtracking solver
class Solver:
    def __init__(self, rows, cols, tiles):
        assert rows * cols == len(tiles), "Grid must match number of tiles"
        self.rows = rows
        self.cols = cols
        # tiles: list of Tile (each tile is fixed, no rotation)
        self.tiles = tiles
        # build sides->id mapping; if a tile's sides appears multiple times, keep first
        self.sides_to_id = {}
        for t in tiles:
            s = tuple(t.sides)
            if s not in self.sides_to_id:
                self.sides_to_id[s] = t.id
        # Group tiles by sides; multiple tiles with same sides → try in order, break after placing one
        self.sides_to_tile_group = {}
        for t in tiles:
            s = tuple(t.sides)
            if s not in self.sides_to_tile_group:
                self.sides_to_tile_group[s] = []
            self.sides_to_tile_group[s].append(t)
        
        self.used = {t.id: 0 for t in tiles}
        self.board = [[None for _ in range(cols)] for _ in range(rows)]
        self.unique_sigs = set()
        self.solutions = []
        self.nodes_visited = 0

    def neighbors_ok(self, r, c, sides):
        """Check adjacency compatibility and strict border (no dangling on edges).
        Tile is fixed; neighbors_ok checks if sides match adjacent tile sides.
        """
        self.nodes_visited += 1
        n,e,s,w = sides
        # Border checks: edges must have no outgoing connection
        if r == 0 and n != 0:
            return False
        if c == 0 and w != 0:
            return False
        if r == self.rows - 1 and s != 0:
            return False
        if c == self.cols - 1 and e != 0:
            return False
        # Top neighbor
        if r > 0 and self.board[r-1][c] is not None:
            _, up_sides = self.board[r-1][c]
            up_s = up_sides[2]
            if up_s != n:
                return False
        # Left neighbor
        if c > 0 and self.board[r][c-1] is not None:
            _, left_sides = self.board[r][c-1]
            left_e = left_sides[1]
            if left_e != w:
                return False
        return True

    def place_next(self, idx=0, max_solutions=None):
        if idx == self.rows * self.cols:
            # complete board -> canonicalize with board D4 transforms
            # Check if canonicalized board can be represented with available tiles
            sig = self.canonical_signature_checked()
            if sig is not None and sig not in self.unique_sigs:
                self.unique_sigs.add(sig)
                self.solutions.append(deepcopy(self.board))
                print(f"Found unique solution #{len(self.solutions)} (nodes {self.nodes_visited})")
                if max_solutions and len(self.solutions) >= max_solutions:
                    return True
            return False
        r = idx // self.cols
        c = idx % self.cols
        
        # For each distinct sides value, try tiles in order
        # If a sides value has multiple tile IDs, use only the first unused one, then break
        tried_sides = set()
        for t in self.tiles:
            sides = tuple(t.sides)
            
            # If we've already tried this sides value, skip
            if sides in tried_sides:
                continue
            
            # If this tile is used, skip
            if self.used[t.id]:
                continue
            
            tried_sides.add(sides)
            
            if not self.neighbors_ok(r, c, sides):
                continue
            
            # place
            self.board[r][c] = (t.id, sides)
            self.used[t.id] += 1
            stop = self.place_next(idx+1, max_solutions)
            # unplace
            self.used[t.id] -= 1
            self.board[r][c] = None
            
            if stop:
                return True
            
            # If this sides value has multiple tile IDs (e.g., BLANK1, BLANK2),
            # don't try other tile IDs with the same sides
        
        return False

    def canonical_signature_checked(self):
        """Apply D4 transforms to board and check each result can be represented with available tiles.
        Only return signature if valid representation exists; else return None.
        Also apply minimal bounding box to remove translational variants.
        """
        transforms = ['identity','rot90','rot180','rot270','fliph','flipv','diag','adiag']
        valid_sigs = []
        for t in transforms:
            try:
                tb, r, c = transform_board(self.board, self.rows, self.cols, t)
                # check if each cell's rotated sides has a corresponding tile
                valid = True
                for i in range(r):
                    for j in range(c):
                        _, sides = tb[i][j]
                        if sides not in self.sides_to_id:
                            valid = False
                            break
                    if not valid:
                        break
                if valid:
                    # Compute minimal bounding box
                    tb_min, r_min, c_min = self.minimal_bounding_box(tb, r, c)
                    sig = self.board_signature_from_board(tb_min, r_min, c_min)
                    valid_sigs.append(sig)
                    # swapped labels: 1<->2
                    swapped = swap_types_on_board(tb_min, r_min, c_min, {1:2, 2:1})
                    valid_sigs.append(self.board_signature_from_board(swapped, r_min, c_min))
            except Exception:
                continue
        if not valid_sigs:
            return None
        return min(valid_sigs)
    
    def minimal_bounding_box(self, board, rows, cols):
        """Extract minimal bounding box by removing empty (BLANK-only) rows/cols from edges.
        Returns (trimmed_board, new_rows, new_cols)
        """
        # Find rows with at least one non-BLANK
        min_row = rows
        max_row = -1
        for r in range(rows):
            for c in range(cols):
                tid, sides = board[r][c]
                if tid != 'BLANK1' and tid != 'BLANK2' and tid != 'BLANK3' and tid != 'BLANK4' and tid != 'BLANK5' and tid != 'BLANK6' and tid != 'BLANK7' and tid != 'BLANK8':
                    min_row = min(min_row, r)
                    max_row = max(max_row, r)
                    break
        
        # Find columns with at least one non-BLANK
        min_col = cols
        max_col = -1
        for c in range(cols):
            for r in range(rows):
                tid, sides = board[r][c]
                if tid != 'BLANK1' and tid != 'BLANK2' and tid != 'BLANK3' and tid != 'BLANK4' and tid != 'BLANK5' and tid != 'BLANK6' and tid != 'BLANK7' and tid != 'BLANK8':
                    min_col = min(min_col, c)
                    max_col = max(max_col, c)
                    break
        
        # If all BLANKs, return a single BLANK cell
        if min_row > max_row or min_col > max_col:
            blank_tile = (board[0][0])
            return [[blank_tile]], 1, 1
        
        # Extract bounding box
        new_rows = max_row - min_row + 1
        new_cols = max_col - min_col + 1
        trimmed = [[board[min_row + r][min_col + c] for c in range(new_cols)] for r in range(new_rows)]
        return trimmed, new_rows, new_cols

    def board_signature_from_board(self, board, rows, cols):
        """Create signature from board using sides_to_id mapping."""
        parts = []
        for r in range(rows):
            for c in range(cols):
                _, sides = board[r][c]
                tid = self.sides_to_id.get(sides)
                if tid is None:
                    tid = 'UNKNOWN:' + sides_to_signature(sides)
                parts.append(tid)
        return '|'.join(parts)


# DEFAULT_TILES: placeholder example with 32 simple tiles (for testing only)
DEFAULT_TILES = [Tile(f"t{i}", ((i>>0)&1, (i>>1)&1, (i>>2)&1, (i>>3)&1)) for i in range(32)]


def load_tiles_from_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    tiles = []
    for entry in data:
        tid = entry.get('id')
        if 'sides' in entry:
            sides = tuple(int(x) for x in entry['sides'])
            if len(sides) != 4:
                raise ValueError('sides must have 4 entries')
        elif 'mask' in entry:
            # legacy: mask bitfield -> sides presence (0/1)
            m = int(entry['mask'])
            sides = (1 if (m & 8) else 0, 1 if (m & 4) else 0, 1 if (m & 2) else 0, 1 if (m & 1) else 0)
        else:
            raise ValueError('tile entry must have sides or mask')
        tiles.append(Tile(tid, sides))
    return tiles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', type=int, default=4)
    ap.add_argument('--cols', type=int, default=8)
    ap.add_argument('--tiles', type=str, default=None, help='JSON file with tiles: [{"id":"...","sides":[N,E,S,W]}, ...]')
    ap.add_argument('--max', type=int, default=1, help='Stop after this many unique solutions (0 = all)')
    args = ap.parse_args()

    if args.tiles:
        tiles = load_tiles_from_json(args.tiles)
    else:
        tiles = DEFAULT_TILES
        print("Warning: using DEFAULT_TILES placeholder. Replace with actual tile set using --tiles file.")

    if len(tiles) != args.rows * args.cols:
        print(f"Tile count ({len(tiles)}) != grid size ({args.rows}x{args.cols}={args.rows*args.cols}). Exiting.")
        sys.exit(1)

    solver = Solver(args.rows, args.cols, tiles)
    solver.place_next(0, max_solutions=(args.max if args.max>0 else None))
    print(f"Done. Unique solutions found: {len(solver.solutions)}")

    # Optionally dump solutions to files
    for i, b in enumerate(solver.solutions,1):
        fname = f'solution_{i}.json'
        out = []
        for r in range(args.rows):
            row = []
            for c in range(args.cols):
                tid, sides = b[r][c]
                row.append({'id': tid, 'sides': list(sides)})
            out.append(row)
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump({'rows': args.rows, 'cols': args.cols, 'board': out}, f, ensure_ascii=False, indent=2)
        print(f"Wrote {fname}")


if __name__ == '__main__':
    main()
