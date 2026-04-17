import random
from settings import GUARD_VISION, GUARD_SPEED_FRAMES, WALL


class Guard:
    PATROL = 'PATROL'
    CHASE  = 'CHASE'
    RETURN = 'RETURN'

    def __init__(self, x, y, maze):
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.maze = maze
        self.state = self.PATROL
        self._frame_counter = 0
        self._patrol_dir = self._random_dir()
        self._patrol_stuck = 0

    # ------------------------------------------------------------------ #
    def update(self, player_x, player_y):
        self._frame_counter += 1
        if self._frame_counter < GUARD_SPEED_FRAMES:
            return
        self._frame_counter = 0

        sees = self._can_see(player_x, player_y)

        if sees:
            self.state = self.CHASE
        elif self.state == self.CHASE:
            self.state = self.RETURN

        if self.state == self.CHASE:
            self._move_toward(player_x, player_y)
        elif self.state == self.RETURN:
            self._move_toward(self.start_x, self.start_y)
            if self.x == self.start_x and self.y == self.start_y:
                self.state = self.PATROL
        else:
            self._patrol()

    def _can_see(self, px, py):
        dist = abs(self.x - px) + abs(self.y - py)
        return dist <= GUARD_VISION

    def _move_toward(self, tx, ty):
        # Prefer axis that reduces distance most; fallback to BFS step
        options = []
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = self.x + dx, self.y + dy
            if self.maze.is_walkable(nx, ny):
                dist = abs(nx - tx) + abs(ny - ty)
                options.append((dist, dx, dy))
        if options:
            options.sort()
            _, dx, dy = options[0]
            self.x += dx
            self.y += dy

    def _patrol(self):
        dx, dy = self._patrol_dir
        nx, ny = self.x + dx, self.y + dy
        if self.maze.is_walkable(nx, ny):
            self.x = nx
            self.y = ny
            self._patrol_stuck = 0
        else:
            self._patrol_stuck += 1
            if self._patrol_stuck > 2:
                self._patrol_dir = self._random_dir()
                self._patrol_stuck = 0

    def _random_dir(self):
        return random.choice([(1,0),(-1,0),(0,1),(0,-1)])

    def catches(self, player_x, player_y):
        return self.x == player_x and self.y == player_y

    @property
    def color_key(self):
        return self.state
