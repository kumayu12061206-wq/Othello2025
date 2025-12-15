from sakura import othello

DIRS = [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]
CORNERS = {(0,0),(7,0),(0,7),(7,7)}
C_SQUARES = {(1,0),(0,1),(6,0),(7,1),(0,6),(1,7),(6,7),(7,6)}
X_SQUARES = {(1,1),(6,1),(1,6),(6,6)}

W = [
    [120,-20, 20,  5,  5, 20,-20,120],
    [-20,-40, -5, -5, -5, -5,-40,-20],
    [ 20, -5, 15,  3,  3, 15, -5, 20],
    [  5, -5,  3,  3,  3,  3, -5,  5],
    [  5, -5,  3,  3,  3,  3, -5,  5],
    [ 20, -5, 15,  3,  3, 15, -5, 20],
    [-20,-40, -5, -5, -5, -5,-40,-20],
    [120,-20, 20,  5,  5, 20,-20,120],
]

def inb(x,y): return 0 <= x < 8 and 0 <= y < 8

def get_moves(board, color):
    opp = -color
    moves = []
    for y in range(8):
        for x in range(8):
            if board[y][x] != 0:
                continue
            ok = False
            for dx, dy in DIRS:
                nx, ny = x+dx, y+dy
                if not inb(nx,ny) or board[ny][nx] != opp:
                    continue
                while inb(nx,ny) and board[ny][nx] == opp:
                    nx += dx; ny += dy
                if inb(nx,ny) and board[ny][nx] == color:
                    ok = True
                    break
            if ok:
                moves.append((x,y))
    return moves

def apply_move(board, color, move):
    x,y = move
    nb = [r[:] for r in board]
    nb[y][x] = color
    opp = -color
    for dx, dy in DIRS:
        nx, ny = x+dx, y+dy
        if not inb(nx,ny) or nb[ny][nx] != opp:
            continue
        path = []
        while inb(nx,ny) and nb[ny][nx] == opp:
            path.append((nx,ny))
            nx += dx; ny += dy
        if inb(nx,ny) and nb[ny][nx] == color and path:
            for px, py in path:
                nb[py][px] = color
    return nb

def empties_count(board):
    return sum(1 for y in range(8) for x in range(8) if board[y][x] == 0)

def count_discs(board, color):
    return sum(1 for y in range(8) for x in range(8) if board[y][x] == color)

def frontier_count(board, color):
    c = 0
    for y in range(8):
        for x in range(8):
            if board[y][x] != color:
                continue
            for dx, dy in DIRS:
                nx, ny = x+dx, y+dy
                if inb(nx,ny) and board[ny][nx] == 0:
                    c += 1
                    break
    return c

def danger_penalty(board, color):
    # 角が空の時のX/Cは危険（近似）
    p = 0
    for (x,y) in X_SQUARES:
        if board[y][x] == color:
            p += 18
    for (x,y) in C_SQUARES:
        if board[y][x] == color:
            p += 8
    return p

# ---------------- 安定石（確定石）近似 ----------------
# 角から伸びる「確定辺」をまず確定 → その後、安定伝播で増やす
def stable_discs(board, color):
    stable = [[False]*8 for _ in range(8)]

    def mark(x,y):
        stable[y][x] = True

    # 角を起点に、同色が連続する限り辺を確定
    def mark_from_corner(cx, cy, dx, dy):
        x, y = cx, cy
        if board[y][x] != color:
            return
        mark(x,y)
        x += dx; y += dy
        while inb(x,y) and board[y][x] == color:
            mark(x,y)
            x += dx; y += dy

    # 4角から上下左右に
    mark_from_corner(0,0, 1,0); mark_from_corner(0,0, 0,1)
    mark_from_corner(7,0,-1,0); mark_from_corner(7,0, 0,1)
    mark_from_corner(0,7, 1,0); mark_from_corner(0,7, 0,-1)
    mark_from_corner(7,7,-1,0); mark_from_corner(7,7, 0,-1)

    # 安定伝播：上下左右それぞれについて「端 or 安定石」に挟まれている（または端まで同色が続く）なら安定
    def stable_in_dir(x,y, dx,dy):
        # その方向に端まで同色が続くなら安定
        nx, ny = x+dx, y+dy
        while inb(nx,ny) and board[ny][nx] == color:
            nx += dx; ny += dy
        if not inb(nx,ny):  # 端に到達
            return True
        if stable[ny-dy][nx-dx] and board[ny-dy][nx-dx] == color and not inb(nx,ny):
            return True
        return False

    changed = True
    while changed:
        changed = False
        for y in range(8):
            for x in range(8):
                if board[y][x] != color or stable[y][x]:
                    continue

                # 4方向ペア（左右・上下・斜め2本）で「少なくとも2ペアが安定」なら安定扱い（近似）
                pairs_ok = 0
                for (dx1,dy1, dx2,dy2) in [(1,0,-1,0),(0,1,0,-1),(1,1,-1,-1),(1,-1,-1,1)]:
                    ok1 = stable_in_dir(x,y, dx1,dy1) or (inb(x+dx1,y+dy1) and stable[y+dy1][x+dx1])
                    ok2 = stable_in_dir(x,y, dx2,dy2) or (inb(x+dx2,y+dy2) and stable[y+dy2][x+dx2])
                    if ok1 and ok2:
                        pairs_ok += 1
                if pairs_ok >= 2:
                    stable[y][x] = True
                    changed = True

    return sum(1 for y in range(8) for x in range(8) if stable[y][x])

# ---------------- 評価＆探索 ----------------
def parity_score(board):
    return 1 if (empties_count(board) % 2 == 1) else -1

def eval_board(board, color):
    opp = -color
    empties = empties_count(board)

    my_discs = count_discs(board, color)
    op_discs = count_discs(board, opp)

    # 位置重み
    pos = 0
    for y in range(8):
        for x in range(8):
            if board[y][x] == color: pos += W[y][x]
            elif board[y][x] == opp: pos -= W[y][x]

    # 角
    my_c = sum(1 for (x,y) in CORNERS if board[y][x] == color)
    op_c = sum(1 for (x,y) in CORNERS if board[y][x] == opp)
    corner = 120 * (my_c - op_c)

    # 機動力
    my_m = len(get_moves(board, color))
    op_m = len(get_moves(board, opp))
    mobility = 0
    if my_m + op_m:
        mobility = 22 * (my_m - op_m)

    # フロンティア（少ないほど良い）
    my_f = frontier_count(board, color)
    op_f = frontier_count(board, opp)
    frontier = -9 * (my_f - op_f)

    # 危険マス
    danger = -danger_penalty(board, color) + danger_penalty(board, opp)

    # ★安定石（確定石）差分：ここが“もう一段”強くなるポイント
    my_s = stable_discs(board, color)
    op_s = stable_discs(board, opp)
    stable = 35 * (my_s - op_s)

    # 終盤：石差を強く（勝ち切り）
    if empties <= 10:
        return 2500 * (my_discs - op_discs) + 800 * (my_c - op_c) + 120 * (my_s - op_s)

    return pos + corner + mobility + frontier + danger + stable + 6 * parity_score(board)

TT = {}

def board_key(board, color):
    return (color, tuple(tuple(r) for r in board))

def terminal_value(board, color):
    opp = -color
    my = count_discs(board, color)
    op = count_discs(board, opp)
    if my > op: return 1000000
    if my < op: return -1000000
    return 0

def ordered_moves(board, color, moves):
    opp = -color
    def score(m):
        x,y = m
        s = W[y][x]
        if (x,y) in CORNERS: s += 100000
        if (x,y) in X_SQUARES: s -= 2500
        if (x,y) in C_SQUARES: s -= 900
        nb = apply_move(board, color, m)
        s += 12 * (len(get_moves(board, opp)) - len(get_moves(nb, opp)))
        return s
    return sorted(moves, key=score, reverse=True)

def negamax(board, color, depth, alpha, beta):
    key = board_key(board, color)
    if key in TT:
        tt_depth, tt_val = TT[key]
        if tt_depth >= depth:
            return tt_val

    moves = get_moves(board, color)
    opp = -color

    if not moves and not get_moves(board, opp):
        v = terminal_value(board, color)
        TT[key] = (depth, v)
        return v

    if depth == 0:
        v = eval_board(board, color)
        TT[key] = (depth, v)
        return v

    if not moves:
        v = -negamax(board, opp, depth-1, -beta, -alpha)
        TT[key] = (depth, v)
        return v

    best = -10**18
    for mv in ordered_moves(board, color, moves):
        nb = apply_move(board, color, mv)
        v = -negamax(nb, opp, depth-1, -beta, -alpha)
        if v > best:
            best = v
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break

    TT[key] = (depth, best)
    return best

def myai(board, color):
    moves = get_moves(board, color)
    if not moves:
        return (-1, -1)

    # 角は即打ち
    for mv in moves:
        if mv in CORNERS:
            return mv

    empties = empties_count(board)

    # 終盤は完全読み（空き<=12なら終局まで）
    if empties <= 12:
        max_depth = empties
    elif empties <= 22:
        max_depth = 8
    elif empties <= 44:
        max_depth = 7
    else:
        max_depth = 6

    best_move = moves[0]
    best_val = -10**18

    for depth in range(2, max_depth+1):
        alpha, beta = -10**18, 10**18
        for mv in ordered_moves(board, color, moves):
            nb = apply_move(board, color, mv)
            val = -negamax(nb, -color, depth-1, -beta, -alpha)
            if val > best_val:
                best_val = val
                best_move = mv
            if val > alpha:
                alpha = val

    return best_move

othello.play(myai)
