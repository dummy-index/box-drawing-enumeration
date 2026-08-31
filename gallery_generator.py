import json
import glob
import os

def generate_gallery_html():
    """Generate HTML gallery for all solutions, ordering single-connected first."""
    solutions = sorted(glob.glob('solution_*.json'))

    def is_single_connected(board, rows, cols):
        # build adjacency based on 接続成立: non-zero and equal on touching sides
        n_cells = rows * cols
        adj = [[] for _ in range(n_cells)]
        def idx(r,c): return r*cols + c
        for r in range(rows):
            for c in range(cols):
                sides = tuple(board[r][c]['sides'])
                i = idx(r,c)
                # down
                if r+1 < rows:
                    nb = tuple(board[r+1][c]['sides'])
                    if sides[2] != 0 and sides[2] == nb[0]:
                        adj[i].append(idx(r+1,c)); adj[idx(r+1,c)].append(i)
                # right
                if c+1 < cols:
                    nb = tuple(board[r][c+1]['sides'])
                    if sides[1] != 0 and sides[1] == nb[3]:
                        adj[i].append(idx(r,c+1)); adj[idx(r,c+1)].append(i)
        # BFS
        from collections import deque
        q = deque([0])
        vis = [False]*n_cells
        vis[0] = True
        cnt = 1
        while q:
            u = q.popleft()
            for v in adj[u]:
                if not vis[v]:
                    vis[v]=True; q.append(v); cnt+=1
        return cnt == n_cells

    connected = []
    not_connected = []
    for path in solutions:
        data = json.load(open(path,'r',encoding='utf-8'))
        if is_single_connected(data['board'], data['rows'], data['cols']):
            connected.append(path)
        else:
            not_connected.append(path)

    ordered = connected + not_connected

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JIS X 0208 罫線素片配置ギャラリー</title>
    <style>
        body {{ font-family: 'Courier New', monospace; margin: 20px; background-color: #f5f5f5; }}
        h1 {{ text-align: center; color: #333; }}
        .info {{ text-align: center; color: #666; margin-bottom: 10px; }}
        .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin: 20px 0; }}
        .solution-box {{ background: white; border: 1px solid #ddd; border-radius: 8px; padding: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .solution-title {{ font-weight: bold; margin-bottom: 8px; color: #333; }}
        .tile-grid {{ display: inline-block; border-collapse: collapse; border: 2px solid #333; font-size: 18px; line-height: 1.2; }}
        .tile-grid td {{ width: 30px; height: 30px; text-align: center; vertical-align: middle; border: 1px solid #ccc; padding: 0; }}
        .tile-thin {{ color: #000; }}
        .tile-heavy {{ color: #000; font-weight:700; }}
        .group-title {{ margin-top: 20px; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>JIS X 0208 罫線素片 32 字 × 8×4 盤面</h1>
    <div class="info">
        <p>単結合な解（上）→ 単結合でない解（下）</p>
        <p>合計 {len(ordered)} 解（単結合: {len(connected)}, 非単結合: {len(not_connected)}）</p>
    </div>
    <div class="gallery">
"""

    # render ordered
    for i, path in enumerate(ordered, 1):
        data = json.load(open(path,'r',encoding='utf-8'))
        rows = data['rows']; cols = data['cols']; board = data['board']
        # styling map
        type_map = { board[r][c]['id']: max(board[r][c]['sides']) for r in range(rows) for c in range(cols)}
        table_html = '<table class="tile-grid">\n'
        for r in range(rows):
            table_html += '  <tr>\n'
            for c in range(cols):
                tile = board[r][c]
                tid = tile['id']
                ch = '?'
                if tid.startswith('U'):
                    try:
                        ch = chr(int(tid[1:],16))
                    except:
                        ch = '?'
                tile_type = type_map.get(tid,0)
                cls = 'tile-heavy' if tile_type==2 else 'tile-thin'
                table_html += f'    <td class="{cls}">{ch}</td>\n'
            table_html += '  </tr>\n'
        table_html += '</table>'
        # determine group label
        group = '単結合' if path in connected else '非単結合'
        html += f"    <div class=\"solution-box\">\n        <div class=\"solution-title\">解 #{i} ({group})</div>\n        {table_html}\n    </div>\n"

    html += """    </div>
</body>
</html>
"""

    with open('gallery.html','w',encoding='utf-8') as f:
        f.write(html)
    print(f"Generated gallery.html with {len(ordered)} solutions ({len(connected)} connected, {len(not_connected)} not)")


def generate_text_summary():
    """Generate text summary, ordered by connectivity."""
    solutions = sorted(glob.glob('solution_*.json'))

    def is_single_connected(board, rows, cols):
        n_cells = rows*cols
        adj = [[] for _ in range(n_cells)]
        def idx(r,c): return r*cols + c
        for r in range(rows):
            for c in range(cols):
                s = tuple(board[r][c]['sides'])
                i = idx(r,c)
                if r+1<rows:
                    nb = tuple(board[r+1][c]['sides'])
                    if s[2]!=0 and s[2]==nb[0]:
                        adj[i].append(idx(r+1,c)); adj[idx(r+1,c)].append(i)
                if c+1<cols:
                    nb = tuple(board[r][c+1]['sides'])
                    if s[1]!=0 and s[1]==nb[3]:
                        adj[i].append(idx(r,c+1)); adj[idx(r,c+1)].append(i)
        from collections import deque
        q=deque([0]); vis=[False]*n_cells; vis[0]=True; cnt=1
        while q:
            u=q.popleft()
            for v in adj[u]:
                if not vis[v]: vis[v]=True; q.append(v); cnt+=1
        return cnt==n_cells

    connected=[]; not_connected=[]
    for path in solutions:
        data=json.load(open(path,'r',encoding='utf-8'))
        if is_single_connected(data['board'], data['rows'], data['cols']):
            connected.append(path)
        else:
            not_connected.append(path)

    ordered = connected + not_connected

    with open('solutions_summary.txt','w',encoding='utf-8') as f:
        f.write("JIS X 0208 罫線素片 32字 × 8×4 盤面\n")
        f.write("単結合配置の全代表解（回転・反転・色置換を同一視）\n")
        f.write("="*60 + "\n\n")
        f.write(f"全解数: {len(ordered)} (単結合: {len(connected)}, 非単結合: {len(not_connected)})\n\n")
        for idx, path in enumerate(ordered,1):
            data=json.load(open(path,'r',encoding='utf-8'))
            rows=data['rows']; cols=data['cols']; board=data['board']
            group = '単結合' if path in connected else '非単結合'
            f.write(f"--- 解 #{idx} ({group}) ---\n")
            for r in range(rows):
                for c in range(cols):
                    tid = board[r][c]['id']
                    ch='?'
                    if tid.startswith('U'):
                        try: ch = chr(int(tid[1:],16))
                        except: ch='?'
                    f.write(ch)
                f.write('\n')
            f.write('\n')
    print(f"Generated solutions_summary.txt with {len(ordered)} solutions")


if __name__ == '__main__':
    generate_gallery_html()
    generate_text_summary()
