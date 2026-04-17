import pygame

# Window
SCREEN_W = 800
SCREEN_H = 800
FPS = 60
TITLE = "AI Maze"

# Maze dimensions (must be odd)
MAZE_COLS = 21
MAZE_ROWS = 21

# Tile size (computed from screen)
TILE_W = SCREEN_W // MAZE_COLS
TILE_H = SCREEN_H // MAZE_ROWS

# Vision radius (Manhattan distance)
VISION_RADIUS = 4

# Entities
NUM_WATER_TRAPS = 6
NUM_GUARDS = 2
NUM_TELEPORT_PAIRS = 1

# Guard
GUARD_VISION = 5
GUARD_SPEED_FRAMES = 12   # move every N frames

# Colors — minimalist dark palette
C_BG           = (18, 10, 8)       # deep dark brown-black
C_WALL         = (18, 10, 8)       # wall = same as bg (negative space)
C_FLOOR        = (30, 18, 14)      # barely lighter floor
C_LINE         = (210, 195, 180)   # thin wall outline color
C_PLAYER       = (255, 255, 255)
C_PLAYER_GLOW  = (255, 255, 200)
C_EXIT         = (255, 255, 255)
C_WATER        = (60, 120, 180)
C_TELEPORT     = (160, 80, 220)
C_GUARD        = (220, 60, 60)
C_GUARD_CHASE  = (255, 30, 30)
C_FOG          = (18, 10, 8)       # fully dark fog
C_VISITED      = (28, 16, 12)      # faint visited
C_PATH_PLAYER  = (180, 80, 80)
C_PATH_OPT     = (80, 200, 120)
C_TEXT         = (210, 195, 180)
C_TEXT_DIM     = (100, 90, 80)
C_STAR         = (200, 180, 160)
C_OVERLAY      = (10, 6, 4)

# Tile symbols
WALL = '#'
FLOOR = '.'
START = 'S'
EXIT = 'E'
WATER = 'W'
TELEPORT = 'T'
GUARD_TILE = 'G'
