import random
from settings import *
from pathfinding import bfs   # ← thêm để tính safe path


class Maze:
    def __init__(self):
        self.cols = MAZE_COLS
        self.rows = MAZE_ROWS
        self.grid = [[WALL] * self.cols for _ in range(self.rows)]
        self.start = (1, 1)
        self.exit = (self.cols - 2, self.rows - 2)
        self.water_cells = []
        self.teleport_pairs = []   # list of [(ax,ay),(bx,by)]
        self.guard_starts = []

        self._generate()
        self._place_elements()

    # ------------------------------------------------------------------ #
    #  Generation                                                          #
    # ------------------------------------------------------------------ #
    def _generate(self):
        stack = [self.start]
        sx, sy = self.start
        self.grid[sy][sx] = FLOOR

        while stack:
            cx, cy = stack[-1]
            neighbours = self._unvisited_neighbours(cx, cy)
            if neighbours:
                nx, ny = random.choice(neighbours)
                # carve wall between
                wx = cx + (nx - cx) // 2
                wy = cy + (ny - cy) // 2
                self.grid[wy][wx] = FLOOR
                self.grid[ny][nx] = FLOOR
                stack.append((nx, ny))
            else:
                stack.pop()

        self.grid[sy][sx] = START
        ex, ey = self.exit
        self.grid[ey][ex] = EXIT

    def _unvisited_neighbours(self, x, y):
        result = []
        for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            nx, ny = x + dx, y + dy
            if 0 < nx < self.cols - 1 and 0 < ny < self.rows - 1:
                if self.grid[ny][nx] == WALL:
                    result.append((nx, ny))
        return result

    # ------------------------------------------------------------------ #
    #  Element placement                                                   #
    # ------------------------------------------------------------------ #
    def _free_floor_cells(self, exclude=None):
        exclude = exclude or set()
        cells = []
        for y in range(self.rows):
            for x in range(self.cols):
                if self.grid[y][x] == FLOOR and (x, y) not in exclude:
                    cells.append((x, y))
        return cells

    def _place_elements(self):
        reserved = {self.start, self.exit}

        # FIX LOGIC: random bẫy nước + teleport nhưng KO ĐƯỢC CHẶN HẾT ĐƯỜNG ĐI
        # Tính đường ngắn nhất trước, sau đó loại các ô trên đường này ra khỏi candidates của WATER
        # → luôn tồn tại ít nhất 1 đường an toàn (không rơi bẫy nước)
        opt_path = bfs(self, self.start, self.exit)
        safe_cells = set(opt_path) if opt_path else set()

        # --- water traps ---
        candidates = self._free_floor_cells(reserved)
        candidates = [c for c in candidates if c not in safe_cells]   # ← FIX quan trọng
        random.shuffle(candidates)
        for _ in range(NUM_WATER_TRAPS):
            if candidates:
                wx, wy = candidates.pop()
                self.grid[wy][wx] = WATER
                self.water_cells.append((wx, wy))
                reserved.add((wx, wy))

        # --- teleports (pairs) ---
        for _ in range(NUM_TELEPORT_PAIRS):
            candidates = self._free_floor_cells(reserved)
            if len(candidates) >= 2:
                random.shuffle(candidates)
                a = candidates.pop()
                b = candidates.pop()
                ax, ay = a
                bx, by = b
                self.grid[ay][ax] = TELEPORT
                self.grid[by][bx] = TELEPORT
                self.teleport_pairs.append([a, b])
                reserved.add(a)
                reserved.add(b)

        # --- guards (placed away from start) ---
        candidates = self._free_floor_cells(reserved)
        # prefer cells far from start
        sx, sy = self.start
        candidates.sort(key=lambda c: -abs(c[0] - sx) - abs(c[1] - sy))
        for _ in range(NUM_GUARDS):
            if candidates:
                gx, gy = candidates.pop(0)
                self.guard_starts.append((gx, gy))
                reserved.add((gx, gy))

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #
    def teleport_partner(self, pos):
        """Return the other end of a teleport, or None."""
        for pair in self.teleport_pairs:
            if pos == pair[0]:
                return pair[1]
            if pos == pair[1]:
                return pair[0]
        return None

    def is_walkable(self, x, y):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            return self.grid[y][x] != WALL
        return False

    def cell(self, x, y):
        return self.grid[y][x]