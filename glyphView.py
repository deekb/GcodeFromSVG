import pygame
import numpy as np

# ==== CONFIG ====
CELL_SIZE = 100
MARGIN = 20
POINT_RADIUS = 2
GRID_COLS = 10
BG_COLOR = (30, 30, 30)
POINT_COLOR = (240, 240, 240)
LINE_COLOR = (100, 200, 255)

# ==== LOAD GLYPH POINTS ====
data = np.load("glyph_points.npz")
glyph_chars = list(data.keys())

# ==== INIT PYGAME ====
pygame.init()
cols = GRID_COLS
rows = (len(glyph_chars) + cols - 1) // cols
window_width = cols * CELL_SIZE + MARGIN * 2
window_height = rows * CELL_SIZE + MARGIN * 2
screen = pygame.display.set_mode((window_width, window_height))
pygame.display.set_caption("Glyph Viewer")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)


# ==== NO SCALING FUNCTION ====
def no_scale(points, size):
    # This function returns points without normalization or scaling
    return [((int(x)*0.1), (int(y)*-0.1)+80) for x, y in points]


# ==== MAIN LOOP ====
running = True
while running:
    screen.fill(BG_COLOR)

    for i, char in enumerate(glyph_chars):
        row = i // cols
        col = i % cols
        x = MARGIN + col * CELL_SIZE
        y = MARGIN + row * CELL_SIZE

        # Draw glyph points
        points = data[char]
        if len(points) == 0:
            continue

        # No scaling, use the points as they are
        shifted = [(px + x + 10, py + y + 10) for px, py in no_scale(points, CELL_SIZE - 20)]

        # Draw lines
        if len(shifted) > 1:
            pygame.draw.lines(screen, LINE_COLOR, False, shifted, 1)

        # Draw points
        for px, py in shifted:
            pygame.draw.circle(screen, POINT_COLOR, (px, py), POINT_RADIUS)

        # Draw character label
        label = font.render(char, True, (200, 200, 200))
        screen.blit(label, (x + 5, y + 5))

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
