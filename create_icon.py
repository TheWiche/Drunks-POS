"""Genera icon.ico para Drunks RIOH — palmera teal sobre fondo navy."""
import math
from PIL import Image, ImageDraw


def rounded_rect(draw, xy, r, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill)
    draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill)
    draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill)
    draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill)


def tapered_frond(draw, bx, by, tx, ty, base_w, tip_w, fill):
    dx, dy = tx - bx, ty - by
    length = math.hypot(dx, dy)
    if length < 1:
        return
    nx, ny = -dy / length, dx / length
    draw.polygon([
        (bx + nx * base_w, by + ny * base_w),
        (bx - nx * base_w, by - ny * base_w),
        (tx - nx * tip_w,  ty - ny * tip_w),
        (tx + nx * tip_w,  ty + ny * tip_w),
    ], fill=fill)


def make_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    BG   = (10, 28, 40, 255)
    TEAL = (38, 198, 170, 255)

    r_bg = max(2, size // 7)
    rounded_rect(draw, (0, 0, size - 1, size - 1), r_bg, BG)

    if size < 24:
        m = size // 5
        draw.ellipse([m, m, size - m, size - m], fill=TEAL)
        return img

    s  = size
    cx = s // 2

    # trunk — from frond-base down
    fb_y   = int(s * 0.46)
    tw     = max(2, s // 12)
    trunk_bot = int(s * 0.86)
    draw.polygon([
        (cx - tw,     fb_y),
        (cx + tw,     fb_y),
        (cx + max(1, tw // 2), trunk_bot),
        (cx - max(1, tw // 2), trunk_bot),
    ], fill=TEAL)

    # fronds: (tip_x, tip_y)
    bw = max(2, s // 16)
    fronds = [
        # top-center
        (cx,                 int(s * 0.08)),
        # upper-left
        (int(cx - s * 0.34), int(s * 0.16)),
        # upper-right
        (int(cx + s * 0.34), int(s * 0.16)),
        # lower-left
        (int(cx - s * 0.40), int(s * 0.36)),
        # lower-right
        (int(cx + s * 0.40), int(s * 0.36)),
    ]
    for tx, ty in fronds:
        tapered_frond(draw, cx, fb_y, tx, ty, bw, max(1, bw // 3), TEAL)

    return img


def main():
    # Dibuja en 256x256 y deja que PIL resize para cada tamaño
    big = make_icon(256)
    big.save(
        "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
               (64, 64), (128, 128), (256, 256)],
    )
    print("icon.ico generado")


if __name__ == "__main__":
    main()
