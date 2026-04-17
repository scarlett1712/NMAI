from collections import deque
from settings import WALL


def bfs(maze, start, goal):
    """Return list of (x,y) from start to goal (inclusive), or [] if unreachable."""
    queue = deque()
    queue.append((start, [start]))
    visited = {start}

    while queue:
        (cx, cy), path = queue.popleft()

        if (cx, cy) == goal:
            return path

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in visited:
                if 0 <= nx < maze.cols and 0 <= ny < maze.rows:
                    if maze.grid[ny][nx] != WALL:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), path + [(nx, ny)]))

    return []
