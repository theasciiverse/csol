#!/usr/bin/env python3
"""Records asciiverse/csol.cast, the catalog preview, at 100x30
(hub/RECORDING.md): a game of FreeCell played from the deal to the win,
with the mouse, then csol's victory animation.

FreeCell deals every card face up, so the script reads the deal off the
screen, solves it (a best-first search under csol's own rules: one card to
a free cell or a foundation, a run of k cards to a column only with k-1
free cells, empty columns not counted, and safe moves home made at once),
then plays the solution as a player with a mouse would: a left click
picks a card (and the cards on it), a right click puts them down.

The seed fixes the deal (-s 1; its solution is 88 moves). csol runs from a
throwaway folder holding the binary with its csolrc, games and themes, and
a throwaway HOME, so nothing touches your own settings or scores; it is
named by bare command, so the cast's header holds no local path.

Needs asciinema 3.x and pyte. Usage, from the repo root, with csol built
into out/:
  uv run --with pyte python3 asciiverse/record-preview.py
Any extra argument is used as the cast's path instead (for test runs);
DEBUG=1 checks the board against the plan after every move.
Run it under a memory cap: systemd-run --user --scope -p MemoryMax=4G ..."""
import fcntl, os, pty, select, shutil, struct, sys, tempfile, termios, time
import heapq, itertools, re
import pyte

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cast = sys.argv[1] if len(sys.argv) > 1 else f"{root}/asciiverse/csol.cast"
COLS, ROWS, SEED = 100, 30, "1"


# reading the board
RANKS = {"A":1,"J":11,"Q":12,"K":13}
SUITS = {"♥":"H","♦":"D","♠":"S","♣":"C"}
def card_at(line, x0):
    m = re.match(r"(10|[2-9AJQK])([♥♦♠♣])", line[x0+1:x0+4])
    if not m: return None
    r = RANKS.get(m.group(1)) or int(m.group(1))
    return (r, SUITS[m.group(2)])
def read_board(display):
    """cells[4], foundations[4] (top card or None), tableau[8] lists bottom->top"""
    top = [card_at(display[1], 2 + 8*i) for i in range(8)]
    tab = []
    for i in range(8):
        col = []
        for y in range(6, len(display)):
            c = card_at(display[y], 2 + 8*i)
            if c is None: break
            col.append(c)
        tab.append(col)
    return top[:4], top[4:], tab


# solving it
RED = {"H", "D"}
def red(c): return c[1] in RED
def fits(c, onto): return onto[0] == c[0] + 1 and red(onto) != red(c)

def key(cells, found, tab):
    return (tuple(sorted(c for c in cells if c)), tuple(sorted(found.items())), tuple(sorted(tuple(t) for t in tab)))

def safe_auto(card, found):
    # safe to send home when both opposite-colour foundations are at least rank-1
    r, s = card
    if found.get(s, 0) != r - 1: return False
    if r <= 2: return True
    opp = ["C", "S"] if s in RED else ["H", "D"]
    return all(found.get(o, 0) >= r - 1 for o in opp)

def moves(cells, found, tab):
    free = sum(1 for c in cells if c is None)
    out = []
    # to foundation
    for i, c in enumerate(cells):
        if c and found.get(c[1], 0) == c[0] - 1: out.append(("cf", i))
    for i, t in enumerate(tab):
        if t and found.get(t[-1][1], 0) == t[-1][0] - 1: out.append(("tf", i))
    # runs between columns
    for i, t in enumerate(tab):
        if not t: continue
        run = 1
        while run < len(t) and fits(t[-run], t[-run-1]): run += 1
        for j, d in enumerate(tab):
            if i == j: continue
            for k in range(1, run + 1):
                if k - 1 > free: break
                c = t[-k]
                if (d and fits(c, d[-1])) or (not d and k < len(t)):
                    out.append(("tt", i, j, k))
    # cell to column
    for i, c in enumerate(cells):
        if not c: continue
        for j, d in enumerate(tab):
            if (d and fits(c, d[-1])) or not d: out.append(("ct", i, j))
    # column to cell
    if free:
        ci = cells.index(None)
        for i, t in enumerate(tab):
            if t: out.append(("tc", i, ci))
    return out

def apply(state, m):
    cells, found, tab = list(state[0]), dict(state[1]), [list(t) for t in state[2]]
    if m[0] == "cf": c = cells[m[1]]; cells[m[1]] = None; found[c[1]] = c[0]
    elif m[0] == "tf": c = tab[m[1]].pop(); found[c[1]] = c[0]
    elif m[0] == "tt": run = tab[m[1]][-m[3]:]; del tab[m[1]][-m[3]:]; tab[m[2]] += run
    elif m[0] == "ct": tab[m[2]].append(cells[m[1]]); cells[m[1]] = None
    elif m[0] == "tc": cells[m[2]] = tab[m[1]].pop()
    return cells, found, tab

def autoplay(state):
    seq = []
    while True:
        cells, found, tab = state
        for i, c in enumerate(cells):
            if c and safe_auto(c, found): m = ("cf", i); break
        else:
            for i, t in enumerate(tab):
                if t and safe_auto(t[-1], found): m = ("tf", i); break
            else:
                return state, seq
        state = apply(state, m); seq.append(m)

def h(state):
    cells, found, tab = state
    left = 52 - sum(found.values())
    # cards lying on a lower card hold it back
    blocked = sum(1 for t in tab for d, c in enumerate(t) if any(x[0] < c[0] for x in t[:d]))
    used = sum(1 for c in cells if c)
    return left * 3 + blocked * 2 + used

def solve(cells, found, tab, limit=400000):
    start, auto = autoplay((cells, found, tab))
    seen = {key(*start)}
    cnt = itertools.count()
    heap = [(h(start), next(cnt), start, auto)]
    while heap and limit:
        limit -= 1
        _, _, st, path = heapq.heappop(heap)
        if sum(st[1].values()) == 52: return path
        for m in moves(*st):
            ns, more = autoplay(apply(st, m))
            k = key(*ns)
            if k in seen: continue
            seen.add(k)
            np = path + [m] + more
            heapq.heappush(heap, (h(ns) + len(np) * 0.5, next(cnt), ns, np))
    return None


# the board on screen: piles 8 columns apart from column 2; the free cells
# and foundations on row 1, the columns from row 6, a row per card
def px(i): return 2 + 8 * i + 2

home = tempfile.mkdtemp(prefix="csol-preview-")
inst = os.path.join(home, "csol")
os.makedirs(inst)
shutil.copy(f"{root}/out/csol", inst)
shutil.copy(f"{root}/csolrc", inst)
shutil.copytree(f"{root}/games", f"{inst}/games")
shutil.copytree(f"{root}/themes", f"{inst}/themes")
env = dict(os.environ, TERM="xterm-256color", LANG="C.UTF-8", HOME=home,
           XDG_CONFIG_HOME=f"{home}/.config", XDG_DATA_HOME=f"{home}/.local/share",
           PATH=f"{inst}:{os.environ['PATH']}")
for v in ("VTE_VERSION", "TERM_PROGRAM", "TERM_PROGRAM_VERSION", "TMUX", "KITTY_WINDOW_ID"):
    env.pop(v, None)

pid, fd = pty.fork()
if pid == 0:
    os.chdir(home)
    os.execvpe("asciinema", ["asciinema", "rec", "--overwrite", "-q", "--idle-time-limit", "2",
        "--window-size", f"{COLS}x{ROWS}", "--capture-env", "TERM,LANG",
        "--title", "csol", "--command", f"csol -s {SEED} freecell", cast], env)
fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
screen = pyte.Screen(COLS, ROWS)
stream = pyte.ByteStream(screen)


def pump(seconds):
    end = time.time() + seconds
    while True:
        left = end - time.time()
        r, _, _ = select.select([fd], [], [], max(0.0, min(0.02, left)))
        if r:
            try:
                stream.feed(os.read(fd, 65536))
            except OSError:
                return
        if left <= 0:
            return


def click(x, y, button, wait):
    """button 0 is the left, 2 the right; SGR mouse reports. ncurses holds a
    click back for its double-click interval (1/6 s) before reporting it, so
    the next click must wait at least that long"""
    os.write(fd, f"\x1b[<{button};{x + 1};{y + 1}M".encode())
    pump(0.04)
    os.write(fd, f"\x1b[<{button};{x + 1};{y + 1}m".encode())
    pump(wait)


pump(2.0)
cells, found, tab = read_board(screen.display)
assert sum(len(t) for t in tab) == 52, "the deal did not read as 52 cards"
plan = solve([None] * 4, {}, tab)
assert plan, "no solution found"
print(f"{len(plan)} moves", file=sys.stderr)

state = ([None] * 4, {}, [list(t) for t in tab])
slots = []                               # suit in each foundation, left to right
for n, m in enumerate(plan):
    cells, found, tab = state
    home_move = m[0] in ("cf", "tf")
    # pick up
    if m[0] in ("cf", "ct"):
        click(px(m[1]), 2, 0, 0.2)
    elif m[0] in ("tf", "tc"):
        click(px(m[1]), 6 + len(tab[m[1]]) - 1, 0, 0.2)
    else:
        click(px(m[1]), 6 + len(tab[m[1]]) - m[3], 0, 0.2)
    # put down
    if home_move:
        card = cells[m[1]] if m[0] == "cf" else tab[m[1]][-1]
        if card[1] not in slots:
            slots.append(card[1])
        click(px(4 + slots.index(card[1])), 2, 2, 0.2)
    elif m[0] == "tc":
        click(px(m[2]), 2, 2, 0.3)
    else:
        dest = tab[m[2]]
        click(px(m[2]), 6 + max(len(dest) - 1, 0), 2, 0.3)
    state = apply(state, m)
    if os.environ.get("DEBUG"):
        got = read_board(screen.display)
        want_tab = [[tuple(c) for c in t] for t in state[2]]
        if got[2] != want_tab or sorted(c for c in got[0] if c) != sorted(c for c in state[0] if c):
            print(f"move {n} {m}: board differs from the plan", file=sys.stderr)
            break
pump(7.0)                                # the victory animation
os.write(fd, b"q")
pump(0.5)
os.write(fd, b"y")
for _ in range(50):
    if os.waitpid(pid, os.WNOHANG)[0]:
        break
    time.sleep(0.2)
shutil.rmtree(home, ignore_errors=True)

# csol names its configuration file before the board comes up, here a
# throwaway path; drop that line from the cast, keeping the timing
import json
lines = open(cast).read().splitlines()
out, carry = [lines[0]], 0.0
for line in lines[1:]:
    ev = json.loads(line)
    if ev[1] == "o" and ev[2].startswith("Using configuration file:"):
        carry += ev[0]
        continue
    ev[0] = round(ev[0] + carry, 6)
    carry = 0.0
    out.append(json.dumps(ev, ensure_ascii=False))
open(cast, "w").write("\n".join(out) + "\n")
