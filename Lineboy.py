import pyxel
import random
import math

# ─── Constants ─────────────────────────────────────────────────────────────────
W  = 512
H  = 512
FPS = 60

# Pyxel 16-color palette indices
C_BLACK  = 0
C_NAVY   = 1
C_PURPLE = 2
C_GREEN  = 3
C_BROWN  = 4
C_DKBLUE = 5
C_LTBLUE = 6
C_WHITE  = 7
C_RED    = 8
C_ORANGE = 9
C_YELLOW = 10
C_LIME   = 11
C_CYAN   = 12
C_GRAY   = 13
C_PINK   = 14
C_PEACH  = 15

# World themes (color for ground/outline, color for accent, sky deco color)
WORLD_THEMES = [
    {"name": "Forest",    "ground": C_GREEN,  "accent": C_BROWN,  "sky": C_LIME,   "bg": C_BLACK},
    {"name": "Desert",    "ground": C_ORANGE, "accent": C_YELLOW, "sky": C_PEACH,  "bg": C_BLACK},
    {"name": "Cave",      "ground": C_CYAN,   "accent": C_GRAY,   "sky": C_LTBLUE, "bg": C_BLACK},
    {"name": "Ghost",     "ground": C_PURPLE, "accent": C_PINK,   "sky": C_WHITE,  "bg": C_BLACK},
    {"name": "Volcano",   "ground": C_RED,    "accent": C_ORANGE, "sky": C_PINK,   "bg": C_BLACK},
]

# Game states
ST_TITLE    = 0
ST_PLAY     = 1
ST_GAMEOVER = 2
ST_CLEAR    = 3

# Physics
GRAVITY      = 0.55
JUMP_VEL     = -9.5
MAX_FALL     = 12.0
MOVE_SPEED   = 3.2
FRICTION     = 0.80

# Player size (pixels)
PW = 12
PH = 14

# World scroll speed (camera follows player)
# Level width in pixels (procedural tiles)
LEVEL_W = W * 4   # 4 screens wide

# Tile size
TS = 16

# ─── Utility drawing helpers (neon / glow effect via double-draw) ────────────
def neon_line(x1, y1, x2, y2, col_core, col_glow=None):
    """Draw a glowing line: wide dim outer + bright inner."""
    if col_glow is None:
        col_glow = col_core
    pyxel.line(x1-1, y1, x2-1, y2, col_glow if col_glow != col_core else C_BLACK)
    pyxel.line(x1+1, y1, x2+1, y2, col_glow if col_glow != col_core else C_BLACK)
    pyxel.line(x1, y1-1, x2, y2-1, col_glow if col_glow != col_core else C_BLACK)
    pyxel.line(x1, y1+1, x2, y2+1, col_glow if col_glow != col_core else C_BLACK)
    pyxel.line(x1, y1, x2, y2, col_core)

def neon_rectb(x, y, w, h, col_core, col_glow=None):
    """Glowing outline rectangle."""
    if col_glow:
        pyxel.rectb(x-1, y-1, w+2, h+2, col_glow)
    pyxel.rectb(x, y, w, h, col_core)

def neon_circb(x, y, r, col_core, col_glow=None):
    """Glowing outline circle."""
    if col_glow:
        pyxel.circb(x, y, r+1, col_glow)
    pyxel.circb(x, y, r, col_core)

# ─── Font & Text Helpers ───────────────────────────────────────────────────────
FONT_UI = None
FONT_LG = None
FONT_TITLE = None

# Text scale: Pyxel's built-in font is 4×6px per char.
CHAR_W = 4
CHAR_H = 6
TEXT_SCALE = 2

def text_width(s, scale=TEXT_SCALE, font=None):
    if font:
        return font.text_width(s)
    return len(s) * CHAR_W * scale

def draw_text(x, y, s, col, scale=TEXT_SCALE, glow=False, font=None):
    """Draw text, using custom font if provided, else manual pixel scaling."""
    if font:
        if glow:
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                pyxel.text(x + dx, y + dy, s, C_GRAY, font)
        pyxel.text(x, y, s, col, font)
        return

    # Fallback manual scaling
    for row in range(scale):
        for col2 in range(scale):
            pyxel.text(x + col2, y + row, s, col)
    if glow:
        pyxel.text(x - 1, y,     s, C_GRAY)
        pyxel.text(x + 1, y,     s, C_GRAY)
        pyxel.text(x,     y - 1, s, C_GRAY)
        pyxel.text(x,     y + 1, s, C_GRAY)
        for row in range(scale):
            for col2 in range(scale):
                pyxel.text(x + col2, y + row, s, col)

# ─── Spiral decoration (sky background element) ──────────────────────────────
def draw_spiral(cx, cy, max_r, col, t_offset=0):
    """Draw a rectangular spiral (like the ones in the reference images)."""
    step = 4
    x, y = cx, cy
    dirs = [(step, 0), (0, step), (-step, 0), (0, -step)]
    d = t_offset % 4
    length = 2
    drawn = 0
    px, py = x, y
    while drawn < max_r * 2:
        dx, dy = dirs[d % 4]
        nx, ny = px + dx * length, py + dy * length
        nx = max(cx - max_r, min(cx + max_r, nx))
        ny = max(cy - max_r, min(cy + max_r, ny))
        pyxel.line(px, py, nx, ny, col)
        px, py = nx, ny
        d += 1
        length += 1
        drawn += length
        if drawn > max_r * 6:
            break

def draw_dash_line(x1, y1, x2, y2, col):
    """Draw dashed horizontal line (like in reference images)."""
    dx = x2 - x1
    dy = y2 - y1
    length = int(math.sqrt(dx*dx + dy*dy))
    if length == 0:
        return
    for i in range(0, length, 6):
        t1 = i / length
        t2 = min((i + 3) / length, 1.0)
        pyxel.line(
            int(x1 + dx * t1), int(y1 + dy * t1),
            int(x1 + dx * t2), int(y1 + dy * t2),
            col
        )

# ─── Tree drawing ─────────────────────────────────────────────────────────────
def draw_tree(x, y, h, col_trunk, col_leaf, style=0):
    """Draw a pixel-art outline tree."""
    trunk_w = 6
    trunk_h = h // 3
    # Trunk
    pyxel.rectb(x - trunk_w//2, y - trunk_h, trunk_w, trunk_h, col_trunk)
    if style == 0:
        # Round bushy tree (overlapping circles)
        r = h // 3
        neon_circb(x, y - trunk_h - r + 2, r,     col_leaf)
        neon_circb(x - r//2, y - trunk_h - r//2, r-4, col_leaf)
        neon_circb(x + r//2, y - trunk_h - r//2, r-4, col_leaf)
    elif style == 1:
        # Cactus
        ch = trunk_h * 2
        pyxel.rectb(x - 3, y - ch, 6, ch, col_trunk)
        pyxel.rectb(x - 10, y - ch//2 - 4, 7, 6, col_trunk)
        pyxel.rectb(x + 3,  y - ch//2 - 4, 7, 6, col_trunk)
    elif style == 2:
        # Tall thin tree
        pyxel.rectb(x - 3, y - trunk_h*3, 6, trunk_h*3, col_trunk)
        for yy in range(0, trunk_h*3, 6):
            pyxel.line(x-3, y-trunk_h*3+yy, x-8, y-trunk_h*3+yy+3, col_leaf)
            pyxel.line(x+3, y-trunk_h*3+yy, x+8, y-trunk_h*3+yy+3, col_leaf)

# ─── Ground terrain generation ───────────────────────────────────────────────
def gen_terrain(seed, width, theme_idx):
    """Returns list of (x, y, w) ground segments and platform list."""
    rng = random.Random(seed)
    ground_y = H - 80
    segments = []  # (x, y, w) – ground tiles
    platforms = [] # (x, y, w)
    trees     = [] # (x, y, style, col_trunk, col_leaf)
    enemies   = [] # (x, y)
    items     = [] # (x, y) – collectible dots

    theme = WORLD_THEMES[theme_idx]

    # Ground with variable height (jagged)
    x = 0
    while x < width:
        seg_w = rng.randint(TS * 2, TS * 8)
        dy    = rng.randint(-TS, TS)
        ground_y = max(H - 140, min(H - 60, ground_y + dy))
        segments.append((x, ground_y, seg_w))
        x += seg_w

    # Platforms
    for i in range(width // (TS * 8)):
        px = rng.randint(TS * 2, width - TS * 6)
        py = rng.randint(H - 260, H - 120)
        pw = rng.randint(TS * 3, TS * 8)
        platforms.append((px, py, pw))

    # Trees
    for seg in segments[::3]:
        sx, sy, sw = seg
        tx = sx + rng.randint(4, max(5, sw - 4))
        style = rng.randint(0, 2)
        th = rng.randint(32, 64)
        trees.append((tx, sy, th, theme["accent"], theme["ground"], style))

    # Enemies
    for i in range(width // (TS * 16)):
        ex = rng.randint(TS * 4, width - TS * 4)
        # Place on ground (find nearest segment)
        ey = H - 80
        for sx, sy, sw in segments:
            if sx <= ex <= sx + sw:
                ey = sy
                break
        enemies.append((ex, ey))

    # Collectible dots (yellow glowing items)
    for seg in segments[::2]:
        sx, sy, sw = seg
        for _ in range(rng.randint(1, 4)):
            ix = sx + rng.randint(4, max(5, sw - 4))
            items.append((ix, sy - 10))

    return segments, platforms, trees, enemies, items

# ─── Particle ────────────────────────────────────────────────────────────────
# shape: 0=dot  1=rect  2=line-tail  3=spark(no gravity)
class Particle:
    def __init__(self, x, y, vx, vy, col, life, shape=0, gravity=0.15):
        self.x        = float(x)
        self.y        = float(y)
        self.ox       = float(x)   # origin for line-tail
        self.oy       = float(y)
        self.vx       = vx
        self.vy       = vy
        self.col      = col
        self.life_max = life
        self.life     = life
        self.shape    = shape
        self.gravity  = gravity

    def update(self):
        self.ox  = self.x
        self.oy  = self.y
        self.x  += self.vx
        self.y  += self.vy
        self.vy += self.gravity
        self.vx *= 0.96
        self.life -= 1

    def draw(self):
        alpha = self.life / self.life_max
        if alpha <= 0:
            return
        sx, sy = int(self.x), int(self.y)
        col = self.col if alpha > 0.4 else C_GRAY
        if self.shape == 0:  # dot
            pyxel.pset(sx, sy, col)
        elif self.shape == 1:  # small rect
            s = max(1, int(alpha * 3))
            pyxel.rectb(sx - s, sy - s, s * 2 + 1, s * 2 + 1, col)
        elif self.shape == 2:  # line tail
            pyxel.line(int(self.ox), int(self.oy), sx, sy, col)
        elif self.shape == 3:  # spark (bright dot + tail)
            pyxel.line(int(self.ox), int(self.oy), sx, sy, col)
            pyxel.pset(sx, sy, C_WHITE)

# ─── Enemy ───────────────────────────────────────────────────────────────────
class Enemy:
    SIZE = 10

    def __init__(self, x, y, col):
        self.x   = float(x)
        self.y   = float(y)
        self.col = col
        self.vx  = random.choice([-1.0, 1.0])
        self.alive = True
        self.anim  = 0

    def update(self, segments, platforms):
        self.x += self.vx
        self.anim += 1
        # Reverse at segment edges
        on_ground = False
        for sx, sy, sw in segments:
            if sx <= self.x <= sx + sw and abs(self.y - sy) < 2:
                on_ground = True
                if self.x <= sx + 4 or self.x >= sx + sw - 4:
                    self.vx *= -1
                break
        for px, py, pw in platforms:
            if px <= self.x <= px + pw and abs(self.y - py) < 2:
                on_ground = True
                if self.x <= px + 4 or self.x >= px + pw - 4:
                    self.vx *= -1
                break

    def draw(self, cam_x):
        sx = int(self.x - cam_x)
        sy = int(self.y - self.SIZE)
        bob = int(math.sin(self.anim * 0.2) * 2)
        sy += bob
        # Body outline (enemy is a small box with face)
        neon_rectb(sx - self.SIZE//2, sy, self.SIZE, self.SIZE, self.col, C_BLACK)
        # Eyes
        ex = sx - 2 if self.vx > 0 else sx + 2
        pyxel.pset(ex, sy + 3, C_WHITE)
        pyxel.pset(sx,  sy + 3, C_WHITE)
        # Legs animation
        leg = int(self.anim * 0.3) % 4
        pyxel.line(sx - 3, sy + self.SIZE, sx - 3 + leg,   sy + self.SIZE + 4, self.col)
        pyxel.line(sx + 3, sy + self.SIZE, sx + 3 - leg,   sy + self.SIZE + 4, self.col)

# ─── Boss ─────────────────────────────────────────────────────────────────────
class Boss:
    def __init__(self, x, y, col):
        self.x    = float(x)
        self.y    = float(y)
        self.col  = col
        self.hp   = 5
        self.vx   = 1.5
        self.vy   = 0.0
        self.alive = True
        self.flash = 0
        self.size  = 40
        self.timer = 0

    def update(self, player):
        self.timer += 1
        # Chase player slowly
        dx = (player.x + PW//2) - self.x
        dy = (player.y + PH//2) - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0:
            speed = 1.2 + self.timer * 0.001
            self.x += (dx / dist) * speed
            self.y += (dy / dist) * speed
        if self.flash > 0:
            self.flash -= 1

    def hit(self):
        self.hp -= 1
        self.flash = 8
        if self.hp <= 0:
            self.alive = False

    def collides_player(self, player):
        dx = abs((player.x + PW//2) - self.x)
        dy = abs((player.y + PH//2) - self.y)
        return dx < self.size * 0.6 and dy < self.size * 0.6

    def draw(self, cam_x):
        sx = int(self.x - cam_x)
        sy = int(self.y)
        r  = self.size
        col = C_WHITE if self.flash % 2 == 1 else self.col
        # Outer glow rings (layered for neon feel)
        neon_circb(sx, sy, r + 6, C_GRAY)
        neon_circb(sx, sy, r + 4, C_BLACK if self.flash % 2 == 0 else col)
        # Main circle
        neon_circb(sx, sy, r, col, C_GRAY)
        # Inner pattern (cross)
        pyxel.line(sx - r + 4, sy,      sx + r - 4, sy,      col)
        pyxel.line(sx,         sy-r+4,  sx,          sy+r-4,  col)
        # Rotating ring segments
        for i in range(8):
            a = (i / 8) * math.pi * 2 + self.timer * 0.05
            rx = int(math.cos(a) * (r - 8))
            ry = int(math.sin(a) * (r - 8))
            pyxel.rectb(sx + rx - 4, sy + ry - 4, 8, 8, col)
        # Counter-rotating inner dots
        for i in range(6):
            a2 = (i / 6) * math.pi * 2 - self.timer * 0.08
            rx2 = int(math.cos(a2) * (r - 20))
            ry2 = int(math.sin(a2) * (r - 20))
            pyxel.pset(sx + rx2, sy + ry2, C_WHITE)

# ─── Player ──────────────────────────────────────────────────────────────────
class Player:
    def __init__(self, x, y):
        self.x     = float(x)
        self.y     = float(y)
        self.vx    = 0.0
        self.vy    = 0.0
        self.on_ground = False
        self.facing    = 1
        self.alive     = True
        self.invincible = 0
        self.score     = 0
        self.stretch_x = 1.0
        self.stretch_y = 1.0
        self.coyote    = 0
        self.jump_buf  = 0
        self.anim      = 0

    def update(self, segments, platforms, enemies, items, boss, particles, col):
        if not self.alive:
            return

        self.anim += 1
        if self.invincible > 0:
            self.invincible -= 1
        if self.coyote   > 0: self.coyote  -= 1
        if self.jump_buf > 0: self.jump_buf -= 1

        # Input
        left  = pyxel.btn(pyxel.KEY_LEFT)  or pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT)
        right = pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT)
        jump  = pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A)
        held  = pyxel.btn(pyxel.KEY_SPACE)  or pyxel.btn(pyxel.KEY_Z)  or pyxel.btn(pyxel.KEY_UP)  or pyxel.btn(pyxel.KEY_W)  or pyxel.btn(pyxel.GAMEPAD1_BUTTON_A)

        # Horizontal
        if left:
            self.vx -= 1.2
            self.facing = -1
        elif right:
            self.vx += 1.2
            self.facing = 1
        else:
            self.vx *= FRICTION

        self.vx = max(-MOVE_SPEED, min(MOVE_SPEED, self.vx))

        # Gravity (lower when holding jump going up)
        grav = GRAVITY * (0.55 if held and self.vy < 0 else 1.0)
        self.vy += grav
        self.vy = min(self.vy, MAX_FALL)

        # Jump buffer
        if jump:
            self.jump_buf = 5

        if self.jump_buf > 0 and self.coyote > 0:
            self.vy = JUMP_VEL
            self.coyote   = 0
            self.jump_buf = 0
            self.stretch_x = 0.6
            self.stretch_y = 1.5
            pyxel.play(3, 0)  # jump sfx
            # Jump burst particles
            for _ in range(10):
                particles.append(Particle(
                    self.x + PW//2, self.y + PH,
                    pyxel.rndf(-2.5, 2.5), pyxel.rndf(0.5, 2.5),
                    col, 18, shape=2, gravity=0.1))

        # Move X
        self.x += self.vx
        self._resolve_x(segments, platforms)

        # Move Y
        self.y += self.vy
        old_on_ground = self.on_ground
        self.on_ground = False
        self._resolve_y(segments, platforms)

        if self.on_ground and not old_on_ground:
            self.stretch_x = 1.4
            self.stretch_y = 0.6
            # Landing dust cloud
            for _ in range(8):
                particles.append(Particle(
                    self.x + PW//2 + pyxel.rndf(-4, 4), self.y + PH,
                    pyxel.rndf(-2, 2), pyxel.rndf(-1, 0.2),
                    col, 14, shape=1, gravity=0.05))

        if self.on_ground:
            self.coyote = 6
            # Running sparks (occasional)
            if abs(self.vx) > 2.0 and self.anim % 8 == 0:
                particles.append(Particle(
                    self.x + PW//2, self.y + PH,
                    -self.vx * 0.4 + pyxel.rndf(-0.5, 0.5), pyxel.rndf(-1.5, -0.2),
                    col, 10, shape=3, gravity=0.12))

        # Recover squash
        self.stretch_x += (1.0 - self.stretch_x) * 0.25
        self.stretch_y += (1.0 - self.stretch_y) * 0.25

        # Fall death
        if self.y > H + 50:
            self._die(particles, col)
            return

        # Collect items
        for item in items[:]:
            ix, iy = item
            if abs(self.x + PW//2 - ix) < 12 and abs(self.y + PH//2 - iy) < 12:
                items.remove(item)
                self.score += 10
                for _ in range(5):
                    particles.append(Particle(ix, iy,
                        pyxel.rndf(-2, 2), pyxel.rndf(-3, 0), C_YELLOW, 20))
                pyxel.play(2, 2)

        # Enemy collision
        if self.invincible == 0:
            for e in enemies:
                if e.alive:
                    if abs(self.x + PW//2 - e.x) < 14 and abs(self.y + PH//2 - e.y) < 14:
                        # Stomp from above?
                        if self.vy > 1 and self.y + PH < e.y + 2:
                            e.alive = False
                            self.vy = -6
                            self.score += 100
                            for _ in range(8):
                                particles.append(Particle(e.x, e.y,
                                    pyxel.rndf(-3, 3), pyxel.rndf(-4, 0), col, 25))
                            pyxel.play(2, 1)
                        else:
                            self._die(particles, col)
                            return

        # Boss collision
        if boss and boss.alive and self.invincible == 0:
            if boss.collides_player(self):
                # Stomp boss?
                if self.vy > 1:
                    boss.hit()
                    self.vy = -8
                    for _ in range(12):
                        particles.append(Particle(boss.x, boss.y,
                            pyxel.rndf(-4, 4), pyxel.rndf(-5, 0), boss.col, 30))
                    pyxel.play(2, 1)
                else:
                    self._die(particles, col)

    def _die(self, particles, col):
        self.alive = False
        cx, cy = self.x + PW//2, self.y + PH//2
        # Big explosion burst
        for _ in range(20):
            particles.append(Particle(cx, cy,
                pyxel.rndf(-5, 5), pyxel.rndf(-6, 1),
                col, 45, shape=3, gravity=0.18))
        for _ in range(12):
            particles.append(Particle(cx, cy,
                pyxel.rndf(-3, 3), pyxel.rndf(-4, 0.5),
                C_WHITE, 30, shape=2, gravity=0.1))
        for _ in range(8):
            particles.append(Particle(cx, cy,
                pyxel.rndf(-2, 2), pyxel.rndf(-3, 0),
                C_YELLOW, 25, shape=1, gravity=0.08))
        pyxel.play(3, 1)

    def _get_ground_y(self, x, segments, platforms):
        """Return ground y under x, or None."""
        best = None
        for sx, sy, sw in segments:
            if sx <= x <= sx + sw:
                if best is None or sy < best:
                    best = sy
        for px, py, pw in platforms:
            if px <= x <= px + pw:
                if best is None or (self.y < py and (best is None or py < best)):
                    best = py
        return best

    def _resolve_x(self, segments, platforms):
        # Clamp to level bounds
        self.x = max(0, self.x)

    def _resolve_y(self, segments, platforms):
        foot = self.y + PH
        head = self.y
        cx   = self.x + PW // 2

        # Collect candidate landing surfaces
        candidates = []

        for sx, sy, sw in segments:
            if sx - 2 <= cx <= sx + sw + 2:
                candidates.append(sy)

        for px, py, pw in platforms:
            if px - 2 <= cx <= px + pw + 2:
                # Only land on top of platform
                if self.vy >= 0 and foot <= py + 18:
                    candidates.append(py)

        if candidates and self.vy >= 0:
            # Find the highest ground surface that is below or at foot
            best = None
            for sy in candidates:
                if foot >= sy - 2 and (best is None or sy < best):
                    best = sy
            if best is not None:
                self.y = float(best - PH)
                self.vy = 0
                self.on_ground = True

    def draw(self, cam_x, col):
        if not self.alive:
            return
        # Blink when invincible
        if self.invincible > 0 and (self.invincible // 4) % 2 == 1:
            return

        sx = int(self.x - cam_x)
        sy = int(self.y)

        sw = int(PW * self.stretch_x)
        sh = int(PH * self.stretch_y)
        ox = (PW - sw) // 2
        oy = PH - sh  # anchor at feet

        # Body (neon outline)
        neon_rectb(sx + ox, sy + oy, sw, sh, col, C_GRAY)

        # Face
        eye_x = sx + (PW - 4 if self.facing > 0 else 2)
        pyxel.pset(eye_x, sy + oy + 3, C_WHITE)

        # Idle bob
        if self.on_ground and abs(self.vx) < 0.3:
            bob = int(math.sin(self.anim * 0.15) * 1.5)
            sy += bob

        # Legs while running
        if not self.on_ground:
            # Show kick
            pyxel.line(sx + 2, sy + PH, sx + 2 + self.facing * 3, sy + PH + 5, col)
            pyxel.line(sx + PW - 3, sy + PH, sx + PW - 3 - self.facing * 3, sy + PH + 5, col)
        else:
            leg = int(self.anim * 0.35) % 4
            pyxel.line(sx + 3,      sy + sh + oy, sx + 3 + leg,      sy + sh + oy + 5, col)
            pyxel.line(sx + sw - 4, sy + sh + oy, sx + sw - 4 - leg, sy + sh + oy + 5, col)

# ─── Level ───────────────────────────────────────────────────────────────────
class Level:
    def __init__(self, world_idx, seed):
        self.world_idx = world_idx
        self.theme = WORLD_THEMES[world_idx]
        self.seed  = seed
        (self.segments, self.platforms,
         self.trees, self.enemies_data, self.items) = gen_terrain(seed, LEVEL_W, world_idx)

        self.enemies = [
            Enemy(ex, ey, self.theme["accent"])
            for ex, ey in self.enemies_data
        ]
        self.goal_x = LEVEL_W - 80

    def draw_bg(self, cam_x, frame):
        """Draw sky background decorations."""
        col_sky = self.theme["sky"]
        col_bg  = self.theme["bg"]

        pyxel.cls(col_bg)

        # Spiral decorations (parallax 0.2) – sparse, small
        rng = random.Random(self.seed + 777)
        for _ in range(6):
            sx = rng.randint(0, LEVEL_W)
            sy = rng.randint(30, H - 220)
            r  = rng.randint(8, 18)
            scx = int(sx - cam_x * 0.25) % (W + 60) - 30
            draw_spiral(scx, sy, r, col_sky, frame // 30 % 4)

        # Dashed lines in upper sky (parallax 0.15)
        rng2 = random.Random(self.seed + 333)
        for _ in range(8):
            lx = rng2.randint(0, LEVEL_W)
            ly = rng2.randint(15, H // 3)
            ln = rng2.randint(20, 60)
            lsx = int(lx - cam_x * 0.15) % (W + 80) - 40
            draw_dash_line(lsx, ly, lsx + ln, ly, col_sky)

        # Mini square particles floating
        rng3 = random.Random(self.seed + 999)
        for _ in range(20):
            px2 = rng3.randint(0, LEVEL_W)
            py2 = rng3.randint(30, H - 200)
            spx = int(px2 - cam_x * 0.18 + frame * 0.2) % (W + 40) - 20
            pyxel.rectb(spx, py2, 3, 3, col_sky)

    def draw_terrain(self, cam_x, frame):
        col   = self.theme["ground"]
        acc   = self.theme["accent"]

        # Trees (parallax 1.0 – world space)
        for tx, ty, th, c_trunk, c_leaf, style in self.trees:
            scrx = int(tx - cam_x)
            if -80 < scrx < W + 80:
                draw_tree(scrx, ty, th, c_trunk, c_leaf, style)

        # Platforms
        for px, py, pw in self.platforms:
            scrx = int(px - cam_x)
            if scrx + pw < 0 or scrx > W:
                continue
            # Jagged top edge (outline only)
            for i in range(0, pw, TS // 2):
                tooth = 4 if (i // (TS // 2)) % 2 == 0 else 2
                pyxel.line(scrx + i, py, scrx + i + TS//2, py, col)
                pyxel.pset(scrx + i, py - tooth, col)
            pyxel.line(scrx, py + 4, scrx + pw, py + 4, acc)

        # Ground segments (jagged top, outline box)
        for sx, sy, sw in self.segments:
            scrx = int(sx - cam_x)
            if scrx + sw < 0 or scrx > W:
                continue
            # Top jagged edge
            for i in range(0, sw, TS // 2):
                tooth = 5 if (i // (TS // 2)) % 2 == 0 else 3
                pyxel.line(scrx + i, sy, scrx + min(i + TS//2, sw), sy, col)
                if i + TS//4 < sw:
                    pyxel.pset(scrx + i + TS//4, sy - tooth, col)
            # Bottom border line
            pyxel.line(scrx, min(sy + 8, H - 2), scrx + sw, min(sy + 8, H - 2), acc)

        # Collectible items (glowing yellow dots)
        for ix, iy in self.items:
            scrx = int(ix - cam_x)
            if -10 < scrx < W + 10:
                bob = int(math.sin(frame * 0.12 + ix * 0.05) * 2)
                pyxel.rectb(scrx - 3, iy + bob - 3, 6, 6, C_YELLOW)
                pyxel.pset(scrx, iy + bob, C_WHITE)

        # Goal flag
        gx = int(self.goal_x - cam_x)
        if -20 < gx < W + 20:
            pyxel.line(gx, H - 180, gx, H - 100, C_WHITE)
            pyxel.rectb(gx, H - 180, 30, 16, C_YELLOW)
            draw_text(gx + 3, H - 178, "GO", C_YELLOW, font=FONT_UI)

    def draw_enemies(self, cam_x, frame):
        for e in self.enemies:
            scrx = int(e.x - cam_x)
            if -30 < scrx < W + 30 and e.alive:
                e.draw(cam_x)

    def update_enemies(self, frame):
        for e in self.enemies:
            e.update(self.segments, self.platforms)

# ─── SkyDeco (stars/orb boss) ─────────────────────────────────────────────────
class BossOrb(Boss):
    pass  # reuse Boss class

# ─── HUD ─────────────────────────────────────────────────────────────────────
def draw_hud(player, world_idx, boss, frame):
    theme = WORLD_THEMES[world_idx]
    col = theme["ground"]

    # Score
    draw_text(6, 6, f"スコア:{player.score}", col, glow=False, font=FONT_UI)

    # World name
    name = theme["name"].upper()
    draw_text(W - text_width(name, font=FONT_UI) - 6, 6, name, col, glow=False, font=FONT_UI)

    # Boss HP bar (if boss active)
    if boss and boss.alive:
        bar_w = 160
        bar_x = W // 2 - bar_w // 2
        bar_y = 20
        bw = text_width("BOSS", font=FONT_UI)
        draw_text(bar_x + bar_w//2 - bw//2, bar_y - 14, "BOSS", C_RED, glow=False, font=FONT_UI)
        neon_rectb(bar_x, bar_y, bar_w, 10, C_RED)
        pyxel.rect(bar_x + 1, bar_y + 1, int(bar_w * boss.hp / 5), 8, C_RED)

# ─── Title Screen ─────────────────────────────────────────────────────────────
_title_pts = []  # ambient title particles (module-level for persistence)

def update_title_particles(frame):
    """Spawn and update ambient floating particles on title screen."""
    global _title_pts
    # Spawn new ones
    if frame % 3 == 0:
        col = random.choice([C_GREEN, C_CYAN, C_LIME, C_ORANGE, C_PINK, C_PURPLE, C_YELLOW])
        shape = random.choice([0, 2, 3])
        _title_pts.append(Particle(
            random.randint(10, W - 10), random.randint(H // 2 + 40, H - 20),
            pyxel.rndf(-0.6, 0.6), pyxel.rndf(-2.5, -0.8),
            col, random.randint(40, 90), shape=shape, gravity=-0.01))
    # Update
    for p in _title_pts:
        p.update()
    _title_pts = [p for p in _title_pts if p.life > 0 and p.y > -10]

def draw_title(frame, world_idx):
    pyxel.cls(C_BLACK)
    t = frame

    # Ambient particles (drawn first, behind everything)
    for p in _title_pts:
        p.draw()

    # Background spirals
    for i, (sx, sy, sr, sc) in enumerate([
        (80, 100, 30, C_GREEN),
        (80, 230, 20, C_LIME),     # New spiral below the green one
        (W-80, 120, 24, C_ORANGE),
        (W-120, 280, 20, C_CYAN),
        (W//2+60, 160, 18, C_PURPLE),
    ]):
        draw_spiral(sx + int(math.sin(t*0.03+i)*10), sy, sr, sc, t // 20)

    letter_cols = [C_GREEN, C_LIME, C_CYAN, C_YELLOW, C_ORANGE, C_PINK, C_PURPLE]

    # Upper element: 7 color-cycling squares
    box_w = 14
    box_h = 14
    box_gap = 6
    total_w = 7 * box_w + 6 * box_gap
    bx = (W - total_w) // 2
    by = H // 2 - 50

    for i in range(7):
        col = letter_cols[(i + t // 10) % len(letter_cols)]
        # Draw glowing solid square
        neon_rectb(bx, by, box_w, box_h, col, C_GRAY)
        pyxel.rect(bx + 1, by + 1, box_w - 2, box_h - 2, col)
        bx += box_w + box_gap

    # "LINE BOY" text (now replacing the old white subtext with rainbow)
    title_str = "LINE BOY"
    font_to_use = FONT_LG if FONT_LG else FONT_TITLE
    if font_to_use:
        tw = text_width(title_str, font=font_to_use)
        tx = (W - tw) // 2
        ty = by + box_h + 16
        
        cx = tx
        for i, ch in enumerate(title_str):
            cw = text_width(ch, font=font_to_use)
            if ch != " ":
                lcol = letter_cols[(i + t // 10) % len(letter_cols)]
                draw_text(cx, ty, ch, lcol, font=font_to_use, glow=False)
            cx += cw
    else:
        # Fallback manual scaling
        char_scale = 4
        tw = text_width(title_str, scale=char_scale)
        tx = (W - tw) // 2
        ty = by + box_h + 24
        cx = tx
        for i, ch in enumerate(title_str):
            cw = text_width(ch, scale=char_scale)
            if ch != " ":
                lcol = letter_cols[(i + t // 10) % len(letter_cols)]
                draw_text(cx, ty, ch, lcol, scale=char_scale, glow=False)
            cx += cw

    # Blinking prompt
    if (t // 20) % 2 == 0:
        prompt = "スペースキーでスタート"
        px2 = (W - text_width(prompt, font=FONT_UI if FONT_UI else None)) // 2
        draw_text(px2, H // 2 + 40, prompt, C_YELLOW, glow=False, font=FONT_UI)

    # Stage Select UI
    theme = WORLD_THEMES[world_idx]
    stage_name = theme["name"].upper()
    stage_text = f"◀ WORLD {world_idx + 1}: {stage_name} ▶"
    s_tw = text_width(stage_text, font=FONT_UI)
    s_tx = (W - s_tw) // 2
    s_ty = H // 2 + 80
    s_col = theme["ground"]
    
    # Selection bounding box
    pad = 8
    hx = s_tx - pad
    hy = s_ty - pad//2
    hw = s_tw + pad*2
    hh = 20
    pyxel.rect(hx, hy, hw, hh, C_BLACK)
    neon_rectb(hx, hy, hw, hh, s_col)
    
    draw_text(s_tx, s_ty, stage_text, s_col, font=FONT_UI)

# ─── World select ─────────────────────────────────────────────────────────────
def draw_world_select(frame, selected):
    pyxel.cls(C_BLACK)
    pyxel.text((W - 80)//2, 40, "SELECT WORLD", C_WHITE)

    for i, theme in enumerate(WORLD_THEMES):
        col = theme["ground"]
        row = i
        x = W//2 - 80
        y = 80 + row * 52

        if i == selected:
            neon_rectb(x - 4, y - 4, 168, 44, col, C_GRAY)
        else:
            pyxel.rectb(x - 4, y - 4, 168, 44, C_GRAY)

        pyxel.text(x, y, theme["name"].upper(), col)
        # Color swatch
        pyxel.rect(x + 120, y, 10, 10, col)
        pyxel.rect(x + 134, y, 10, 10, theme["accent"])

    pyxel.text(10, H - 30, "UP/DOWN:SELECT  SPACE:GO", C_WHITE)

# ─── App ─────────────────────────────────────────────────────────────────────
class App:
    def __init__(self):
        pyxel.init(W, H, title="Lineboy", fps=FPS)

        # ── Neon fluorescent palette (overwrite all 16 slots) ──────────────────
        # 0: deep black background
        pyxel.colors[0]  = 0x050508
        # 1: dark navy (dim glow)
        pyxel.colors[1]  = 0x0D1B4B
        # 2: neon purple
        pyxel.colors[2]  = 0xBF00FF
        # 3: neon green
        pyxel.colors[3]  = 0x39FF14
        # 4: warm brown / copper (trunk)
        pyxel.colors[4]  = 0xA0522D
        # 5: dim blue (glow shadow)
        pyxel.colors[5]  = 0x1A3A5C
        # 6: electric blue
        pyxel.colors[6]  = 0x00BFFF
        # 7: bright white
        pyxel.colors[7]  = 0xF0F0FF
        # 8: neon red
        pyxel.colors[8]  = 0xFF2020
        # 9: neon orange
        pyxel.colors[9]  = 0xFF6B00
        # 10: neon yellow
        pyxel.colors[10] = 0xFFFF00
        # 11: neon lime
        pyxel.colors[11] = 0xCCFF00
        # 12: neon cyan
        pyxel.colors[12] = 0x00F5FF
        # 13: mid gray (glow outer)
        pyxel.colors[13] = 0x404050
        # 14: neon pink / hot pink
        pyxel.colors[14] = 0xFF1493
        # 15: neon peach / salmon
        pyxel.colors[15] = 0xFF7F50

        # Setup Sounds
        # 0: jump
        pyxel.sounds[0].set("a3c4", "p", "76", "n", 6)
        # 1: enemy stomp
        pyxel.sounds[1].set("c3a2", "n", "76", "f", 5)
        # 2: collect
        pyxel.sounds[2].set("e4g4a4", "t", "765", "n", 4)
        # 3: die
        pyxel.sounds[3].set("c2a1f1", "n", "776", "f", 10)

        # ── Load Custom Fonts ──────────────────────────────────────────────────────
        global FONT_UI, FONT_LG, FONT_TITLE
        import os
        fonts_to_try = [
            "./ZenKakuGothicNew-Medium.ttf",
        ]
        for fp in fonts_to_try:
            if os.path.exists(fp):
                try:
                    FONT_UI    = pyxel.Font(fp, 12)
                    FONT_LG    = pyxel.Font(fp, 24)
                    FONT_TITLE = pyxel.Font(fp, 24)
                    break
                except Exception:
                    pass

        # Title screen ambient particles
        self.title_particles = []

        self.state      = ST_TITLE
        self.world_idx  = 0
        self.level      = None
        self.player     = None
        self.boss       = None
        self.particles  = []
        self.cam_x      = 0.0
        self.shake      = 0
        self.boss_triggered = False
        self.world_complete = False
        self.over_timer = 0
        self.score_total= 0

        pyxel.run(self.update, self.draw)

    def _start_level(self):
        seed = self.world_idx * 9999 + 42
        self.level  = Level(self.world_idx, seed)
        theme = WORLD_THEMES[self.world_idx]

        # Player starts at left side on first ground segment
        start_y = H - 160
        if self.level.segments:
            start_y = self.level.segments[0][1]
        self.player = Player(60, start_y - PH - 2)
        self.particles = []
        self.cam_x  = 0.0
        self.shake  = 0
        self.boss_triggered = False
        self.world_complete = False
        self.over_timer = 0

        # Boss at end of level
        boss_x = LEVEL_W - 200
        boss_y = start_y - 80
        self.boss = Boss(boss_x, boss_y, WORLD_THEMES[self.world_idx]["ground"])

    def update(self):
        frame = pyxel.frame_count

        if self.state == ST_TITLE:
            update_title_particles(frame)
            
            # Select level
            if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT):
                self.world_idx = (self.world_idx - 1) % len(WORLD_THEMES)
                pyxel.play(2, 0)
            if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT):
                self.world_idx = (self.world_idx + 1) % len(WORLD_THEMES)
                pyxel.play(2, 0)

            if (pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_Z) or
                    pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A)):
                self.state = ST_PLAY
                self._start_level()
            return

        if self.state == ST_GAMEOVER:
            self.over_timer += 1
            if self.over_timer > 60:
                if (pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_Z) or
                        pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A)):
                    self.state = ST_TITLE
            return

        if self.state == ST_CLEAR:
            self.over_timer += 1
            if self.over_timer > 60:
                if (pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_Z) or
                        pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A)):
                    # Next world
                    self.score_total += self.player.score
                    self.world_idx = (self.world_idx + 1) % len(WORLD_THEMES)
                    self.state = ST_PLAY
                    self._start_level()
            return

        # ── Gameplay ──────────────────────────────────────────────────────────
        lv = self.level
        p  = self.player

        # Activate boss when player near end
        if not self.boss_triggered and p.x > LEVEL_W - 400:
            self.boss_triggered = True
            self.shake = 20

        # Update player
        p.update(lv.segments, lv.platforms, lv.enemies, lv.items,
                 self.boss if self.boss_triggered else None,
                 self.particles, WORLD_THEMES[self.world_idx]["ground"])

        if not p.alive:
            self.shake = 15
            self.state = ST_GAMEOVER
            return

        # Update boss
        if self.boss_triggered and self.boss.alive:
            self.boss.update(p)
            # Boss aura particles (every 3 frames)
            if frame % 3 == 0:
                a = (frame * 0.15)
                for ring_r in [self.boss.size + 2, self.boss.size - 10]:
                    ox = int(math.cos(a) * ring_r)
                    oy = int(math.sin(a) * ring_r)
                    self.particles.append(Particle(
                        self.boss.x + ox, self.boss.y + oy,
                        pyxel.rndf(-0.5, 0.5), pyxel.rndf(-0.5, 0.5),
                        self.boss.col, 20, shape=3, gravity=0.0))
            if not self.boss.alive:
                # Level clear! – big celebratory burst
                for _ in range(40):
                    self.particles.append(Particle(
                        self.boss.x, self.boss.y,
                        pyxel.rndf(-6, 6), pyxel.rndf(-7, 0),
                        random.choice([C_YELLOW, C_WHITE, C_CYAN, C_LIME, C_PINK]),
                        60, shape=random.choice([0, 1, 3]), gravity=0.15))
                for _ in range(20):
                    self.particles.append(Particle(
                        self.boss.x, self.boss.y,
                        pyxel.rndf(-4, 4), pyxel.rndf(-5, 0),
                        self.boss.col, 45, shape=2, gravity=0.1))
                self.state = ST_CLEAR
                self.over_timer = 0
                return

        # Update enemies
        lv.update_enemies(frame)

        # Update particles
        for pt in self.particles[:]:
            pt.update()
            if pt.life <= 0:
                self.particles.remove(pt)

        # Camera: smooth follow
        target_cam = p.x - W // 3
        target_cam = max(0, min(LEVEL_W - W, target_cam))
        self.cam_x += (target_cam - self.cam_x) * 0.12

        # Goal reach (only if boss defeated)
        if not self.boss.alive and p.x >= self.level.goal_x:
            self.state = ST_CLEAR
            self.over_timer = 0

        if self.shake > 0:
            self.shake -= 1

    def draw(self):
        frame = pyxel.frame_count

        if self.state == ST_TITLE:
            draw_title(frame, self.world_idx)
            return

        if self.state == ST_GAMEOVER:
            self._draw_game()
            col = WORLD_THEMES[self.world_idx]["ground"]
            msg = "ゲームオーバー"
            mw = text_width(msg, font=FONT_LG)
            pyxel.rect(W//2 - mw//2 - 12, H//2 - 28, mw + 24, 66, C_BLACK)
            neon_rectb(W//2 - mw//2 - 12, H//2 - 28, mw + 24, 66, col)
            draw_text((W - mw) // 2, H//2 - 18, msg, col, glow=False, font=FONT_LG)
            sub = "スペースでタイトルへ"
            draw_text((W - text_width(sub, font=FONT_UI)) // 2, H//2 + 16, sub, C_WHITE, font=FONT_UI)
            return

        if self.state == ST_CLEAR:
            self._draw_game()
            col = WORLD_THEMES[self.world_idx]["ground"]
            msg = "ワールドクリア！"
            mw = text_width(msg, font=FONT_LG)
            pyxel.rect(W//2 - mw//2 - 12, H//2 - 32, mw + 24, 80, C_BLACK)
            neon_rectb(W//2 - mw//2 - 12, H//2 - 32, mw + 24, 80, col)
            draw_text((W - mw) // 2, H//2 - 22, msg, C_YELLOW, glow=False, font=FONT_LG)
            sc = f"最終スコア:{self.player.score}"
            draw_text((W - text_width(sc, font=FONT_UI)) // 2, H//2 + 10, sc, col, font=FONT_UI)
            nxt = "スペースキーで次へ"
            draw_text((W - text_width(nxt, font=FONT_UI)) // 2, H//2 + 30, nxt, C_WHITE, font=FONT_UI)
            return

        self._draw_game()

    def _draw_game(self):
        frame = pyxel.frame_count
        cam_off_x = int(pyxel.rndf(-self.shake, self.shake)) if self.shake > 0 else 0
        cam_off_y = int(pyxel.rndf(-self.shake, self.shake)) if self.shake > 0 else 0

        # Camera
        cx = self.cam_x + cam_off_x

        # Background
        self.level.draw_bg(cx, frame)

        # Apply camera offset
        pyxel.camera(cam_off_x, cam_off_y)

        # Terrain
        self.level.draw_terrain(cx, frame)

        # Enemies
        self.level.draw_enemies(cx, frame)

        # Particles
        for pt in self.particles:
            pt.draw()

        # Boss
        if self.boss_triggered and self.boss.alive:
            self.boss.draw(cx)

        # Player
        col = WORLD_THEMES[self.world_idx]["ground"]
        self.player.draw(cx, col)

        pyxel.camera()

        # HUD
        draw_hud(self.player, self.world_idx, self.boss if self.boss_triggered else None, frame)

        # Boss incoming warning
        if self.boss_triggered and self.boss.alive and pyxel.frame_count % 40 < 20:
            if self.player.x < LEVEL_W - 350:
                warn = "!! BOSS !!"
                draw_text((W - text_width(warn, font=FONT_LG)) // 2, 36, warn, C_RED, glow=True, font=FONT_LG)

# ─── Entry ────────────────────────────────────────────────────────────────────
App()
