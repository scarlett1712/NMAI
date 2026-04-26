from collections import deque
from settings import WALL, WATER, TELEPORT


def bfs(maze, start, goal, can_teleport=True):
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
            if 0 <= nx < maze.cols and 0 <= ny < maze.rows:
                cell = maze.grid[ny][nx]
                
                # 1. Bỏ qua tường và nước (đây là những ô không thể/không nên đi vào)
                if cell == WALL or cell == WATER:
                    continue
                
                target_pos = (nx, ny)
                target_path = path + [target_pos]
                
                # 2. Xử lý cổng dịch chuyển (chỉ áp dụng nếu can_teleport là True)
                if can_teleport and cell == TELEPORT:
                    # Nếu là cổng dịch chuyển, nó sẽ tự động đẩy người chơi sang đầu bên kia
                    dest = maze.teleport_partner(target_pos)
                    if dest:
                        target_pos = dest
                        target_path = target_path + [target_pos]

                # 3. Kiểm tra xem vị trí đích này đã được duyệt chưa
                if target_pos not in visited:
                    visited.add(target_pos)
                    queue.append((target_pos, target_path))

    return []
