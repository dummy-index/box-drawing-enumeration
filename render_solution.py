import json
import glob
import os

# rendering mapping
H = {0: ' ', 1: '-', 2: '='}
V = {0: ' ', 1: '|', 2: '#'}

# try to load tile id->char mapping from known json files
def load_tile_char_map():
    for fname in ['jis32.json','jis8.json','jis32_template.json']:
        if os.path.exists(fname):
            try:
                with open(fname,'r',encoding='utf-8') as f:
                    data = json.load(f)
                return {e.get('id'): e.get('char', e.get('id')[-1]) for e in data}
            except Exception:
                continue
    return {}

TILE_CHAR_MAP = load_tile_char_map()

def verify(board, rows, cols):
    issues = []
    for r in range(rows):
        for c in range(cols):
            tid, sides = board[r][c]
            n,e,s,w = sides
            # border
            if r==0 and n!=0:
                issues.append((r,c,'north border nonzero',sides))
            if r==rows-1 and s!=0:
                issues.append((r,c,'south border nonzero',sides))
            if c==0 and w!=0:
                issues.append((r,c,'west border nonzero',sides))
            if c==cols-1 and e!=0:
                issues.append((r,c,'east border nonzero',sides))
            # neighbors
            if r+1<rows:
                _, nb = board[r+1][c]
                if nb[0] != s:
                    issues.append((r,c,'south mismatch',sides, 'nbr', nb))
            if c+1<cols:
                _, nb = board[r][c+1]
                if nb[3] != e:
                    issues.append((r,c,'east mismatch',sides, 'nbr', nb))
    return issues


def render(board, rows, cols):
    tile_h = 3
    tile_w = 3
    out_rows = rows * tile_h
    out_cols = cols * tile_w
    canvas = [[' ' for _ in range(out_cols)] for _ in range(out_rows)]
    for r in range(rows):
        for c in range(cols):
            tid, sides = board[r][c]
            n,e,s,w = sides
            base_r = r * tile_h
            base_c = c * tile_w
            # center: prefer actual character if available, else last char of id
            center_char = TILE_CHAR_MAP.get(tid, tid[-1])
            canvas[base_r+1][base_c+1] = center_char
            # top middle
            canvas[base_r+0][base_c+1] = H.get(n,' ')
            # bottom middle
            canvas[base_r+2][base_c+1] = H.get(s,' ')
            # left middle
            canvas[base_r+1][base_c+0] = V.get(w,' ')
            # right middle
            canvas[base_r+1][base_c+2] = V.get(e,' ')
    return '\n'.join(''.join(row) for row in canvas)


def process_file(path):
    with open(path,'r',encoding='utf-8') as f:
        data = json.load(f)
    rows = data['rows']
    cols = data['cols']
    board = [ [ (cell['id'], tuple(cell['sides'])) for cell in row ] for row in data['board'] ]
    issues = verify(board, rows, cols)
    print('File:', path)
    if not issues:
        print('Verified: no issues')
    else:
        print('Issues found:', len(issues))
        for it in issues[:10]:
            print(' ', it)
    print('ASCII render:\n')
    print(render(board, rows, cols))
    print('\n' + ('-'*60) + '\n')

if __name__ == '__main__':
    files = glob.glob('solution_*.json')
    files.sort()
    for p in files:
        process_file(p)
