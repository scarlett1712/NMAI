import pygame
import sys
import time
import random
import math

from settings import *
from maze import Maze
from player import Player
from guard import Guard
from pathfinding import bfs


# ======================================================================
#  Utility helpers
# ======================================================================

def tile_rect(x, y):
    return pygame.Rect(x * TILE_W, y * TILE_H, TILE_W, TILE_H)


def draw_text_centered(surf, text, font, color, cy, alpha=255):
    s = font.render(text, True, color)
    s.set_alpha(alpha)
    surf.blit(s, (SCREEN_W // 2 - s.get_width() // 2, cy))


def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ======================================================================
#  Stars background (static, generated once)
# ======================================================================

def generate_stars(n=120):
    return [(random.randint(0, SCREEN_W), random.randint(0, SCREEN_H),
             random.randint(1, 2), random.random()) for _ in range(n)]


def draw_stars(surf, stars, t):
    for sx, sy, r, phase in stars:
        alpha = int(80 + 60 * math.sin(t * 0.8 + phase * 6.28))
        c = (min(255, C_STAR[0]), min(255, C_STAR[1]), min(255, C_STAR[2]))
        star_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(star_surf, (*c, alpha), (r, r), r)
        surf.blit(star_surf, (sx - r, sy - r))


# ======================================================================
#  Fog of war surface
# ======================================================================

def build_fog(player_x, player_y, visited, radius):
    fog = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    fog.fill((*C_FOG, 255))

    for y in range(MAZE_ROWS):
        for x in range(MAZE_COLS):
            dist = abs(x - player_x) + abs(y - player_y)
            r = tile_rect(x, y)
            if dist <= radius:
                # fully visible
                fog.fill((0, 0, 0, 0), r)
            elif (x, y) in visited:
                # faint visited
                fog.fill((*C_VISITED, 200), r)
            # else: fully opaque fog (default)
    return fog


# ======================================================================
#  Draw maze tiles
# ======================================================================

def draw_maze(surf, maze, player_x, player_y, visited, radius,
              player_path, opt_path, show_paths):
    for y in range(maze.rows):
        for x in range(maze.cols):
            dist = abs(x - player_x) + abs(y - player_y)
            visible = dist <= radius
            was_visited = (x, y) in visited

            if not visible and not was_visited:
                continue

            cell = maze.grid[y][x]
            r = tile_rect(x, y)

            # Base tile color
            if cell == WALL:
                pygame.draw.rect(surf, C_WALL, r)
            else:
                pygame.draw.rect(surf, C_FLOOR, r)

            # Path highlights (shown on win screen)
            if show_paths:
                if (x, y) in opt_path:
                    hl = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    hl.fill((*C_PATH_OPT, 80))
                    surf.blit(hl, r.topleft)
                elif (x, y) in player_path:
                    hl = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    hl.fill((*C_PATH_PLAYER, 50))
                    surf.blit(hl, r.topleft)

            # Special tiles
            if cell == EXIT:
                draw_exit_tile(surf, x, y)
            elif cell == WATER:
                draw_water_tile(surf, x, y)
            elif cell == TELEPORT:
                draw_teleport_tile(surf, x, y)
            elif cell in (START,):
                # draw faint S marker
                pass

    # Draw thin grid lines for wall borders
    draw_wall_lines(surf, maze, player_x, player_y, visited, radius)


def draw_wall_lines(surf, maze, px, py, visited, radius):
    line_color = (*C_LINE, 40)
    for y in range(maze.rows):
        for x in range(maze.cols):
            dist = abs(x - px) + abs(y - py)
            if dist > radius and (x, y) not in visited:
                continue
            if maze.grid[y][x] == WALL:
                # draw thin border on walkable neighbours
                r = tile_rect(x, y)
                for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx2, ny2 = x+dx, y+dy
                    if 0 <= nx2 < maze.cols and 0 <= ny2 < maze.rows:
                        if maze.grid[ny2][nx2] != WALL:
                            # draw line on the shared edge
                            if dx == 1:
                                pygame.draw.line(surf, C_LINE,
                                    (r.right-1, r.top), (r.right-1, r.bottom), 1)
                            elif dx == -1:
                                pygame.draw.line(surf, C_LINE,
                                    (r.left, r.top), (r.left, r.bottom), 1)
                            elif dy == 1:
                                pygame.draw.line(surf, C_LINE,
                                    (r.left, r.bottom-1), (r.right, r.bottom-1), 1)
                            else:
                                pygame.draw.line(surf, C_LINE,
                                    (r.left, r.top), (r.right, r.top), 1)


def draw_exit_tile(surf, x, y):
    r = tile_rect(x, y)
    size = min(TILE_W, TILE_H) - 8
    inner = pygame.Rect(r.centerx - size//2, r.centery - size//2, size, size)
    pygame.draw.rect(surf, C_EXIT, inner, 2)
    # pulsing inner dot drawn in main loop via time


def draw_water_tile(surf, x, y):
    r = tile_rect(x, y)
    t = pygame.time.get_ticks() / 1000
    wobble = int(3 * math.sin(t * 2 + x + y))
    s = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (*C_WATER, 180),
                        pygame.Rect(4, 4 + wobble, TILE_W - 8, TILE_H - 8))
    surf.blit(s, r.topleft)


def draw_teleport_tile(surf, x, y):
    r = tile_rect(x, y)
    t = pygame.time.get_ticks() / 1000
    pulse = int(3 * math.sin(t * 3 + x * 0.5 + y * 0.5))
    s = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    radius = TILE_W // 2 - 4 + pulse
    pygame.draw.circle(s, (*C_TELEPORT, 160),
                       (TILE_W // 2, TILE_H // 2), max(4, radius), 2)
    surf.blit(s, r.topleft)


# ======================================================================
#  Draw entities
# ======================================================================

def draw_player(surf, player, t):
    r = tile_rect(player.x, player.y)
    # square body (like screenshot)
    size = TILE_W - 8
    body = pygame.Rect(r.centerx - size//2, r.centery - size//2, size, size)
    pygame.draw.rect(surf, C_PLAYER, body)
    # small downward triangle indicator
    tip = (r.centerx, r.bottom - 1)
    left = (r.centerx - size//3, r.centery + size//4)
    right = (r.centerx + size//3, r.centery + size//4)
    pygame.draw.polygon(surf, C_PLAYER_GLOW, [left, right, tip])


def draw_guard(surf, guard, player_x, player_y, t):
    dist = abs(guard.x - player_x) + abs(guard.y - player_y)
    if dist > VISION_RADIUS + 2:
        return  # outside render vision

    r = tile_rect(guard.x, guard.y)
    color = C_GUARD_CHASE if guard.state == Guard.CHASE else C_GUARD
    size = TILE_W - 10
    body = pygame.Rect(r.centerx - size//2, r.centery - size//2, size, size)
    pygame.draw.rect(surf, color, body, 2)
    # X marker
    pygame.draw.line(surf, color, body.topleft, body.bottomright, 2)
    pygame.draw.line(surf, color, body.topright, body.bottomleft, 2)


def draw_exit_pulse(surf, maze, t):
    ex, ey = maze.exit
    r = tile_rect(ex, ey)
    pulse = 0.5 + 0.5 * math.sin(t * 3)
    alpha = int(80 + 120 * pulse)
    glow = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    glow.fill((*C_EXIT, alpha))
    surf.blit(glow, r.topleft)


# ======================================================================
#  HUD
# ======================================================================

def draw_hud(surf, player, elapsed, font_small):
    pad = 6
    texts = [
        f"Steps: {player.steps}",
        f"Time: {int(elapsed)}s",
    ]
    x = pad
    y = pad
    for txt in texts:
        s = font_small.render(txt, True, C_TEXT_DIM)
        surf.blit(s, (x, y))
        x += s.get_width() + 20


def draw_guard_state_hud(surf, guards, player_x, player_y, font_small):
    """Show CHASE warning near top-right when guard sees player."""
    chasing = any(g.state == Guard.CHASE for g in guards)
    if chasing:
        s = font_small.render("! GUARD ALERT !", True, C_GUARD_CHASE)
        surf.blit(s, (SCREEN_W - s.get_width() - 8, 8))


# ======================================================================
#  Death / Teleport flash overlay
# ======================================================================

def draw_flash(surf, color, alpha):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((*color, alpha))
    surf.blit(overlay, (0, 0))


# ======================================================================
#  Win screen
# ======================================================================

def draw_win_screen(surf, player, elapsed, opt_path, font_large, font_med, font_small, alpha):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((*C_OVERLAY, min(220, alpha)))
    surf.blit(overlay, (0, 0))

    cy = SCREEN_H // 2 - 120
    draw_text_centered(surf, "YOU ESCAPED", font_large, C_EXIT, cy, alpha)
    cy += 70
    draw_text_centered(surf, f"Your steps : {player.steps}", font_med, C_TEXT, cy, alpha)
    cy += 40
    opt = len(opt_path) - 1 if opt_path else 0
    draw_text_centered(surf, f"Best possible : {opt}", font_med, C_PATH_OPT, cy, alpha)
    cy += 40
    draw_text_centered(surf, f"Time : {elapsed:.1f}s", font_med, C_TEXT, cy, alpha)
    cy += 50
    efficiency = (opt / player.steps * 100) if player.steps > 0 else 0
    eff_color = C_PATH_OPT if efficiency >= 80 else C_TEXT
    draw_text_centered(surf, f"Efficiency : {efficiency:.0f}%", font_med, eff_color, cy, alpha)
    cy += 60

    legend = font_small.render("  Green = optimal path    Red = your path", True, C_TEXT_DIM)
    legend.set_alpha(alpha)
    surf.blit(legend, (SCREEN_W // 2 - legend.get_width() // 2, cy))
    cy += 30
    draw_text_centered(surf, "Press R to play again", font_small, C_TEXT_DIM, cy, alpha)


# ======================================================================
#  Game state
# ======================================================================

STATE_PLAY = 'play'
STATE_DEAD_WATER = 'dead_water'
STATE_DEAD_GUARD = 'dead_guard'
STATE_TELEPORTING = 'teleporting'
STATE_WIN = 'win'


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self.font_large = pygame.font.SysFont('consolas', 48, bold=True)
        self.font_med   = pygame.font.SysFont('consolas', 28)
        self.font_small = pygame.font.SysFont('consolas', 18)

        self.stars = generate_stars(100)
        self._new_game()

    def _new_game(self):
        self.maze = Maze()
        sx, sy = self.maze.start
        self.player = Player(sx, sy)
        self.guards = [Guard(gx, gy, self.maze)
                       for gx, gy in self.maze.guard_starts]
        self.state = STATE_PLAY
        self.start_time = time.time()
        self.elapsed = 0.0
        self.flash_timer = 0
        self.flash_color = C_WATER
        self.win_alpha = 0
        self.opt_path = []
        self.opt_path_set = set()

        # Move queue for smooth input
        self._move_cooldown = 0
        self._teleport_dest = None

    # ------------------------------------------------------------------ #
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            t = pygame.time.get_ticks() / 1000
            self._handle_events()
            self._update(t)
            self._draw(t)
            pygame.display.flip()

    # ------------------------------------------------------------------ #
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._new_game()
                if self.state == STATE_PLAY:
                    moved = False
                    if event.key in (pygame.K_w, pygame.K_UP):
                        moved = self.player.try_move(0, -1, self.maze)
                    elif event.key in (pygame.K_s, pygame.K_DOWN):
                        moved = self.player.try_move(0, 1, self.maze)
                    elif event.key in (pygame.K_a, pygame.K_LEFT):
                        moved = self.player.try_move(-1, 0, self.maze)
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        moved = self.player.try_move(1, 0, self.maze)
                    if moved:
                        self._on_player_move()

    def _on_player_move(self):
        px, py = self.player.x, self.player.y
        cell = self.maze.cell(px, py)

        # Check teleport
        if cell == TELEPORT:
            dest = self.maze.teleport_partner((px, py))
            if dest:
                self.state = STATE_TELEPORTING
                self._teleport_dest = dest
                self.flash_timer = 0.4
                self.flash_color = C_TELEPORT
                return

        # Check water
        if cell == WATER:
            self.state = STATE_DEAD_WATER
            self.flash_timer = 1.2
            self.flash_color = C_WATER
            return

        # Check exit
        if cell == EXIT:
            self._trigger_win()
            return

        # Check guard collision after moving
        for g in self.guards:
            if g.catches(px, py):
                self._trigger_guard_death()
                return

    def _trigger_win(self):
        self.state = STATE_WIN
        self.elapsed = time.time() - self.start_time
        self.opt_path = bfs(self.maze, self.maze.start, self.maze.exit)
        self.opt_path_set = set(self.opt_path)

    def _trigger_guard_death(self):
        self.state = STATE_DEAD_GUARD
        self.flash_timer = 1.0
        self.flash_color = C_GUARD_CHASE

    # ------------------------------------------------------------------ #
    def _update(self, t):
        if self.state == STATE_PLAY:
            self.elapsed = time.time() - self.start_time
            for g in self.guards:
                g.update(self.player.x, self.player.y)
                if g.catches(self.player.x, self.player.y):
                    self._trigger_guard_death()
                    break

        elif self.state in (STATE_DEAD_WATER, STATE_DEAD_GUARD, STATE_TELEPORTING):
            self.flash_timer -= 1 / FPS
            if self.flash_timer <= 0:
                if self.state == STATE_TELEPORTING and self._teleport_dest:
                    dx, dy = self._teleport_dest
                    self.player.teleport_to(dx, dy)
                    self._teleport_dest = None
                    # Check if landed on exit
                    if self.maze.cell(dx, dy) == EXIT:
                        self._trigger_win()
                        return
                else:
                    self.player.reset_to_start()
                self.state = STATE_PLAY

        elif self.state == STATE_WIN:
            if self.win_alpha < 255:
                self.win_alpha = min(255, self.win_alpha + 3)

    # ------------------------------------------------------------------ #
    def _draw(self, t):
        self.screen.fill(C_BG)
        draw_stars(self.screen, self.stars, t)

        show_paths = self.state == STATE_WIN
        player_path_set = set(self.player.path) if show_paths else set()

        draw_maze(self.screen, self.maze,
                  self.player.x, self.player.y,
                  self.player.visited, VISION_RADIUS,
                  player_path_set, self.opt_path_set, show_paths)

        draw_exit_pulse(self.screen, self.maze, t)

        for g in self.guards:
            draw_guard(self.screen, g, self.player.x, self.player.y, t)

        draw_player(self.screen, self.player, t)

        # Fog of war
        fog = build_fog(self.player.x, self.player.y, self.player.visited, VISION_RADIUS)
        self.screen.blit(fog, (0, 0))

        # HUD (drawn above fog)
        if self.state != STATE_WIN:
            draw_hud(self.screen, self.player, self.elapsed, self.font_small)
            draw_guard_state_hud(self.screen, self.guards,
                                 self.player.x, self.player.y, self.font_small)

        # Flash overlay
        if self.state in (STATE_DEAD_WATER, STATE_DEAD_GUARD, STATE_TELEPORTING):
            alpha = int(min(180, self.flash_timer * 200))
            draw_flash(self.screen, self.flash_color, alpha)

            # Show message
            if self.state == STATE_DEAD_WATER:
                draw_text_centered(self.screen, "DROWNED", self.font_large, C_WATER,
                                   SCREEN_H // 2 - 30)
                draw_text_centered(self.screen, "back to start...", self.font_small, C_TEXT_DIM,
                                   SCREEN_H // 2 + 30)
            elif self.state == STATE_DEAD_GUARD:
                draw_text_centered(self.screen, "CAUGHT", self.font_large, C_GUARD_CHASE,
                                   SCREEN_H // 2 - 30)
                draw_text_centered(self.screen, "back to start...", self.font_small, C_TEXT_DIM,
                                   SCREEN_H // 2 + 30)
            elif self.state == STATE_TELEPORTING:
                draw_text_centered(self.screen, "TELEPORTING...", self.font_med, C_TELEPORT,
                                   SCREEN_H // 2 - 20)

        if self.state == STATE_WIN:
            draw_win_screen(self.screen, self.player, self.elapsed,
                            self.opt_path, self.font_large, self.font_med,
                            self.font_small, self.win_alpha)

        # Controls hint (bottom)
        hint = self.font_small.render("WASD / Arrow keys to move   R = restart", True, C_TEXT_DIM)
        self.screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 22))


# ======================================================================
if __name__ == '__main__':
    Game().run()
