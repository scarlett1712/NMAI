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
#  Exit marker — vẽ sau lớp fog: luôn sáng trên map mờ
# ======================================================================

def draw_exit_star_bright(surf, x, y):
    """Ngôi sao 5 cánh + quầng sáng tĩnh; gọi sau `blit(fog)` để không bị fog làm mờ."""
    r = tile_rect(x, y)
    cx, cy = r.centerx, r.centery
    glow = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    gcx, gcy = TILE_W // 2, TILE_H // 2
    rr = min(TILE_W, TILE_H)
    pygame.draw.circle(glow, (255, 255, 255, 55), (gcx, gcy), int(rr * 0.52))
    pygame.draw.circle(glow, (255, 255, 255, 95), (gcx, gcy), int(rr * 0.34))
    surf.blit(glow, r.topleft)

    outer = rr * 0.42
    inner = outer * 0.38
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * (math.pi / 5)
        rad = outer if i % 2 == 0 else inner
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    pygame.draw.polygon(surf, (255, 255, 255), pts)
    pygame.draw.polygon(surf, C_LINE, pts, 1)

# ======================================================================
#  Fog of war
# ======================================================================

def build_fog(player_x, player_y, visited, radius):
    fog = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    fog.fill((*C_FOG, 255))

    for y in range(MAZE_ROWS):
        for x in range(MAZE_COLS):
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

def _path_centers(path):
    return [(x * TILE_W + TILE_W // 2, y * TILE_H + TILE_H // 2) for x, y in path]


def draw_path_line(surf, path, color, width, alpha=255):
    if len(path) < 2:
        return
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    pts = _path_centers(path)
    pygame.draw.lines(layer, (*color, alpha), False, pts, width)
    surf.blit(layer, (0, 0))


def draw_maze(surf, maze, player_x, player_y, visited, radius,
              player_path, opt_path, show_paths, t, win_timer=0):
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

            if cell == EXIT:
                pass  # ngôi sao đích vẽ sau lớp fog (draw_exit_star_bright)
            elif cell == WATER:
                draw_water_tile(surf, x, y)
            elif cell == TELEPORT:
                draw_teleport_tile(surf, x, y)

    draw_wall_lines(surf, maze, player_x, player_y, visited, radius, show_paths)

    if show_paths:
        opt_path_set = set(opt_path)

        # Phase 1 (1.5s+): to trang ca o duong ngan nhat
        opt_alpha = min(255, int((win_timer - 1.5) / 0.6 * 255)) if win_timer >= 1.5 else 0
        if opt_alpha > 0:
            for oy in range(maze.rows):
                for ox in range(maze.cols):
                    if (ox, oy) in opt_path_set:
                        orl = tile_rect(ox, oy)
                        hl = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                        pulse = int(30 * math.sin(t * 5))
                        hl.fill((255, 255, 255, min(255, 160 + pulse)))
                        surf.blit(hl, orl.topleft)

        # Phase 2 (2.5s+): replay tung buoc player co cham xanh dau duong
        if win_timer >= 2.5 and len(player_path) >= 2:
            steps_shown = int((win_timer - 2.5) / 0.08) + 2
            steps_shown = min(steps_shown, len(player_path))
            visible_path = player_path[:steps_shown]
            draw_path_line(surf, visible_path, (60, 160, 255), 2, 220)
            if steps_shown < len(player_path):
                hx, hy = visible_path[-1]
                hr = tile_rect(hx, hy)
                dot_pulse = int(3 * math.sin(t * 10))
                pygame.draw.circle(surf, (140, 210, 255), hr.center, TILE_W // 4 + dot_pulse)
                pygame.draw.circle(surf, (220, 240, 255), hr.center, TILE_W // 8)


def draw_wall_lines(surf, maze, px, py, visited, radius, show_paths=False):
    for y in range(maze.rows):
        for x in range(maze.cols):
            dist = abs(x - px) + abs(y - py)
            if not show_paths and dist > radius and (x, y) not in visited and (x, y) != maze.exit:
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


def draw_bulb_icon(surf, center, size, color, lit=True):
    """Vẽ biểu tượng bóng đèn bằng vector để không phụ thuộc vào font emoji"""
    cx, cy = center
    # Phần kính (thân bóng đèn)
    r = int(size * 0.3)
    glass_color = color if lit else (70, 70, 70)
    # Vẽ phần đầu tròn
    pygame.draw.circle(surf, glass_color, (cx, cy - int(size * 0.1)), r)
    # Vẽ phần cổ bóng đèn (hình chữ nhật nhỏ nối với đế)
    neck_w = int(r * 1.1)
    neck_h = int(size * 0.15)
    neck_rect = pygame.Rect(cx - neck_w // 2, cy - int(size * 0.05), neck_w, neck_h)
    pygame.draw.rect(surf, glass_color, neck_rect)
    
    # Phần đế kim loại
    base_w = int(r * 0.9)
    base_h = int(size * 0.18)
    base_color = (130, 130, 130) if lit else (60, 60, 60)
    base_rect = pygame.Rect(cx - base_w // 2, cy + int(size * 0.1), base_w, base_h)
    pygame.draw.rect(surf, base_color, base_rect, border_radius=2)
    # Các sọc trên đế
    for i in range(2):
        y = base_rect.top + (i + 1) * (base_h // 3)
        pygame.draw.line(surf, (80, 80, 80), (base_rect.left + 2, y), (base_rect.right - 2, y), 1)
        
    # Sợi tóc bóng đèn (nếu đang sáng)
    if lit:
        eye_color = (255, 255, 255)
        # Vẽ một chút lấp lánh bên trong
        pygame.draw.circle(surf, eye_color, (cx - r//3, cy - size//6), 2)


def draw_hint_button(surf, hint_btn, cooldown_remaining, font_small, t, mouse_pos):
    cx, cy = hint_btn.center
    is_hover = hint_btn.collidepoint(mouse_pos)
    
    # Cooldown percentage
    cooldown_max = 45.0
    progress = max(0.0, min(1.0, cooldown_remaining / cooldown_max))
    
    base_r = max(12, min(hint_btn.width, hint_btn.height) // 2 - 3)
    if cooldown_remaining <= 0:
        # --- TRẠNG THÁI SẴN SÀNG (PREMIUM) ---
        pulse = 2.0 * math.sin(t * 8)
        hover_scale = 1.15 if is_hover else 1.0
        r = int(base_r * hover_scale + pulse)
        
        # 1. Hào quang Neon đa tầng (Multi-layered Glow)
        for i in range(3):
            glow_r = r + 6 + i * 8 + int(3 * math.sin(t * 4 + i))
            glow_alpha = int((50 - i * 15) * (1.3 if is_hover else 1.0))
            if glow_alpha > 0:
                g_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(g_surf, (*C_PATH_OPT, glow_alpha), (glow_r, glow_r), glow_r)
                surf.blit(g_surf, (cx - glow_r, cy - glow_r))
            
        # 2. Thân nút chính (Main Body)
        body_color = C_PATH_OPT if not is_hover else (100, 255, 170)
        pygame.draw.circle(surf, body_color, (cx, cy), r)
        
        # 3. Hiệu ứng gương kính (Specular Highlight)
        highlight_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        h_rect = pygame.Rect(int(r * 0.3), int(r * 0.2), int(r * 1.0), int(r * 0.6))
        pygame.draw.ellipse(highlight_surf, (255, 255, 255, 90), h_rect)
        surf.blit(highlight_surf, (cx - r, cy - r))
        
        # 4. Viền trắng bóng bẩy
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), r, 3)
        
        # 5. Vẽ Icon bóng đèn
        draw_bulb_icon(surf, (cx, cy), int(r * 1.1), (255, 255, 150), True)
    else:
        # --- TRẠNG THÁI HỒI CHIÊU (COOLDOWN) ---
        r = base_r
        # Thân nút tối
        pygame.draw.circle(surf, (35, 35, 35), (cx, cy), r)
        
        # Vòng track bên ngoài
        pygame.draw.circle(surf, (60, 60, 60), (cx, cy), r + 5, 2)
        
        # Vòng cung tiến trình (Glowing Arc)
        rect = pygame.Rect(cx - r - 5, cy - r - 5, (r + 5) * 2, (r + 5) * 2)
        start_angle = -math.pi / 2
        stop_angle = start_angle + (progress * 2 * math.pi)
        if progress > 0:
            # Hiệu ứng glow cho vòng cung
            pygame.draw.arc(surf, (100, 200, 255), rect, start_angle, stop_angle, 6)
            pygame.draw.arc(surf, (255, 255, 255), rect, start_angle, stop_angle, 2)
            
        # Icon bóng đèn mờ
        draw_bulb_icon(surf, (cx, cy), int(r * 1.0), (80, 80, 80), False)
        
        # Text đếm ngược (đưa xuống dưới nút để không che icon)
        cd_text = font_small.render(str(int(cooldown_remaining + 1)), True, (180, 180, 180))
        surf.blit(cd_text, cd_text.get_rect(center=(cx, cy + r + 18)))


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
    
    # Tính số bước tối ưu (chỉ đếm các bước di chuyển kề nhau, không đếm bước nhảy teleport)
    opt = 0
    if opt_path:
        for i in range(len(opt_path) - 1):
            x1, y1 = opt_path[i]
            x2, y2 = opt_path[i+1]
            if abs(x1 - x2) + abs(y1 - y2) == 1:
                opt += 1
                
    draw_text_centered(surf, f"Best possible : {opt}", font_med, C_PATH_OPT, cy, alpha)
    cy += 40
    draw_text_centered(surf, f"Time : {elapsed:.1f}s", font_med, C_TEXT, cy, alpha)
    cy += 50
    efficiency = (opt / player.steps * 100) if player.steps > 0 else 0
    eff_color = C_PATH_OPT if efficiency >= 80 else C_TEXT
    draw_text_centered(surf, f"Efficiency : {efficiency:.0f}%", font_med, eff_color, cy, alpha)
    cy += 60

    legend = font_small.render("  White = optimal path    Blue = your path", True, C_TEXT_DIM)
    legend.set_alpha(alpha)
    surf.blit(legend, (SCREEN_W // 2 - legend.get_width() // 2, cy))
    cy += 30
    draw_text_centered(surf, "Press R to play again", font_small, C_TEXT_DIM, cy, alpha)

# ======================================================================
#  PAUSE
# ======================================================================
def draw_pause_overlay(surf, game, font_med, font_small):
    # Lớp phủ mờ toàn màn hình
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    surf.blit(overlay, (0, 0))

    # Vẽ Popup Background
    pygame.draw.rect(surf, (30, 30, 35), game.pause_popup_rect, border_radius=15)
    pygame.draw.rect(surf, C_LINE, game.pause_popup_rect, 3, border_radius=15)
    
    draw_text_centered(surf, "PAUSED", game.font_large, (255, 255, 255), game.pause_popup_rect.top + 5) #sửa chữ đè nút

    # Các nút: Resume, Replay, Exit
    for btn, label, color in [
        (game.resume_btn, "RESUME", C_PATH_OPT),
        (game.replay_btn, "REPLAY", C_TELEPORT),
        (game.exit_btn, "EXIT", C_GUARD_CHASE)
    ]:
        pygame.draw.rect(surf, color, btn, border_radius=10)
        txt = font_small.render(label, True, (255, 255, 255))
        surf.blit(txt, txt.get_rect(center=btn.center))

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

    # FIX FRAME HƯỚNG DẪN BỊ ĐÈ NÉT (OVERDRAW)
    if show_instructions:
        if show_instructions:
            popup_w, popup_h = 650, 580
            popup_x = SCREEN_W // 2 - popup_w // 2
            popup_y = SCREEN_H // 2 - popup_h // 2
            
            # Tạo 1 Surface ảo có hỗ trợ Alpha để quản lý trọn vẹn UI Popup
            popup_surf = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
            pygame.draw.rect(popup_surf, (25, 20, 18, 250), (0, 0, popup_w, popup_h), border_radius=16)
            pygame.draw.rect(popup_surf, C_LINE, (0, 0, popup_w, popup_h), 6, border_radius=16)

            title_surf = font_med.render("HƯỚNG DẪN", True, C_EXIT)
            popup_surf.blit(title_surf, (popup_w // 2 - title_surf.get_width() // 2, 28))

            lines = [
            "ĐIỀU KHIỂN:", "   WASD / ↑↓←→ : Di chuyển", "   R             : Tạo map mới / chơi lại", "",
            "MỤC TIÊU:", "   Hãy tìm ngôi sao sáng mà không bị bắt!", "",
            "CÁC YẾU TỐ:",
            "   • Nước độc: Rơi vào → Ựa X",
            "   • Cổng teleport: Dịch chuyển đến cổng khác ",""
            "     (hãy nhớ cổng có 2 chiều)",""
            "   • Lính canh: Thấy là dí té khói", "",
            "Fog of war: Xung quanh tối tăm mịt mù",
            "Chỉ bạn là có hào quang nhân vật chính ",""
            "_Nếu bạn không thấy lính, nó cũng sẽ không thấy bạn!_",
        ]

            y = 95
            for line in lines:
                color = (240, 230, 210) if "hào quang" in line or "sáng" in line else C_TEXT_DIM
                txt_surf = font_small.render(line, True, color)
                # Tọa độ lúc này là tương đối so với popup_surf
                popup_surf.blit(txt_surf, (50, y))
                y += 29

            close_center = (popup_w - 33, 39)
            pygame.draw.circle(popup_surf, C_GUARD_CHASE, close_center, 19)
            close_txt = font_small.render("×", True, (255, 255, 255))
            popup_surf.blit(close_txt, close_txt.get_rect(center=close_center))

            # Blit trọn gói lên màn hình duy nhất 1 lần
            surf.blit(popup_surf, (popup_x, popup_y))
    # Gom toàn bộ hình khối vẽ nền và text vào một layer ảo popup_surf (có cờ pygame.SRCALPHA), 
    # sau đó mới dán (blit) layer này lên màn hình chính. Cách này ngăn lỗi trộn pixel (blend) của font 
    # Antialiasing với background, giúp frame nét và hỗ trợ transparency đẹp mắt hơn.

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
STATE_PAUSE = 'pause'

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.pause_btn = pygame.Rect(SCREEN_W - 106, 8, 40, 40)
        self.pause_popup_rect = pygame.Rect(SCREEN_W // 2 - 150, SCREEN_H // 2 - 125, 300, 250)

        self.font_large = pygame.font.SysFont('consolas', 48, bold=True)
        self.font_med   = pygame.font.SysFont('consolas', 28, bold=True)
        self.font_small = pygame.font.SysFont('consolas', 19)

        self.stars = generate_stars(100)

        self.play_btn = pygame.Rect(SCREEN_W // 2 - 130, SCREEN_H // 2 - 30, 260, 75)
        self.instr_btn = pygame.Rect(SCREEN_W // 2 - 130, SCREEN_H // 2 + 70, 260, 75)
        self.hint_btn = pygame.Rect(SCREEN_W - 58, 8, 40, 40)

        self.state = STATE_MENU
        self.show_instructions = False

        self.resume_btn = pygame.Rect(SCREEN_W // 2 - 100, SCREEN_H // 2 - 70, 200, 50)
        self.replay_btn = pygame.Rect(SCREEN_W // 2 - 100, SCREEN_H // 2 - 10, 200, 50)
        self.exit_btn   = pygame.Rect(SCREEN_W // 2 - 100, SCREEN_H // 2 + 50, 200, 50)

        # Hint system
        self.hint_path = []
        self.hint_timer = 0.0
        self.hint_cooldown = 0.0
        #Khai báo biến đếm giờ hiển thị cảnh báo
        self.cd_warn_timer = 0.0

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
        self.win_timer = 0.0
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
                
                # Phím tắt P để Pause/Resume
                if event.key == pygame.K_p and self.state in (STATE_PLAY, STATE_PAUSE):
                    if self.state == STATE_PLAY:
                        self.state = STATE_PAUSE
                        self.pause_start_time = time.time()
                    else:
                        self.start_time += (time.time() - self.pause_start_time)
                        self.state = STATE_PLAY

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
                        popup = pygame.Rect(SCREEN_W // 2 - 325, SCREEN_H // 2 - 290, 650, 580)
                        close_rect = pygame.Rect(popup.right - 55, popup.top + 22, 38, 38)
                        if close_rect.collidepoint(mx, my):
                            self.show_instructions = False
                #Sửa logic bắt event
                elif self.state == STATE_PLAY:
                    if self.pause_btn.collidepoint(mx, my):
                        self.state = STATE_PAUSE
                        self.pause_start_time = time.time()
                    elif self.hint_btn.collidepoint(mx, my):
                        if self.hint_cooldown <= 0:
                            self._show_hint()
                        else:
                            # Bấm lúc đang cooldown -> Set 2 giây để hiện thông báo cảnh báo
                            self.cd_warn_timer = 2.0 
                
                # Trạng thái Pause
                elif self.state == STATE_PAUSE:
                    if self.resume_btn.collidepoint(mx, my):
                        # Bù đắp thời gian đã trôi qua khi dừng
                        self.start_time += (time.time() - self.pause_start_time)
                        self.state = STATE_PLAY
                    elif self.replay_btn.collidepoint(mx, my):
                        # Gọi hàm chơi lại map hiện tại
                        self._replay_current_map()
                    elif self.exit_btn.collidepoint(mx, my):
                        self.state = STATE_MENU

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
        self.win_timer = 0.0
        self.win_alpha = 0

    def _trigger_guard_death(self):
        self.state = STATE_DEAD_GUARD
        self.flash_timer = 1.0
        self.flash_color = C_GUARD_CHASE

    def _replay_current_map(self):
            #Khởi tạo lại trạng thái game nhưng GIỮ NGUYÊN map hiện tại (self.maze)
            
            # 1. Đưa player về vạch xuất phát (dùng hàm reset có sẵn của class Player)
            self.player.reset_to_start()
            
            # 2. Hồi sinh/Đưa lính canh về đúng vị trí xuất phát ban đầu của map này
            self.guards = [Guard(gx, gy, self.maze) for gx, gy in self.maze.guard_starts]
            
            # 3. Reset lại toàn bộ thông số thời gian, trạng thái, hint
            self.state = STATE_PLAY
            self.start_time = time.time()
            self.elapsed = 0.0
            self.flash_timer = 0
            self.win_alpha = 0
            self.win_timer = 0.0
            self.opt_path = []
            self.opt_path_set = set()
            self._teleport_dest = None

            self.hint_path = []
            self.hint_timer = 0.0
            self.hint_cooldown = 0.0
            self.cd_warn_timer = 0.0

    def _update(self, dt, t):
        #Trừ hao thời gian của thông báo
        if self.state == STATE_PLAY:
            self.elapsed = time.time() - self.start_time
            if self.cd_warn_timer > 0:
                self.cd_warn_timer -= dt

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
            self.win_timer += dt
            if self.win_timer >= 7.0:
                self.win_alpha = min(255, self.win_alpha + 4)

    def _draw(self, t):
        if self.state == STATE_MENU:
            draw_menu(self.screen, self.stars, t, self.play_btn, self.instr_btn,
                      self.show_instructions, self.font_large, self.font_med, self.font_small)
            return

        self.screen.fill(C_BG)
        draw_stars(self.screen, self.stars, t)

        show_paths = (self.state == STATE_WIN)

        # Vẽ mê cung (sao đích vẽ sau fog)
        draw_maze(self.screen, self.maze, self.player.x, self.player.y,
                  self.player.visited, VISION_RADIUS,
                  list(self.player.path), self.opt_path, show_paths, t,
                  self.win_timer if self.state == STATE_WIN else 0)

        for g in self.guards:
            draw_guard(self.screen, g, self.player.x, self.player.y, t)
        draw_player(self.screen, self.player, t)

        # Fog of war
        if self.state != STATE_WIN:
            fog = build_fog(self.player.x, self.player.y, self.player.visited, VISION_RADIUS)
            self.screen.blit(fog, (0, 0))

        # Đích: luôn sáng, vẽ trên fog / visited mờ
        ex, ey = self.maze.exit
        draw_exit_star_bright(self.screen, ex, ey)

        # SỬA LOGIC NÚT GỢI Ý (CHỈ HIỂN THỊ BƯỚC TIẾP THEO)
        # Vẽ mũi tên gợi ý (nếu đang active)
        if self.hint_timer > 0 and len(self.hint_path) > 1:
            # Lấy vị trí hiện tại của player [0] và ô cần đi tiếp theo [1]
            x1, y1 = self.hint_path[0]
            x2, y2 = self.hint_path[1]
            start = (x1 * TILE_W + TILE_W // 2, y1 * TILE_H + TILE_H // 2)
            end = (x2 * TILE_W + TILE_W // 2, y2 * TILE_H + TILE_H // 2)
            draw_arrow(self.screen, start, end, (100, 255, 140), width=5)
        # Bỏ vòng lặp for. Đường đi (path) do BFS trả về bao gồm cả điểm xuất phát tại index [0]. 
        # Chỉ lấy index [0] nối với [1] để hướng dẫn user đi duy nhất 1 ô tiếp theo.

        # HUD
        if self.state != STATE_WIN:
            draw_hud(self.screen, self.player, self.elapsed, self.font_small)
            draw_guard_state_hud(self.screen, self.guards, self.font_small)
            draw_hint_button(self.screen, self.hint_btn, self.hint_cooldown, self.font_small, t, pygame.mouse.get_pos())
            
            #Render Text lên màn hình 
            # Khối code AFTER: Thêm render cảnh báo hồi chiêu
            if self.cd_warn_timer > 0:
                msg = f"Đang hồi chiêu, hãy chờ {int(self.hint_cooldown) + 1}s"
                msg_surf = self.font_med.render(msg, True, (255, 100, 100)) # Màu đỏ nhạt cảnh báo
                self.screen.blit(msg_surf, (SCREEN_W // 2 - msg_surf.get_width() // 2, 80))
        # Vẽ nút Pause nhỏ khi đang chơi
        if self.state == STATE_PLAY:
                mouse_pos = pygame.mouse.get_pos()
                is_hover = self.pause_btn.collidepoint(mouse_pos)
                
                cx, cy = self.pause_btn.center
                r = 17 # Đồng bộ với bán kính nút Hint
                
                # Tính toán màu sắc dựa trên trạng thái Hover
                if is_hover:
                    body_color = (60, 75, 90)      # Nền sáng hơn khi hover
                    bar_color = (255, 255, 255)    
                    border_color = (130, 210, 255) 
                else:
                    body_color = (35, 35, 35)      
                    bar_color = (180, 180, 180)    
                    border_color = (70, 70, 70)    
                
                # 1. Vẽ nền và viền
                pygame.draw.circle(self.screen, body_color, (cx, cy), r)
                pygame.draw.circle(self.screen, border_color, (cx, cy), r, 2)
                
                # 2. Vẽ biểu tượng Pause (||) nhỏ hơn để cân đối
                bar_w, bar_h = 5, 14
                pygame.draw.rect(self.screen, bar_color, 
                                 (cx - 6, cy - bar_h // 2, bar_w, bar_h), border_radius=1)
                pygame.draw.rect(self.screen, bar_color, 
                                 (cx + 1, cy - bar_h // 2, bar_w, bar_h), border_radius=1)

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
        self.screen.blit(bottom_hint, (SCREEN_W // 2 - bottom_hint.get_width() // 2, SCREEN_H - 36))

        if self.state == STATE_PAUSE:
            draw_pause_overlay(self.screen, self, self.font_med, self.font_small)
if __name__ == '__main__':
    Game().run()