from sakura import othello

DIRS = [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]

# ---------------- 基本ユーティリティ ----------------
def inb(board, x, y):
    return 0 <= y < len(board) and 0 <= x < len(board[y])

def empties_count(board):
    return sum(1 for y in range(len(board)) for x in range(len(board[y])) if board[y][x] == 0)

def count_discs(board, color):
    return sum(1 for y in range(len(board)) for x in range(len(board[y])) if board[y][x] == color)

def opp_of(color):
    # 環境差を吸収：
    #  - 1/2表現なら 1<->2
    #  - ±1表現なら符号反転
    if color in (1, 2):
        return 3 - color
    return -color

# ---------------- 合法手生成 & 反映 ----------------
def get_moves(board, color):
    opp = opp_of(color)
    moves = []

    for y in range(len(board)):
        for x in range(len(board[y])):
            if board[y][x] != 0:
                continue

            ok = False
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if not inb(board, nx, ny) or board[ny][nx] != opp:
                    continue

                # 相手石が続く間進む
                while inb(board, nx, ny) and board[ny][nx] == opp:
                    nx += dx
                    ny += dy

                # 自分石で挟めていれば合法
                if inb(board, nx, ny) and board[ny][nx] == color:
                    ok = True
                    break

            if ok:
                moves.append((x, y))

    return moves

def apply_move(board, color, move):
    x, y = move
    nb = [r[:] for r in board]
    nb[y][x] = color

    opp = opp_of(color)

    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if not inb(nb, nx, ny) or nb[ny][nx] != opp:
            continue

        path = []
        while inb(nb, nx, ny) and nb[ny][nx] == opp:
            path.append((nx, ny))
            nx += dx
            ny += dy

        if inb(nb, nx, ny) and nb[ny][nx] == color and path:
            for px, py in path:
                nb[py][px] = color

    return nb

# ---------------- 評価関数（シンプルに安定動作重視） ----------------
# 「置けません」をなくす目的なら、まずは評価を堅牢にするのが正解
# 角・辺・機動力・石差（終盤だけ強め）で十分強い
def eval_board(board, color):
    opp = opp_of(color)
    empties = empties_count(board)

    # 角（盤面サイズ依存）
    H = len(board)
    W0 = len(board[0])
    Wb = len(board[H-1])
    CORNERS = {(0,0), (W0-1,0), (0,H-1), (Wb-1,H-1)}

    my_c = sum(1 for (x,y) in CORNERS if inb(board,x,y) and board[y][x] == color)
    op_c = sum(1 for (x,y) in CORNERS if inb(board,x,y) and board[y][x] == opp)

    # 辺（端にある石を少し評価）
    my_edge = 0
    op_edge = 0
    for y in range(H):
        for x in range(len(board[y])):
            if x == 0 or y == 0 or y == H-1 or x == len(board[y]) - 1:
                if board[y][x] == color: my_edge += 1
                elif board[y][x] == opp: op_edge += 1

    # 機動力
    my_m = len(get_moves(board, color))
    op_m = len(get_moves(board, opp))

    # 石差（終盤だけ強め）
    my_d = count_discs(board, color)
    op_d = count_discs(board, opp)

    if empties <= 12:
        return 2000 * (my_d - op_d) + 500 * (my_c - op_c) + 30 * (my_m - op_m)

    return 300 * (my_c - op_c) + 10 * (my_edge - op_edge) + 20 * (my_m - op_m) + 2 * (my_d - op_d)

# ---------------- 探索（negamax + αβ + TT） ----------------
TT = {}

def board_key(board, color):
    return (color, tuple(tuple(r) for r in board))

def game_over(board, color):
    opp = opp_of(color)
    return (len(get_moves(board, color)) == 0) and (len(get_moves(board, opp)) == 0)

def terminal_value(board, color):
    opp = opp_of(color)
    my = count_discs(board, color)
    op = count_discs(board, opp)
    if my > op: return 10**9
    if my < op: return -10**9
    return 0

def ordered_moves(board, color, moves):
    # 角優先 + 相手の手を減らす手を優先
    opp = opp_of(color)
    H = len(board)
    W0 = len(board[0])
    Wb = len(board[H-1])
    CORNERS = {(0,0), (W0-1,0), (0,H-1), (Wb-1,H-1)}

    def score(mv):
        x, y = mv
        s = 0
        if (x,y) in CORNERS:
            s += 100000
        nb = apply_move(board, color, mv)
        s += 30 * (len(get_moves(board, opp)) - len(get_moves(nb, opp)))
        return s

    return sorted(moves, key=score, reverse=True)

def negamax(board, color, depth, alpha, beta):
    key = board_key(board, color)
    if key in TT:
        tt_depth, tt_val = TT[key]
        if tt_depth >= depth:
            return tt_val

    opp = opp_of(color)
    moves = get_moves(board, color)

    if game_over(board, color):
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

# ---------------- AI本体（座標も自動対応） ----------------
def myai(board, color):
    # 念のため毎手TTを肥大化させすぎない（軽く）
    # TT.clear()  # 強くしたいならコメントアウト（保持した方が強い）

    moves = get_moves(board, color)
    if not moves:
        return (-1, -1)

    empties = empties_count(board)

    # 深さ（重くしすぎない）
    if empties <= 12:
        max_depth = empties
    elif empties <= 22:
        max_depth = 7
    elif empties <= 44:
        max_depth = 6
    else:
        max_depth = 5

    best_move = moves[0]
    best_val = -10**18

    # 反復深化
    for depth in range(2, max_depth + 1):
        alpha, beta = -10**18, 10**18
        for mv in ordered_moves(board, color, moves):
            nb = apply_move(board, color, mv)
            val = -negamax(nb, opp_of(color), depth-1, -beta, -alpha)
            if val > best_val:
                best_val = val
                best_move = mv
            if val > alpha:
                alpha = val

    # --- ここが超重要：座標系が (x,y) か (y,x) か自動で合わせる ---
    # sakura側がどっちでも、「合法手として認識される方」を返す
    cand1 = best_move
    cand2 = (best_move[1], best_move[0])

    if cand1 in moves:
        return cand1
    if cand2 in moves:
        return cand2

    # 万一ズレても置けません連発を防ぐ：確実に合法な手を返す
    return moves[0]

othello.play(myai)
