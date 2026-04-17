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


def draw_arrow(surf, start, end, color, width=6):
    pygame.draw.line(surf, color, start, end, width)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = math.atan2(dy, dx)
    arrow_len = 18
    arrow_angle = math.pi / 6
    left = (end[0] - arrow_len * math.cos(angle - arrow_angle),
            end[1] - arrow_len * math.sin(angle - arrow_angle))
    right = (end[0] - arrow_len * math.cos(angle + arrow_angle),
             end[1] - arrow_len * math.sin(angle + arrow_angle))
    pygame.draw.polygon(surf, color, [end, left, right])


# ======================================================================
#  Stars background
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
#  Glowing Star for Exit (luôn hiển thị)
# ======================================================================

def draw_exit_star(surf, x, y, t):
    """Ngôi sao phát sáng đẹp, mượt mà - luôn hiển thị rõ"""
    r = tile_rect(x, y)
    cx = r.centerx
    cy = r.centery
    base_size = TILE_W * 0.52   # Kích thước vừa phải

    # Pulse nhịp nhàng
    pulse = 0.85 + 0.15 * math.sin(t * 5.5)

    # Glow ngoài cùng (mờ, to)
    glow_surf = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    glow_size = int(base_size * 1.85 * pulse)
    points = []
    for i in range(8):
        ang = i * math.pi / 4 + t * 1.2
        rx = glow_size * (0.9 if i % 2 == 0 else 0.55)
        ry = glow_size * (0.55 if i % 2 == 0 else 0.9)
        px = cx + rx * math.cos(ang)
        py = cy + ry * math.sin(ang)
        points.append((px, py))
    pygame.draw.polygon(glow_surf, (*C_EXIT, 45), points)
    surf.blit(glow_surf, r.topleft)

    # Glow giữa (sáng hơn)
    glow_surf2 = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    glow_size2 = int(base_size * 1.35 * pulse)
    points2 = []
    for i in range(8):
        ang = i * math.pi / 4 - t * 0.8
        rx = glow_size2 * (0.85 if i % 2 == 0 else 0.6)
        ry = glow_size2 * (0.6 if i % 2 == 0 else 0.85)
        px = cx + rx * math.cos(ang)
        py = cy + ry * math.sin(ang)
        points2.append((px, py))
    pygame.draw.polygon(glow_surf2, (*C_EXIT, 90), points2)
    surf.blit(glow_surf2, r.topleft)

    # Ngôi sao chính (sáng nhất)
    star_size = int(base_size * pulse)
    star_points = []
    for i in range(8):
        ang = i * math.pi / 4
        length = star_size if i % 2 == 0 else star_size * 0.42
        px = cx + length * math.cos(ang)
        py = cy + length * math.sin(ang)
        star_points.append((px, py))

    pygame.draw.polygon(surf, C_EXIT, star_points)
    
    # Điểm sáng ở giữa ngôi sao
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), int(star_size * 0.28))

    # Tia sáng nhỏ ngẫu nhiên (tăng độ lung linh)
    for i in range(4):
        ang = t * 3 + i * 1.57
        length = star_size * 1.6
        tx = cx + length * math.cos(ang)
        ty = cy + length * math.sin(ang)
        pygame.draw.line(surf, (*C_EXIT, 120), (cx, cy), (tx, ty), 2)

# ======================================================================
#  Fog of war - Exit luôn hiển thị
# ======================================================================

def build_fog(player_x, player_y, visited, radius, exit_pos):
    fog = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    fog.fill((*C_FOG, 255))
    ex, ey = exit_pos

    for y in range(MAZE_ROWS):
        for x in range(MAZE_COLS):
            if (x, y) == (ex, ey):
                continue  # Exit không bị fog che

            dist = abs(x - player_x) + abs(y - player_y)
            r = tile_rect(x, y)

            if dist <= radius:
                fog.fill((0, 0, 0, 0), r)
            elif (x, y) in visited:
                fog.fill((*C_VISITED, 160), r)
            else:
                extra = max(0, dist - radius)
                alpha = min(255, 120 + extra * 35)
                fog.fill((*C_FOG, alpha), r)
    return fog


# ======================================================================
#  Draw maze
# ======================================================================

def draw_maze(surf, maze, player_x, player_y, visited, radius,
              player_path, opt_path, show_paths, t):
    for y in range(maze.rows):
        for x in range(maze.cols):
            dist = abs(x - player_x) + abs(y - player_y)
            visible = dist <= radius
            was_visited = (x, y) in visited
            is_exit = (x, y) == maze.exit

            if not visible and not was_visited and not is_exit:
                continue

            cell = maze.grid[y][x]
            r = tile_rect(x, y)

            if cell == WALL:
                pygame.draw.rect(surf, C_WALL, r)
            else:
                pygame.draw.rect(surf, C_FLOOR, r)

            if show_paths:
                if (x, y) in opt_path:
                    hl = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    hl.fill((*C_PATH_OPT, 80))
                    surf.blit(hl, r.topleft)
                elif (x, y) in player_path:
                    hl = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    hl.fill((*C_PATH_PLAYER, 50))
                    surf.blit(hl, r.topleft)

            if cell == EXIT:
                draw_exit_star(surf, x, y, t)
            elif cell == WATER:
                draw_water_tile(surf, x, y)
            elif cell == TELEPORT:
                draw_teleport_tile(surf, x, y)

    draw_wall_lines(surf, maze, player_x, player_y, visited, radius)


def draw_wall_lines(surf, maze, px, py, visited, radius):
    for y in range(maze.rows):
        for x in range(maze.cols):
            dist = abs(x - px) + abs(y - py)
            if dist > radius and (x, y) not in visited and (x, y) != maze.exit:
                continue
            if maze.grid[y][x] == WALL:
                r = tile_rect(x, y)
                for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx2, ny2 = x+dx, y+dy
                    if 0 <= nx2 < maze.cols and 0 <= ny2 < maze.rows and maze.grid[ny2][nx2] != WALL:
                        if dx == 1:
                            pygame.draw.line(surf, C_LINE, (r.right-1, r.top), (r.right-1, r.bottom), 1)
                        elif dx == -1:
                            pygame.draw.line(surf, C_LINE, (r.left, r.top), (r.left, r.bottom), 1)
                        elif dy == 1:
                            pygame.draw.line(surf, C_LINE, (r.left, r.bottom-1), (r.right, r.bottom-1), 1)
                        else:
                            pygame.draw.line(surf, C_LINE, (r.left, r.top), (r.right, r.top), 1)


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


def draw_player(surf, player, t):
    r = tile_rect(player.x, player.y)
    size = TILE_W - 8
    body = pygame.Rect(r.centerx - size//2, r.centery - size//2, size, size)
    pygame.draw.rect(surf, C_PLAYER, body)
    tip = (r.centerx, r.bottom - 1)
    left = (r.centerx - size//3, r.centery + size//4)
    right = (r.centerx + size//3, r.centery + size//4)
    pygame.draw.polygon(surf, C_PLAYER_GLOW, [left, right, tip])


def draw_guard(surf, guard, player_x, player_y, t):
    dist = abs(guard.x - player_x) + abs(guard.y - player_y)
    if dist > VISION_RADIUS + 2:
        return
    r = tile_rect(guard.x, guard.y)
    color = C_GUARD_CHASE if guard.state == Guard.CHASE else C_GUARD
    size = TILE_W - 10
    body = pygame.Rect(r.centerx - size//2, r.centery - size//2, size, size)
    pygame.draw.rect(surf, color, body, 2)
    pygame.draw.line(surf, color, body.topleft, body.bottomright, 2)
    pygame.draw.line(surf, color, body.topright, body.bottomleft, 2)


# ======================================================================
#  HUD & Hint Button
# ======================================================================

def draw_hud(surf, player, elapsed, font_small):
    pad = 6
    texts = [f"Steps: {player.steps}", f"Time: {int(elapsed)}s"]
    x = pad
    y = pad
    for txt in texts:
        s = font_small.render(txt, True, C_TEXT_DIM)
        surf.blit(s, (x, y))
        x += s.get_width() + 20


def draw_guard_state_hud(surf, guards, font_small):
    if any(g.state == Guard.CHASE for g in guards):
        s = font_small.render("! GUARD ALERT !", True, C_GUARD_CHASE)
        surf.blit(s, (SCREEN_W - s.get_width() - 8, 8))


def draw_hint_button(surf, hint_btn, cooldown_remaining, font_small):
    color = (80, 80, 80) if cooldown_remaining > 0 else C_PATH_OPT
    pygame.draw.circle(surf, color, hint_btn.center, 28)
    pygame.draw.circle(surf, (255,255,255), hint_btn.center, 28, 3)
    bulb = font_small.render("💡", True, (255, 255, 200))
    surf.blit(bulb, bulb.get_rect(center=hint_btn.center))


# ======================================================================
#  Flash & Win screen
# ======================================================================

def draw_flash(surf, color, alpha):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((*color, alpha))
    surf.blit(overlay, (0, 0))


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
#  MENU + HƯỚNG DẪN
# ======================================================================

def draw_menu(surf, stars, t, play_btn, instr_btn, show_instructions, font_large, font_med, font_small):
    surf.fill(C_BG)
    draw_stars(surf, stars, t)

    draw_text_centered(surf, TITLE, font_large, C_TEXT, SCREEN_H // 4 - 40)

    pygame.draw.rect(surf, C_PATH_OPT, play_btn, border_radius=12)
    play_txt = font_med.render("CHƠI", True, (18, 10, 8))
    surf.blit(play_txt, play_txt.get_rect(center=play_btn.center))

    pygame.draw.rect(surf, C_TELEPORT, instr_btn, border_radius=12)
    instr_txt = font_med.render("HƯỚNG DẪN", True, (18, 10, 8))
    surf.blit(instr_txt, instr_txt.get_rect(center=instr_btn.center))

    if show_instructions:
        popup_w, popup_h = 650, 480
        popup = pygame.Rect(SCREEN_W // 2 - popup_w//2, SCREEN_H // 2 - popup_h//2, popup_w, popup_h)
        pygame.draw.rect(surf, (25, 20, 18), popup, border_radius=16)
        pygame.draw.rect(surf, C_LINE, popup, 6, border_radius=16)

        title_surf = font_med.render("HƯỚNG DẪN", True, C_EXIT)
        surf.blit(title_surf, (popup.centerx - title_surf.get_width()//2, popup.top + 28))

        lines = [
            "ĐIỀU KHIỂN:", "   WASD / ↑↓←→ : Di chuyển", "   R             : Tạo map mới / chơi lại", "",
            "MỤC TIÊU:", "   Đến Exit (ngôi sao sáng) mà không bị bắt!", "",
            "CÁC YẾU TỐ:",
            "   • Bẫy nước (elip xanh): Rơi vào → reset về Start",
            "   • Cổng teleport (vòng tím): Dịch chuyển ngay",
            "   • Lính canh (X đỏ): Thấy bạn sẽ đuổi theo", "",
            "Fog of war: Tầm nhìn chỉ 3 ô, mờ dần ra xa.",
            "Phát sáng quanh nhân vật — tránh lính canh thông minh!",
        ]
        y = popup.top + 95
        for line in lines:
            color = (240, 230, 210) if "Fog of war" in line or "Phát sáng" in line else C_TEXT_DIM
            txt_surf = font_small.render(line, True, color)
            surf.blit(txt_surf, (popup.left + 50, y))
            y += 29

        close_rect = pygame.Rect(popup.right - 52, popup.top + 20, 38, 38)
        pygame.draw.circle(surf, C_GUARD_CHASE, close_rect.center, 19)
        close_txt = font_small.render("×", True, (255, 255, 255))
        surf.blit(close_txt, close_txt.get_rect(center=close_rect.center))

    if not show_instructions:
        hint = font_small.render("Nhấn vào nút CHƠI hoặc HƯỚNG DẪN", True, C_TEXT_DIM)
        surf.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 45))


# ======================================================================
#  Game Class
# ======================================================================

STATE_PLAY = 'play'
STATE_DEAD_WATER = 'dead_water'
STATE_DEAD_GUARD = 'dead_guard'
STATE_TELEPORTING = 'teleporting'
STATE_WIN = 'win'
STATE_MENU = 'menu'


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self.font_large = pygame.font.SysFont('consolas', 48, bold=True)
        self.font_med   = pygame.font.SysFont('consolas', 28, bold=True)
        self.font_small = pygame.font.SysFont('consolas', 19)

        self.stars = generate_stars(100)

        self.play_btn = pygame.Rect(SCREEN_W // 2 - 130, SCREEN_H // 2 - 30, 260, 75)
        self.instr_btn = pygame.Rect(SCREEN_W // 2 - 130, SCREEN_H // 2 + 70, 260, 75)
        self.hint_btn = pygame.Rect(SCREEN_W - 80, 25, 56, 56)

        self.state = STATE_MENU
        self.show_instructions = False

        # Hint system
        self.hint_path = []
        self.hint_timer = 0.0
        self.hint_cooldown = 0.0

    def _new_game(self):
        self.maze = Maze()
        sx, sy = self.maze.start
        self.player = Player(sx, sy)
        self.guards = [Guard(gx, gy, self.maze) for gx, gy in self.maze.guard_starts]
        
        self.state = STATE_PLAY
        self.start_time = time.time()
        self.elapsed = 0.0
        self.flash_timer = 0
        self.flash_color = C_WATER
        self.win_alpha = 0
        self.opt_path = []
        self.opt_path_set = set()
        self._teleport_dest = None

        # Reset hint
        self.hint_path = []
        self.hint_timer = 0.0
        self.hint_cooldown = 0.0

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            t = pygame.time.get_ticks() / 1000.0
            self._handle_events(dt)
            self._update(dt, t)
            self._draw(t)
            pygame.display.flip()

    def _handle_events(self, dt):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # Cho phép bấm R ở mọi trạng thái để restart
                if event.key == pygame.K_r:
                    self._new_game()
                    return

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

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if self.state == STATE_MENU:
                    if self.play_btn.collidepoint(mx, my):
                        self._new_game()
                    elif self.instr_btn.collidepoint(mx, my):
                        self.show_instructions = True
                    elif self.show_instructions:
                        popup = pygame.Rect(SCREEN_W // 2 - 325, SCREEN_H // 2 - 240, 650, 520)
                        close_rect = pygame.Rect(popup.right - 55, popup.top + 22, 38, 38)
                        if close_rect.collidepoint(mx, my):
                            self.show_instructions = False
                elif self.state == STATE_PLAY:
                    if self.hint_btn.collidepoint(mx, my) and self.hint_cooldown <= 0:
                        self._show_hint()

    def _show_hint(self):
        self.hint_path = bfs(self.maze, (self.player.x, self.player.y), self.maze.exit)
        self.hint_timer = 7.0
        self.hint_cooldown = 45.0

    def _on_player_move(self):
        px, py = self.player.x, self.player.y
        cell = self.maze.cell(px, py)

        if cell == TELEPORT:
            dest = self.maze.teleport_partner((px, py))
            if dest:
                self.state = STATE_TELEPORTING
                self._teleport_dest = dest
                self.flash_timer = 0.4
                self.flash_color = C_TELEPORT
                return
        if cell == WATER:
            self.state = STATE_DEAD_WATER
            self.flash_timer = 1.2
            self.flash_color = C_WATER
            return
        if cell == EXIT:
            self._trigger_win()
            return

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

    def _update(self, dt, t):
        if self.state == STATE_PLAY:
            self.elapsed = time.time() - self.start_time

            for g in self.guards:
                g.update(self.player.x, self.player.y)
                if g.catches(self.player.x, self.player.y):
                    self._trigger_guard_death()
                    break

            if self.hint_timer > 0:
                self.hint_timer -= dt
            if self.hint_cooldown > 0:
                self.hint_cooldown -= dt

        elif self.state in (STATE_DEAD_WATER, STATE_DEAD_GUARD, STATE_TELEPORTING):
            self.flash_timer -= dt
            if self.flash_timer <= 0:
                if self.state == STATE_TELEPORTING and self._teleport_dest:
                    dx, dy = self._teleport_dest
                    self.player.teleport_to(dx, dy)
                    self._teleport_dest = None
                    if self.maze.cell(dx, dy) == EXIT:
                        self._trigger_win()
                        return
                else:
                    self.player.reset_to_start()
                self.state = STATE_PLAY

        elif self.state == STATE_WIN:
            if self.win_alpha < 255:
                self.win_alpha = min(255, self.win_alpha + 3)

    def _draw(self, t):
        if self.state == STATE_MENU:
            draw_menu(self.screen, self.stars, t, self.play_btn, self.instr_btn,
                      self.show_instructions, self.font_large, self.font_med, self.font_small)
            return

        self.screen.fill(C_BG)
        draw_stars(self.screen, self.stars, t)

        show_paths = (self.state == STATE_WIN)
        player_path_set = set(self.player.path) if show_paths else set()

        # Vẽ mê cung + ngôi sao Exit
        draw_maze(self.screen, self.maze, self.player.x, self.player.y,
                  self.player.visited, VISION_RADIUS,
                  player_path_set, self.opt_path_set, show_paths, t)

        for g in self.guards:
            draw_guard(self.screen, g, self.player.x, self.player.y, t)
        draw_player(self.screen, self.player, t)

        # Fog of war
        fog = build_fog(self.player.x, self.player.y, self.player.visited, VISION_RADIUS, self.maze.exit)
        self.screen.blit(fog, (0, 0))

        # Vẽ mũi tên gợi ý (nếu đang active)
        if self.hint_timer > 0 and len(self.hint_path) > 1:
            for i in range(len(self.hint_path) - 1):
                x1, y1 = self.hint_path[i]
                x2, y2 = self.hint_path[i + 1]
                start = (x1 * TILE_W + TILE_W // 2, y1 * TILE_H + TILE_H // 2)
                end = (x2 * TILE_W + TILE_W // 2, y2 * TILE_H + TILE_H // 2)
                draw_arrow(self.screen, start, end, (100, 255, 140), width=5)

        # HUD
        if self.state != STATE_WIN:
            draw_hud(self.screen, self.player, self.elapsed, self.font_small)
            draw_guard_state_hud(self.screen, self.guards, self.font_small)
            draw_hint_button(self.screen, self.hint_btn, self.hint_cooldown, self.font_small)

        # Flash khi chết hoặc teleport
        if self.state in (STATE_DEAD_WATER, STATE_DEAD_GUARD, STATE_TELEPORTING):
            alpha = int(min(180, self.flash_timer * 200))
            draw_flash(self.screen, self.flash_color, alpha)

            if self.state == STATE_DEAD_WATER:
                draw_text_centered(self.screen, "DROWNED", self.font_large, C_WATER, SCREEN_H // 2 - 30)
                draw_text_centered(self.screen, "back to start...", self.font_small, C_TEXT_DIM, SCREEN_H // 2 + 30)
            elif self.state == STATE_DEAD_GUARD:
                draw_text_centered(self.screen, "CAUGHT", self.font_large, C_GUARD_CHASE, SCREEN_H // 2 - 30)
                draw_text_centered(self.screen, "back to start...", self.font_small, C_TEXT_DIM, SCREEN_H // 2 + 30)
            elif self.state == STATE_TELEPORTING:
                draw_text_centered(self.screen, "TELEPORTING...", self.font_med, C_TELEPORT, SCREEN_H // 2 - 20)

        # Win screen
        if self.state == STATE_WIN:
            draw_win_screen(self.screen, self.player, self.elapsed, self.opt_path,
                            self.font_large, self.font_med, self.font_small, self.win_alpha)

            # Vẽ đường đi ngay cả khi đang ở win screen
            # (đã được xử lý trong draw_maze)

        # Hint dưới cùng
        bottom_hint = self.font_small.render("WASD / Arrow keys   R = map mới", True, C_TEXT_DIM)
        self.screen.blit(bottom_hint, (SCREEN_W // 2 - bottom_hint.get_width() // 2, SCREEN_H - 22))


if __name__ == '__main__':
    Game().run()