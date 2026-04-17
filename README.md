# AI Maze Game

Minimalist maze game inspired by Escape Maze — dark aesthetic, thin white lines.

## Cài đặt

```bash
pip install pygame
```

## Chạy game

```bash
cd maze_game
python main.py
```

## Điều khiển

| Phím | Tác dụng |
|------|----------|
| W / ↑ | Đi lên |
| S / ↓ | Đi xuống |
| A / ← | Đi trái |
| D / → | Đi phải |
| R | Chơi lại (map mới) |

## Các yếu tố trong game

| Ký hiệu | Màu | Mô tả |
|---------|-----|--------|
| Ô trắng | Trắng | Nhân vật (player) |
| Ô nhấp nháy trắng | Trắng | Exit — đích đến |
| Vòng tím | Tím | Teleport (đứng vào → dịch chuyển sang đầu kia) |
| Hình elip xanh | Xanh dương | Bẫy nước (rơi vào → về Start) |
| Ô chữ X đỏ | Đỏ | Lính canh — đứng gần sẽ bị đuổi |

## Tính năng AI

- **Maze generation**: DFS recursive backtracking — mỗi lần chơi là 1 mê cung khác nhau
- **Fog of war**: Chỉ thấy bán kính 4 ô xung quanh. Ô đã đi qua thì hiện mờ
- **Guard FSM**: Lính canh có 3 trạng thái: PATROL → CHASE (khi thấy player) → RETURN (khi mất dấu)
- **BFS pathfinding**: Sau khi thắng, hiện đường đi ngắn nhất màu xanh lá và đường bạn đi màu đỏ

## Cấu trúc project

```
maze_game/
├── main.py          ← Vòng lặp chính, rendering, game states
├── maze.py          ← Sinh mê cung, đặt bẫy/teleport/guard
├── player.py        ← State nhân vật
├── guard.py         ← AI lính canh (FSM)
├── pathfinding.py   ← BFS tìm đường ngắn nhất
├── settings.py      ← Hằng số, màu sắc, config
└── README.md
```

## Tuỳ chỉnh dễ dàng trong `settings.py`

```python
VISION_RADIUS = 4      # tầm nhìn (tăng = dễ hơn)
NUM_GUARDS = 2         # số lính canh
NUM_WATER_TRAPS = 6    # số bẫy nước
GUARD_VISION = 5       # tầm nhìn của guard
GUARD_SPEED_FRAMES = 12  # guard di chuyển mỗi N frame (giảm = nhanh hơn)
MAZE_COLS = 21         # kích thước mê cung (phải là số lẻ)
MAZE_ROWS = 21
```
