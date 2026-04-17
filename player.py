from settings import *


class Player:
    def __init__(self, start_x, start_y):
        self.start_x = start_x
        self.start_y = start_y
        self.x = start_x
        self.y = start_y
        self.path = [(start_x, start_y)]   # full traversal path
        self.steps = 0
        self.visited = {(start_x, start_y)}

    def try_move(self, dx, dy, maze):
        nx, ny = self.x + dx, self.y + dy
        if maze.is_walkable(nx, ny):
            self.x = nx
            self.y = ny
            self.steps += 1
            self.path.append((nx, ny))
            self.visited.add((nx, ny))
            return True
        return False

    def reset_to_start(self):
        self.x = self.start_x
        self.y = self.start_y
        self.path = [(self.start_x, self.start_y)]
        self.steps = 0
        self.visited = {(self.start_x, self.start_y)}

    def teleport_to(self, tx, ty):
        self.x = tx
        self.y = ty
        self.path.append((tx, ty))
        self.visited.add((tx, ty))
