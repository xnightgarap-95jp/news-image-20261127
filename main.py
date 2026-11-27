#!/usr/bin/env python3
"""Sum up the world's news of Friday 27 November 2026 in one image.

A Python 3.13 standard-library-only program. It draws a one-page
newspaper front page -- masthead with the day's date, a headline
ticker, a region strip, five key figures, three hero stories with
flat vector scenes, twelve smaller story panels, a world map with
the stories pinned, a numbered list of twenty more stories, and a
date-check footer -- and writes it to /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png, or the directory given as argv[1]).

Everything is drawn from scratch in this file: a hand-made 5x7
pixel font, a tiny raster canvas with rect / circle / line /
polygon fills, flat vector scenes for each story, and a minimal
PNG encoder (zlib + struct). No network, no randomness, no clock:
two runs write byte-identical files.

The 35 stories were gathered from the morning wires of Friday
27 November 2026 (BBC, Reuters, AP, New York Times, NDTV, India
Today, The Hindu, Newstalk ZB) and are listed with their sources
in NEWS.md. Only events that happened, or were first reported, on
Friday 27 November 2026 in some time zone are counted as the
day's news; bigger stories that belong to earlier days are named
in the footer's DATE CHECK instead of being passed off as today's.
"""

import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font
# Hand-made 5x7 pixel font. Each glyph is 7 rows of 5 bits, stored as
# seven small ints, top row first. At scale 1 a glyph is 5 px wide and
# 7 px tall; characters advance 6 px. Bit 4 is the leftmost pixel.
FONT = {
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    '"': (0x0A, 0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00),
    "#": (0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A),
    "$": (0x04, 0x0F, 0x15, 0x0E, 0x05, 0x1E, 0x04),
    "%": (0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03),
    "&": (0x0E, 0x11, 0x12, 0x0A, 0x15, 0x12, 0x0D),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "*": (0x00, 0x0A, 0x04, 0x1F, 0x04, 0x0A, 0x00),
    "+": (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    ",": (0x00, 0x00, 0x00, 0x00, 0x04, 0x04, 0x08),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    "/": (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x0E, 0x10, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x02, 0x04, 0x04, 0x04),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E),
    ":": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ";": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x08),
    "<": (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
    "=": (0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00),
    ">": (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    "@": (0x0E, 0x11, 0x17, 0x15, 0x14, 0x10, 0x0E),
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0E),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x19, 0x15, 0x13, 0x13, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "[": (0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E),
    "\\": (0x10, 0x08, 0x08, 0x04, 0x04, 0x02, 0x01),
    "]": (0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E),
    "^": (0x04, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00),
    "_": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F),
    "`": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    "a": (0x00, 0x00, 0x0F, 0x01, 0x0F, 0x11, 0x0E),
    "b": (0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x1E),
    "c": (0x00, 0x00, 0x0E, 0x10, 0x10, 0x11, 0x0E),
    "d": (0x01, 0x01, 0x0F, 0x11, 0x11, 0x11, 0x0F),
    "e": (0x00, 0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E),
    "f": (0x06, 0x09, 0x08, 0x1C, 0x08, 0x08, 0x08),
    "g": (0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    "h": (0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x11),
    "i": (0x04, 0x00, 0x0C, 0x04, 0x04, 0x04, 0x0E),
    "j": (0x01, 0x00, 0x06, 0x02, 0x02, 0x02, 0x0C),
    "k": (0x10, 0x10, 0x12, 0x14, 0x18, 0x14, 0x12),
    "l": (0x0C, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "m": (0x00, 0x00, 0x1A, 0x15, 0x15, 0x15, 0x15),
    "n": (0x00, 0x00, 0x1E, 0x11, 0x11, 0x11, 0x11),
    "o": (0x00, 0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E),
    "p": (0x00, 0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10),
    "q": (0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01, 0x01),
    "r": (0x00, 0x00, 0x16, 0x19, 0x10, 0x10, 0x10),
    "s": (0x00, 0x00, 0x0F, 0x10, 0x0E, 0x01, 0x1E),
    "t": (0x08, 0x08, 0x1C, 0x08, 0x08, 0x08, 0x06),
    "u": (0x00, 0x00, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "v": (0x00, 0x00, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "w": (0x00, 0x00, 0x11, 0x15, 0x15, 0x15, 0x0A),
    "x": (0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11),
    "y": (0x00, 0x11, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    "z": (0x00, 0x00, 0x1F, 0x02, 0x04, 0x08, 0x1F),
    "{": (0x06, 0x08, 0x08, 0x1C, 0x08, 0x08, 0x06),
    "|": (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "}": (0x0C, 0x02, 0x02, 0x07, 0x02, 0x02, 0x0C),
    "~": (0x00, 0x00, 0x0E, 0x15, 0x00, 0x00, 0x00),
    "•": (0x00, 0x00, 0x0E, 0x0E, 0x0E, 0x00, 0x00),
    "—": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
}


def text_w(s, scale=1):
    """Pixel width of s at the given scale (no trailing advance)."""
    if not s:
        return 0
    return len(s) * 6 * scale - scale


def wrap_text(s, max_w, scale=1):
    """Greedy word wrap; returns a list of lines fitting max_w pixels."""
    lines, cur = [], ""
    for word in s.split(" "):
        trial = word if not cur else cur + " " + word
        if text_w(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- canvas
PAPER = (247, 242, 231)
INK = (20, 20, 20)
RED = (176, 42, 30)
NAVY = (20, 38, 74)
GREY = (110, 108, 100)
LIGHT = (232, 226, 210)
WHITE = (255, 255, 255)


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = bytes(c) * (x1 - x0)

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill and d <= r * r:
                    self.set(xx, yy, c)
                elif not fill and abs(d - r * r) <= r:
                    self.set(xx, yy, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for yy in range(cy - ry, cy + ry + 1):
            for xx in range(cx - rx, cx + rx + 1):
                if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0:
                    self.set(xx, yy, c)

    def tri(self, ax, ay, bx, by, cx, cy, c):
        minx, maxx = min(ax, bx, cx), max(ax, bx, cx)
        miny, maxy = min(ay, by, cy), max(ay, by, cy)
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if den == 0:
            return
        for yy in range(miny, maxy + 1):
            for xx in range(minx, maxx + 1):
                a = ((by - cy) * (xx - cx) + (cx - bx) * (yy - cy)) / den
                b = ((cy - ay) * (xx - cx) + (ax - cx) * (yy - cy)) / den
                cc = 1 - a - b
                if a >= 0 and b >= 0 and cc >= 0:
                    self.set(xx, yy, c)

    def poly(self, pts, c):
        """Scanline fill of a simple polygon given as [(x, y), ...]."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                for x in range(int(xs[j]), int(xs[j + 1]) + 1):
                    self.set(x, y, c)

    def text(self, x, y, s, c, scale=1, bold=False):
        """Draw s with its top-left at (x, y). Unknown chars become '?'."""
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT["?"])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, c)
                        if bold:
                            self.rect(cx + col * scale + 1,
                                      y + row * scale, scale, scale, c)
            cx += 6 * scale
        return cx

    def text_c(self, cx, y, s, c, scale=1, bold=False):
        """Draw s centred on cx."""
        self.text(cx - text_w(s, scale) // 2, y, s, c, scale, bold)


# ---------------------------------------------------------------- png
def png_bytes(cv):
    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


# ---------------------------------------------------------------- scenes
# Flat vector pictograms, one per story kind. Each draws inside the
# box (x, y, w, h) and never outside it.

def scene_drone(cv, x, y, w, h):
    cv.rect(x, y, w, h, (31, 44, 66))
    cv.circle(x + w // 4, y + h // 4, 16, (210, 205, 190))
    cv.circle(x + 3 * w // 4, y + h // 4, 12, (210, 205, 190))
    # explosion burst, right side
    ex, ey = x + int(w * 0.72), y + int(h * 0.62)
    for dx, dy, r in ((0, 0, 16), (-18, -8, 9), (16, -10, 8),
                      (-12, 12, 8), (18, 10, 9), (0, -20, 7)):
        cv.circle(ex + dx, ey + dy, r, (232, 120, 30))
    cv.circle(ex, ey, 8, (255, 210, 90))
    # drone body + arms + rotors
    dx0, dy0 = x + w // 2 - 34, y + h // 2 - 8
    cv.rect(dx0, dy0, 68, 16, (20, 20, 20))
    cv.rect(dx0 - 26, dy0 - 4, 26, 4, (20, 20, 20))
    cv.rect(dx0 + 68, dy0 - 4, 26, 4, (20, 20, 20))
    cv.circle(dx0 - 28, dy0 - 2, 7, (200, 200, 200))
    cv.circle(dx0 + 96, dy0 - 2, 7, (200, 200, 200))
    cv.rect(dx0 + 26, dy0 + 5, 16, 6, (176, 42, 30))
    # ground + flag pole
    cv.rect(x, y + h - 14, w, 14, (120, 96, 66))
    cv.vline(x + 26, y + h - 52, 40, (240, 240, 240), 3)
    cv.rect(x + 29, y + h - 52, 26, 14, (0, 122, 61))


def scene_storm(cv, x, y, w, h):
    cv.rect(x, y, w, h, (58, 74, 96))
    # rain
    for i in range(26):
        rx = x + 8 + (i * 37) % (w - 16)
        ry = y + 6 + (i * 23) % (h - 30)
        cv.line(rx, ry, rx - 5, ry + 12, (180, 200, 220))
    # clouds
    for cx, cy, r in ((70, 26, 22), (110, 20, 26), (150, 28, 20),
                      (240, 24, 24), (280, 30, 18)):
        cv.circle(x + cx, y + cy, r, (210, 214, 220))
    # parade balloon: big oval + basket, tilted by the wind
    cv.ellipse(x + w // 2, y + h // 2 + 6, 62, 34, (232, 120, 30))
    cv.ellipse(x + w // 2, y + h // 2 + 6, 44, 22, (255, 210, 90))
    cv.rect(x + w // 2 - 12, y + h // 2 + 42, 24, 12, (120, 72, 30))
    cv.line(x + w // 2 - 30, y + h // 2 + 38, x + w // 2 - 10,
            y + h // 2 + 42, (40, 40, 40))
    cv.line(x + w // 2 + 30, y + h // 2 + 38, x + w // 2 + 10,
            y + h // 2 + 42, (40, 40, 40))
    # street
    cv.rect(x, y + h - 12, w, 12, (40, 40, 44))
    cv.text(x + 8, y + h - 30, "100th PARADE POSTPONED", (255, 255, 255), 1, True)


def scene_rubble(cv, x, y, w, h):
    cv.rect(x, y, w, h, (214, 190, 150))
    cv.rect(x, y, w, 34, (94, 110, 140))
    cv.circle(x + 52, y + 18, 12, (255, 220, 130))
    # standing and broken buildings
    cv.rect(x + 20, y + 52, 46, h - 66, (90, 84, 76))
    cv.rect(x + 76, y + 72, 40, h - 86, (120, 112, 100))
    cv.poly([(x + 130, y + h - 14), (x + 130, y + 92), (x + 178, y + 60),
             (x + 196, y + h - 14)], (70, 64, 56))
    cv.rect(x + 210, y + 60, 44, h - 74, (100, 92, 82))
    cv.rect(x + 264, y + 84, 40, h - 98, (130, 122, 110))
    # windows
    for bx, by in ((28, 60), (44, 60), (28, 78), (84, 80), (218, 68),
                   (234, 68), (272, 92)):
        cv.rect(x + bx, y + by, 7, 9, (255, 220, 130))
    # smoke
    for sx, sy, r in ((150, 66, 12), (168, 54, 15), (186, 68, 10)):
        cv.circle(x + sx, y + sy, r, (150, 146, 138))
    cv.rect(x, y + h - 14, w, 14, (70, 64, 56))


def scene_mini(cv, kind, x, y, w, h):
    """Small pictogram strip for the twelve grid panels."""
    bg = {"chart_down": (226, 232, 238), "chess": (232, 226, 210),
          "podium": (238, 226, 222), "tanker": (210, 226, 236),
          "court": (232, 228, 218), "rocket": (214, 226, 238),
          "chart_up": (226, 236, 224), "scales": (232, 230, 220),
          "flame": (244, 224, 210), "virus": (228, 234, 226),
          "mountain": (228, 226, 214), "satellite": (216, 222, 236)}[kind]
    cv.rect(x, y, w, h, bg)
    if kind == "chart_down":
        cv.line(x + 8, y + 8, x + w - 8, y + h - 8, RED)
        cv.line(x + w - 8, y + h - 8, x + w - 8, y + h - 18, RED)
        cv.line(x + w - 8, y + h - 8, x + w - 18, y + h - 8, RED)
        cv.text(x + 8, y + h - 14, "-6.2%", INK, 1, True)
    elif kind == "chess":
        for r in range(4):
            for c in range(8):
                if (r + c) % 2 == 0:
                    cv.rect(x + 8 + c * 18, y + 2 + r * 8, 18, 8, INK)
        cv.text(x + 8, y + h - 14, "GAME 3 DRAW", INK, 1, True)
    elif kind == "podium":
        cv.rect(x + 14, y + h - 18, 34, 18, (176, 42, 30))
        cv.rect(x + 56, y + h - 26, 34, 26, (20, 38, 74))
        cv.rect(x + 98, y + h - 12, 34, 12, (110, 108, 100))
        cv.text(x + 8, y + 4, "NO CLEAR", INK, 1, True)
        cv.text(x + 8, y + 14, "WINNER", INK, 1, True)
    elif kind == "tanker":
        cv.poly([(x + 20, y + h - 12), (x + 30, y + 12), (x + 130, y + 22),
                 (x + 140, y + h - 12)], (60, 60, 66))
        cv.rect(x, y + h - 12, w, 12, (40, 90, 130))
        cv.text(x + 8, y + 4, "7,000 T", INK, 1, True)
    elif kind == "court":
        for cx in (24, 62, 100, 138):
            cv.rect(x + cx, y + 8, 8, h - 20, (120, 108, 84))
        cv.rect(x + 10, y + 4, 146, 6, (120, 108, 84))
        cv.rect(x + 10, y + h - 12, 146, 6, (120, 108, 84))
    elif kind == "rocket":
        cv.tri(x + 78, y + 2, x + 66, y + 26, x + 90, y + 26, (220, 60, 40))
        cv.rect(x + 70, y + 24, 16, 8, (240, 240, 240))
        cv.tri(x + 70, y + 30, x + 78, y + 30, x + 78, y + 40, (255, 180, 60))
        cv.text(x + 8, y + h - 14, "2 SHARES", INK, 1, True)
    elif kind == "chart_up":
        cv.line(x + 8, y + h - 8, x + w - 8, y + 8, (0, 122, 61))
        cv.line(x + w - 8, y + 8, x + w - 8, y + 18, (0, 122, 61))
        cv.line(x + w - 8, y + 8, x + w - 18, y + 8, (0, 122, 61))
        cv.text(x + 8, y + 4, "4.3%", INK, 1, True)
    elif kind == "scales":
        cv.vline(x + w // 2, y + 4, h - 14, INK, 2)
        cv.hline(x + 20, y + 8, w - 40, INK, 2)
        cv.tri(x + 26, y + 10, x + 44, y + 10, x + 35, y + 22, INK)
        cv.tri(x + w - 46, y + 10, x + w - 28, y + 10, x + w - 37, y + 22, INK)
    elif kind == "flame":
        cv.tri(x + w // 2, y + 2, x + w // 2 - 16, y + 22,
               x + w // 2 + 16, y + 22, (232, 120, 30))
        cv.tri(x + w // 2, y + 12, x + w // 2 - 10, y + 26,
               x + w // 2 + 10, y + 26, (255, 180, 60))
        cv.rect(x + 12, y + h - 12, w - 24, 8, (90, 84, 76))
    elif kind == "virus":
        cv.circle(x + w // 2, y + h // 2, 10, (90, 140, 90))
        for dx, dy in ((-16, -8), (16, -8), (-16, 8), (16, 8), (0, -14)):
            cv.circle(x + w // 2 + dx, y + h // 2 + dy, 5, (90, 140, 90))
        cv.text(x + 8, y + h - 14, "12,000+", INK, 1, True)
    elif kind == "mountain":
        cv.tri(x + 10, y + h - 8, x + 60, y + 4, x + 110, y + h - 8, (120, 110, 96))
        cv.tri(x + 90, y + h - 8, x + 130, y + 12, x + 160, y + h - 8, (90, 84, 76))
        cv.circle(x + 60, y + 8, 5, (255, 255, 255))
    elif kind == "satellite":
        cv.rect(x + 66, y + 10, 34, 14, (200, 200, 210))
        cv.rect(x + 40, y + 12, 24, 10, (40, 90, 160))
        cv.rect(x + 102, y + 12, 24, 10, (40, 90, 160))
        cv.line(x + 100, y + 30, x + 130, y + h - 8, (150, 150, 150))
        cv.text(x + 8, y + h - 14, "500 SATS", INK, 1, True)


# ---------------------------------------------------------------- data
# (number, region, field, headline, body) for the three heroes.
HEROES = [
    ("drone",
     "KUWAIT  •  MIDDLE EAST  •  WAR",
     "Drone strike kills 2 Italians in Kuwait",
     "Kuwait says an Iranian drone struck a site in the country, "
     "killing two Italian workers. Iran denies responsibility.",
     "WHY IT MATTERS  First reported Iranian strike on Kuwaiti "
     "soil; Gulf tensions rise."),
    ("storm",
     "NEW YORK  •  USA  •  WEATHER",
     "Storms halt Thanksgiving travel; Macy's parade postponed",
     "A huge storm disrupts Thanksgiving travel across the US. New "
     "York postpones its 100th Macy's parade for the first time.",
     "WHY IT MATTERS  80 million Americans were travelling for "
     "the holiday; 500,000+ lost power."),
    ("rubble",
     "GAZA  •  MIDDLE EAST  •  WAR",
     "Hamas weighs reply after Israel kills 10 in Gaza",
     "Hamas weighs its response after Israeli strikes kill 10 "
     "people in Gaza. 16 schoolchildren have died there this month.",
     "WHY IT MATTERS  The ceasefire is under strain as the "
     "death toll keeps rising."),
]

# (number, scene kind, kicker, headline, body) for the twelve panels.
PANELS = [
    (4, "chart_down", "LONDON  •  MIGRATION",
     "UK migration falls to lowest since 1997",
     "Net migration drops to its lowest since 1997, outside the pandemic."),
    (5, "chess", "CHESS  •  SPORT",
     "Gukesh, Sindarov draw marathon Game 3",
     "Nothing separates the pair after three games of the title match."),
    (6, "podium", "PARIS  •  POLITICS",
     "France mainstream risks vote debacle",
     "Macron slams Le Pen as no clear candidate emerges."),
    (7, "tanker", "IBIZA  •  DISASTER",
     "Tanker capsizes off Ibiza; 1 killed",
     "Diesel tanker carrying up to 7,000 tonnes sinks; oil-spill race on."),
    (8, "court", "PARIS  •  JUSTICE",
     "Depardieu to stand trial over 2018 rape claim",
     "Court orders trial for the alleged rape of an actress in 2018."),
    (9, "rocket", "USA  •  TECH",
     "Musk: every US child gets 2 SpaceX shares",
     "Elon Musk says every child in the US will receive two shares."),
    (10, "chart_up", "WASHINGTON  •  ECONOMY",
     "Trump seeks probe into 'fake' GDP figures",
     "Growth revised up to 4.3%; Trump demands an inquiry."),
    (11, "scales", "NEW DELHI  •  JUSTICE",
     "India court: judge must sit on PMLA bench",
     "Top court also quashes ex-MP Anand Mohan's early release."),
    (12, "flame", "JAZAN  •  WAR",
     "Jazan refinery attack kills Nepali worker",
     "Strike on Saudi refinery kills one worker; fire contained."),
    (13, "virus", "CONGO  •  HEALTH",
     "Ebola in Congo passes 12,000 cases",
     "Outbreak grows as unrest forces responders to leave."),
    (14, "mountain", "NEPAL  •  DISASTER",
     "Nepal declares 4,000 landslide missing dead",
     "Missing victims of the landslides formally declared dead."),
    (15, "satellite", "BELGIUM  •  SPACE",
     "Europe's biggest satellite factory opens",
     "Belgian plant can build 500 satellites."),
]

# (number, place, one-line story) for the twenty more stories.
# Kept short on purpose: place + " — " + text must fit one column
# (about 50 chars at scale 1); the draw loop truncates as a backstop.
ALSO = [
    (16, "BLACK FRIDAY", "Half of sale prices no cheaper"),
    (17, "AI", "Anthropic turns Claude artifacts into apps"),
    (18, "MALI", "300+ Russians killed backing junta"),
    (19, "INDIA", "Politician hosts a 400,000-guest wedding"),
    (20, "GERMANY", "Two Iraqis held over synagogue attack plot"),
    (21, "NEW ZEALAND", "Coalition keeps 67 of 131 seats"),
    (22, "USA", "Judge: FCC violated ABC's free speech"),
    (23, "SAUDI ARABIA", "Riyadh stops two Houthi missiles"),
    (24, "UKRAINE", "Russian ballistic missiles hit Kyiv"),
    (25, "PAKISTAN", "Karachi collapse: 3 dead, 14 hurt"),
    (26, "INDIA", "Cabinet backs Rs 11,000-cr factory scheme"),
    (27, "TECH", "Nvidia halts chip sales to 4 SE Asian states"),
    (28, "SOUTH KOREA", "Bank of Korea lifts rates on AI boom"),
    (29, "NORTH KOREA", "Kim vows permanent nuclear armament"),
    (30, "THAILAND", "Bangkok oil plant blast prompts evacuation"),
    (31, "MEDITERRANEAN", "65 terror suspects held in sweep"),
    (32, "USA", "Flights to Washington DCA grounded in storm"),
    (33, "FIFA", "Hackers accessed limited personal data"),
    (34, "RUGBY", "Barrett to captain All Blacks vs England"),
    (35, "NFL", "Rams beat Packers 26-13; Corum runs 184 yards"),
]

REGIONS = [
    ("N. AMERICA", 6, (20, 38, 74)), ("EUROPE", 8, (176, 42, 30)),
    ("MIDDLE EAST", 4, (0, 122, 61)), ("AFRICA", 2, (200, 130, 20)),
    ("SOUTH ASIA", 5, (150, 60, 140)), ("EAST ASIA", 2, (0, 140, 160)),
    ("SE ASIA", 2, (200, 90, 0)), ("OCEANIA", 3, (60, 120, 200)),
    ("GLOBAL", 3, (110, 108, 100)),
]

STATS = [
    ("2", "Italians killed in the Kuwait drone strike"),
    ("500K+", "US homes and businesses lose power in the storms"),
    ("4.3%", "US growth, revised up — Trump calls it 'fake'"),
    ("12,000", "Ebola cases in Congo, and still rising"),
    ("400,000", "guests at an Indian politician's wedding"),
]

# (lon, lat) pins for stories 1-15 on the map (5 has no known venue).
PINS = {1: (47.5, 29.3), 2: (-74.0, 40.7), 3: (34.5, 31.5), 4: (-0.1, 51.5),
        6: (2.35, 48.85), 7: (1.4, 38.98), 8: (2.6, 48.9), 9: (-97.7, 30.3),
        10: (-77.0, 38.9), 11: (77.2, 28.6), 12: (42.5, 16.9),
        13: (25.0, -2.0), 14: (84.0, 28.0), 15: (4.35, 50.85)}

# Leader offsets (dx, dy) for pins that would collide at this map scale:
# Europe's pins all fall within a few pixels of each other, and Gaza /
# Jazan / Delhi crowd the Arabia-India corner, so their numbered discs
# are pushed apart with a thin leader line back to the true spot.
PIN_OFFSET = {1: (0, 0), 2: (0, 0), 3: (-12, 10), 4: (-16, -12),
              6: (-2, -14), 7: (-14, 12), 8: (14, -10), 9: (0, 0),
              10: (0, 0), 11: (0, 0), 12: (12, 12), 13: (0, 0),
              14: (10, -12), 15: (16, 10)}

# Rough continent outlines in map-panel coordinates (x 0..296, y 0..170).
CONTINENTS = [
    [(18, 30), (60, 18), (96, 26), (104, 44), (88, 62), (66, 78),
     (52, 66), (30, 58)],                       # North America
    [(84, 92), (106, 88), (116, 106), (104, 138), (92, 122), (82, 104)],
    [(138, 30), (158, 22), (176, 30), (170, 48), (152, 46), (142, 40)],
    [(142, 62), (168, 56), (182, 72), (172, 100), (156, 96), (144, 78)],
    [(180, 24), (230, 14), (272, 26), (280, 52), (252, 66), (228, 88),
     (204, 72), (186, 48)],                      # Asia
    [(248, 108), (272, 104), (282, 122), (264, 132), (250, 122)],
]


# ---------------------------------------------------------------- layout
def draw(cv):
    cv.rect(0, 0, W, H, PAPER)

    # --- top bar
    cv.rect(0, 0, W, 24, NAVY)
    cv.text_c(W // 2, 8, "THE WORLD IN ONE DAY  •  35 STORIES  •  9 REGIONS  •  "
              "ALL FIRST REPORTED FRIDAY 27 NOVEMBER 2026", WHITE, 1, True)

    # --- masthead
    cv.text_c(W // 2, 30, "Friday 27 November 2026", INK, 6, True)
    cv.rect(60, 84, W - 120, 3, RED)

    # --- ticker
    cv.text_c(W // 2, 92,
              "Kuwait drone strike kills 2  •  Macy's parade postponed  •  "
              "Hamas weighs Gaza reply", RED, 2, True)

    # --- region strip
    x = 8
    chip_w = (W - 16) // len(REGIONS)
    for name, n, col in REGIONS:
        cv.rect(x, 114, chip_w - 3, 20, col)
        cv.text_c(x + (chip_w - 3) // 2, 120, "%s %d" % (name, n),
                  WHITE, 1, True)
        x += chip_w

    # --- five key figures
    y0 = 140
    cv.hline(8, y0 - 2, W - 16, INK, 2)
    bw = (W - 16) // 5
    for i, (num, label) in enumerate(STATS):
        bx = 8 + i * bw
        if i:
            cv.vline(bx, y0 + 2, 34, GREY, 1)
        cv.text_c(bx + bw // 2, y0 + 2, num, RED, 3, True)
        for j, ln in enumerate(wrap_text(label, bw - 10, 1)):
            cv.text_c(bx + bw // 2, y0 + 24 + j * 8, ln, INK, 1)
    cv.hline(8, y0 + 42, W - 16, INK, 2)

    # --- three hero stories
    hy, hh = 190, 246
    hw = (W - 16 - 12) // 3
    for i, (scene, kicker, head, body, why) in enumerate(HEROES):
        hx = 8 + i * (hw + 6)
        cv.rect(hx, hy, hw, hh, WHITE)
        cv.rect(hx, hy, hw, hh, INK)  # border via outline below
        cv.rect(hx + 1, hy + 1, hw - 2, hh - 2, WHITE)
        sy = hy + 4
        if scene == "drone":
            scene_drone(cv, hx + 4, sy, hw - 8, 104)
        elif scene == "storm":
            scene_storm(cv, hx + 4, sy, hw - 8, 104)
        else:
            scene_rubble(cv, hx + 4, sy, hw - 8, 104)
        ty = sy + 108
        cv.rect(hx + 4, ty, 22, 14, RED)
        cv.text(hx + 7, ty + 3, str(i + 1), WHITE, 1, True)
        cv.text(hx + 30, ty + 3, kicker, RED, 1, True)
        ty += 18
        for ln in wrap_text(head, hw - 12, 2):
            cv.text(hx + 6, ty, ln, INK, 2, True)
            ty += 16
        ty += 2
        for ln in wrap_text(body, hw - 12, 1):
            cv.text(hx + 6, ty, ln, INK, 1)
            ty += 8
        ty += 4
        for ln in wrap_text(why, hw - 12, 1):
            cv.text(hx + 6, ty, ln, GREY, 1)
            ty += 8
        cv.hline(hx, hy + hh, hw, INK, 1)

    # --- twelve small panels, 6 x 2
    gy = 446
    pw, ph = 166, 124
    for idx, (num, kind, kicker, head, body) in enumerate(PANELS):
        px = 4 + (idx % 6) * (pw + 4)
        py = gy + (idx // 6) * (ph + 6)
        cv.rect(px, py, pw, ph, WHITE)
        cv.rect(px, py, pw, 1, INK)
        cv.rect(px, py + ph - 1, pw, 1, INK)
        cv.rect(px, py, 1, ph, INK)
        cv.rect(px + pw - 1, py, 1, ph, INK)
        scene_mini(cv, kind, px + 3, py + 3, pw - 6, 34)
        ty = py + 40
        cv.rect(px + 3, ty, 16, 12, NAVY)
        cv.text(px + 5, ty + 2, str(num), WHITE, 1, True)
        cv.text(px + 22, ty + 2, kicker, RED, 1, True)
        ty += 15
        for ln in wrap_text(head, pw - 8, 1):
            cv.text(px + 4, ty, ln, INK, 1, True)
            ty += 8
        ty += 1
        for ln in wrap_text(body, pw - 8, 1):
            cv.text(px + 4, ty, ln, INK, 1)
            ty += 8

    # --- map + also list
    my = 710
    mh = 268
    cv.rect(4, my, 296, mh, WHITE)
    cv.rect(4, my, 296, 1, INK)
    cv.rect(4, my + mh - 1, 296, 1, INK)
    cv.rect(4, my, 1, mh, INK)
    cv.rect(299, my, 1, mh, INK)
    cv.text(12, my + 6, "WHERE IT HAPPENED", INK, 1, True)
    cv.text(12, my + 16, "dots = story numbers 1-15", GREY, 1)
    mx, myy = 4, my + 28
    for pts in CONTINENTS:
        cv.poly([(mx + px, myy + py) for px, py in pts], (206, 196, 172))
    for num, (lon, lat) in sorted(PINS.items()):
        px = mx + int((lon + 180) / 360.0 * 296)
        py = myy + int((75 - lat) / 130.0 * 170)
        dx, dy = PIN_OFFSET.get(num, (0, 0))
        if dx or dy:
            cv.line(px, py, px + dx, py + dy, RED)
            cv.circle(px, py, 2, RED)
        cv.circle(px + dx, py + dy, 7, RED)
        cv.text(px + dx - 2 if num < 10 else px + dx - 5, py + dy - 3,
                str(num), WHITE, 1, True)
    cv.text(12, my + mh - 26, "5: title match — venue not stated", GREY, 1)
    cv.text(12, my + mh - 16, "in the wires; no pin drawn.", GREY, 1)

    ax = 312
    cv.text(ax, my + 6, "ALSO ON FRIDAY 27 NOVEMBER — 20 MORE STORIES",
            INK, 1, True)
    cv.hline(ax, my + 18, W - ax - 8, INK, 2)
    col_w = (W - ax - 8) // 2
    for idx, (num, place, text) in enumerate(ALSO):
        col = idx // 10
        row = idx % 10
        lx = ax + col * col_w
        ly = my + 26 + row * 24
        cv.rect(lx, ly, 20, 13, NAVY)
        cv.text(lx + 3 if num < 10 else lx + 1, ly + 3, str(num),
                WHITE, 1, True)
        line = place + " — " + text
        while text_w(line, 1) > col_w - 28 and " " in line:
            line = line.rsplit(" ", 1)[0]
        cv.text(lx + 24, ly + 3, line, INK, 1)
        if ly + 22 > my + mh - 6:
            pass

    # --- footer
    fy = 986
    cv.rect(0, fy, W, H - fy, NAVY)
    cv.text(8, fy + 5,
            "DATE CHECK  Every story above happened or was first reported "
            "on Friday 27 November 2026.", WHITE, 1, True)
    cv.text(8, fy + 15,
            "NOT 27 NOV: US tariff plan on 14 economies (25 Nov)  •  "
            "Champions League results (25-26 Nov).", (200, 205, 215), 1)
    cv.text(8, fy + 25,
            "Sources: BBC, Reuters, AP, NYT, NDTV, India Today, The Hindu, "
            "Newstalk ZB. Every drawing original.", (200, 205, 215), 1)


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        "MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    draw(cv)
    data = png_bytes(cv)
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (os.path.join(outdir, "entry.png"),
                                   len(data)))


if __name__ == "__main__":
    main()
