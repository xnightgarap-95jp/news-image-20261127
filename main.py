#!/usr/bin/env python3
"""Sum up the world's news of Friday 27 November 2026 in one image.

A Python 3.13 standard-library-only program. It draws a one-page
newspaper front page -- masthead naming the day, a ticker, a strip
of six key figures, a region strip, a UTC wire-times strip, three
hero stories with flat vector scenes, ten more pictured panels,
a dotted world map with the pictured stories pinned, a list of 39
more stories, and a date-check footer -- and writes it to
/output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png, or the
directory given as argv[1]).

Everything is drawn from scratch in this file: a hand-made 5x7
pixel font, a tiny raster canvas with rect / circle / line /
polygon fills, flat vector scenes for each story, and a minimal
PNG encoder (zlib + struct). No network, no randomness, no clock:
two runs write byte-identical files.

The 52 stories were gathered from the wires of Friday 27 November
2026 (AP, Reuters, BBC, New York Times, Electoral Commission of
New Zealand, Bank of Japan data via Yonhap, and others) and are
listed with their sources in NEWS.md. Only events that happened,
or were first reported, on Friday 27 November 2026 in some time
zone are counted as the day's news. Stories that belong to earlier
days -- the Kuwait drone strike, the Gaza strikes, the Ibiza
tanker, the Bangkok refinery blast, the Depardieu trial, the ONS
migration release -- are named in the footer's DATE CHECK instead
of being passed off as today's. The v1 entry for this same day
led with the Kuwait strike, the Thanksgiving storm peak and the
Gaza strikes, all Thursday 26 November events; this rebuild
replaces them with stories that are unambiguously Friday's: the
New Zealand final count, the China stock surge, the Zelenskyy
BBC interview, the 155-drone night, the Mackenzie verdict, the
Malinin world record, and Friday's market closes.

Scenes are clipped to their own panel box by construction: the
canvas carries a clip rectangle while a scene draws, so no scene
can paint over the panel above it.
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
        self.clip = None  # (x0, y0, x1, y1) or None: nothing may paint outside

    def set_clip(self, x, y, w, h):
        self.clip = (x, y, x + w, y + h)

    def clear_clip(self):
        self.clip = None

    def _in_clip(self, x, y):
        if self.clip is None:
            return True
        x0, y0, x1, y1 = self.clip
        return x0 <= x < x1 and y0 <= y < y1

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h and self._in_clip(x, y):
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if self.clip is not None:
            cx0, cy0, cx1, cy1 = self.clip
            x0, y0 = max(x0, cx0), max(y0, cy0)
            x1, y1 = min(x1, cx1), min(y1, cy1)
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
# Flat vector pictograms. Each draws inside the box (x, y, w, h).
# The caller sets a clip to the box first, so a scene physically
# cannot paint outside it even if its maths overshoots.

def scene_parliament(cv, x, y, w, h):
    cv.rect(x, y, w, h, (222, 228, 232))
    # hemicycle of seats: 65 of 130 filled one colour, rest another
    cx, cy = x + w // 2, y + h - 6
    for ring, r in ((0, 78), (1, 62), (2, 46)):
        n = 26 - ring * 4
        for i in range(n):
            ang = 3.14159 * (i + 0.5) / n
            px = int(cx + r * 1.9 * (0.5 - ang / 3.14159) * 2)
            py = int(cy - r * 0.62 * (1 - abs(i - n / 2) / (n / 2)) ** 0.5
                     - 6)
            col = (20, 38, 74) if (ring * 26 + i) < 65 else (176, 42, 30)
            cv.circle(px, py, 3, col)
    cv.rect(x + w // 2 - 40, y + h - 14, 80, 6, (20, 38, 74))
    cv.text(x + 8, y + 6, "65 / 130", INK, 2, True)
    cv.text(x + w - 78, y + 6, "66 NEEDED", RED, 1, True)


def scene_market(cv, x, y, w, h):
    cv.rect(x, y, w, h, (16, 32, 58))
    # skyline
    for bx, bw, bh in ((8, 26, 46), (40, 20, 62), (66, 30, 38),
                       (102, 18, 70), (126, 24, 52), (156, 28, 44),
                       (190, 22, 66), (218, 26, 40), (248, 24, 56),
                       (278, 22, 34)):
        cv.rect(x + bx, y + h - 12 - bh, bw, bh, (70, 90, 130))
        for wy in range(y + h - 8 - bh, y + h - 12, 8):
            cv.rect(x + bx + 4, wy, 4, 4, (255, 210, 90))
    # rising chart
    cv.line(x + 10, y + h - 20, x + w - 60, y + 18, (0, 200, 120))
    cv.line(x + w - 60, y + 18, x + w - 60, y + 30, (0, 200, 120))
    cv.line(x + w - 60, y + 18, x + w - 72, y + 18, (0, 200, 120))
    cv.text(x + w - 108, y + 6, "+4.2%", (0, 200, 120), 2, True)


def scene_interview(cv, x, y, w, h):
    cv.rect(x, y, w, h, (36, 68, 120))
    cv.rect(x, y, w, h // 2, (0, 90, 180))
    cv.rect(x, y + h // 2, w, h - h // 2, (255, 210, 60))
    # desk + two microphones
    cv.rect(x + w // 2 - 70, y + h - 34, 140, 26, (90, 60, 30))
    cv.rect(x + w // 2 - 70, y + h - 38, 140, 4, (120, 84, 44))
    for mx in (x + w // 2 - 44, x + w // 2 + 34):
        cv.line(mx, y + h - 38, mx + 8, y + h - 62, INK)
        cv.circle(mx + 9, y + h - 64, 6, INK)
    # speaker silhouette
    cv.circle(x + w // 2, y + h - 62, 12, (30, 30, 30))
    cv.rect(x + w // 2 - 16, y + h - 52, 32, 16, (30, 30, 30))
    cv.text(x + 8, y + 6, "BBC", WHITE, 2, True)
    cv.text(x + w - 130, y + 6, "KYIV", WHITE, 1, True)


def scene_mini(cv, kind, x, y, w, h):
    """Small pictogram strip for the ten grid panels."""
    bg = {"drones": (24, 30, 44), "court": (232, 228, 218),
          "skater": (214, 230, 240), "tanker": (210, 226, 236),
          "chart_up": (226, 236, 224), "asia": (232, 230, 214),
          "storm": (58, 74, 96), "virus": (228, 234, 226),
          "eu": (20, 38, 74), "pillars": (232, 226, 210)}[kind]
    cv.rect(x, y, w, h, bg)
    if kind == "drones":
        for dx, dy in ((30, 8), (90, 6), (150, 10)):
            cv.rect(x + dx, y + dy + 4, 22, 4, (200, 200, 200))
            cv.circle(x + dx - 2, y + dy + 6, 3, (200, 200, 200))
            cv.circle(x + dx + 24, y + dy + 6, 3, (200, 200, 200))
        cv.circle(x + w - 30, y + h - 10, 6, (232, 120, 30))
        cv.circle(x + w - 30, y + h - 10, 3, (255, 210, 90))
        cv.text(x + 6, y + h - 12, "155", WHITE, 1, True)
    elif kind == "court":
        cv.vline(x + w // 2, y + 4, h - 10, INK, 2)
        cv.hline(x + 24, y + 8, w - 48, INK, 2)
        cv.tri(x + 30, y + 10, x + 48, y + 10, x + 39, y + 22, INK)
        cv.tri(x + w - 50, y + 10, x + w - 32, y + 10, x + w - 41, y + 22, INK)
        cv.text(x + 6, y + h - 12, "123", RED, 1, True)
    elif kind == "skater":
        cv.rect(x, y + h - 8, w, 8, (255, 255, 255))
        cv.line(x + w // 2, y + 6, x + w // 2 - 8, y + h - 12, INK)
        cv.line(x + w // 2, y + 6, x + w // 2 + 12, y + h - 16, INK)
        cv.circle(x + w // 2 + 2, y + 4, 4, INK)
        cv.line(x + w // 2 - 8, y + h - 12, x + w // 2 + 16, y + h - 12, INK)
        cv.text(x + 6, y + 4, "114.81", RED, 1, True)
    elif kind == "tanker":
        cv.poly([(x + 20, y + h - 10), (x + 30, y + 10), (x + 130, y + 16),
                 (x + 140, y + h - 10)], (60, 60, 66))
        cv.rect(x, y + h - 10, w, 10, (40, 90, 130))
        cv.circle(x + w - 24, y + 8, 5, (232, 120, 30))
        cv.circle(x + w - 40, y + 12, 4, (232, 120, 30))
        cv.text(x + 6, y + 4, "$97.71", INK, 1, True)
    elif kind == "chart_up":
        cv.line(x + 8, y + h - 8, x + w - 8, y + 8, (0, 122, 61))
        cv.line(x + w - 8, y + 8, x + w - 8, y + 18, (0, 122, 61))
        cv.line(x + w - 8, y + 8, x + w - 18, y + 8, (0, 122, 61))
        cv.text(x + 6, y + 4, "+1.6%", (0, 122, 61), 1, True)
    elif kind == "asia":
        for i, bh in enumerate((10, 16, 22, 28)):
            cv.rect(x + 14 + i * 26, y + h - 8 - bh, 16, bh,
                    (0, 122, 61) if i > 1 else (110, 108, 100))
        cv.line(x + 8, y + h - 16, x + w - 8, y + 6, (176, 42, 30))
        cv.text(x + 6, y + 4, "+2.1% +4.3%", INK, 1, True)
    elif kind == "storm":
        for cx, cy, r in ((50, 10, 10), (70, 8, 12), (90, 10, 9)):
            cv.circle(x + cx, y + cy, r, (210, 214, 220))
        for i in range(10):
            rx = x + 120 + (i * 7) % 60
            ry = y + 4 + (i * 11) % 18
            cv.line(rx, ry, rx - 3, ry + 7, (180, 200, 220))
        cv.ellipse(x + 46, y + h // 2 + 2, 26, 12, (232, 120, 30))
        cv.rect(x + 38, y + h - 8, 16, 6, (120, 72, 30))
        cv.text(x + 6, y + h - 12, "600K", WHITE, 1, True)
    elif kind == "virus":
        cv.circle(x + w // 2, y + h // 2, 9, (90, 140, 90))
        for dx, dy in ((-15, -7), (15, -7), (-15, 7), (15, 7), (0, -12)):
            cv.circle(x + w // 2 + dx, y + h // 2 + dy, 4, (90, 140, 90))
        cv.text(x + 6, y + 4, "12,021", INK, 1, True)
    elif kind == "eu":
        # 12 stars on an ellipse, offsets hand-computed (no trig needed)
        for dx, dy in ((52, 0), (45, 6), (26, 10), (0, 11), (-26, 10),
                       (-45, 6), (-52, 0), (-45, -6), (-26, -10),
                       (0, -11), (26, -10), (45, -6)):
            cv.circle(x + w // 2 + dx, y + h // 2 + dy, 2, (255, 210, 90))
        cv.text(x + 6, y + 4, "NO DEAL", (255, 210, 90), 1, True)
    elif kind == "pillars":
        cv.rect(x + 10, y + 4, w - 20, 4, (120, 108, 84))
        for cx in (30, 66, 102, 138):
            cv.rect(x + cx, y + 8, 8, h - 16, (120, 108, 84))
        cv.rect(x + 10, y + h - 8, w - 20, 4, (120, 108, 84))
        cv.text(x + 6, y + h - 12, "BILL 21", INK, 1, True)


# ---------------------------------------------------------------- data
# (scene, kicker, headline, body, source) for the three heroes.
HEROES = [
    ("parliament",
     "WELLINGTON  •  OCEANIA  •  ELECTION",
     "Coalition falls one seat short",
     "Final count: the National-led bloc holds 65 of 130 seats, "
     "one short of a majority. Newcomer Opportunity's 7 MPs hold "
     "the balance of power.",
     "REPORTED  •  Electoral Commission  •  AP  •  Reuters"),
    ("market",
     "SHANGHAI  •  EAST ASIA  •  MARKETS",
     "China stocks leap 4.2% in a day",
     "CSI 300 jumps 4.2%, its best day in two years, as Beijing "
     "vows bigger state support. Shanghai +3.7%; STAR 50 +15%.",
     "REPORTED  •  Reuters"),
    ("interview",
     "KYIV  •  EUROPE  •  WAR",
     "Zelenskyy: Putin can't be a friend",
     "In a BBC interview, Zelenskyy urges the US to press Putin "
     "harder, warning that delays to Patriot missiles are costing "
     "Ukrainian lives.",
     "ON RECORD  •  BBC  •  AP"),
]

# (number, scene kind, kicker, headline, body, source) for panels 4-13.
PANELS = [
    (4, "drones", "UKRAINE  •  WAR",
     "155 drones fired at Ukraine",
     "Air defences down 110; hits at 27 sites.",
     "REPORTED  •  Ukraine Air Force"),
    (5, "court", "MOMBASA  •  JUSTICE",
     "Cult chief guilty: 123 dead",
     "Mackenzie convicted over Shakahola fasts.",
     "OFFICIAL  •  Court  •  Reuters"),
    (6, "skater", "TOKYO  •  SPORT",
     "Malinin sets world record",
     "114.81 in the short program at NHK Trophy.",
     "REPORTED  •  AP  •  Reuters"),
    (7, "tanker", "HORMUZ  •  ENERGY",
     "Brent nears $98 on mine hits",
     "Two tankers hit mines, IRGC says; Jazan hit.",
     "CLAIM  •  IRGC  •  Reuters"),
    (8, "chart_up", "NEW YORK  •  MARKETS",
     "Best week in 19 months",
     "S&P 500 +1.6% to 7,297.49; Nasdaq +2.3%.",
     "REPORTED  •  AP"),
    (9, "asia", "ASIA  •  MARKETS",
     "Asia markets surge on AI",
     "Nikkei +2.11% to 58,711; Kospi +4.3%.",
     "REPORTED  •  Yonhap  •  Reuters"),
    (10, "storm", "NEW YORK  •  WEATHER",
     "600,000 dark on Black Friday",
     "Macy's 100th parade moves to Saturday, a first.",
     "REPORTED  •  NPR  •  Reuters"),
    (11, "virus", "CONGO  •  HEALTH",
     "Ebola passes 12,000 cases",
     "12,021 confirmed; 5,904 dead; fighting hampers response.",
     "OFFICIAL  •  Health Ministry"),
    (12, "eu", "BRUSSELS  •  POLITICS",
     "EU summit ends with no deal",
     "24 states back a 45bn euro Ukraine loan; talks resume Dec.",
     "REPORTED  •  Xinhua"),
    (13, "pillars", "OTTAWA  •  RIGHTS",
     "Court upholds Quebec Bill 21",
     "Notwithstanding clause stands; one section struck down.",
     "OFFICIAL  •  Supreme Court"),
]

# (number, place, one-line story) for the 39 more stories.
# Kept short on purpose: place + " — " + text must fit one column
# (about 52 chars at scale 1); the draw loop truncates as a backstop.
ALSO = [
    (14, "LONDON", "DWP cyber incident takes benefits offline"),
    (15, "OSLO", "Norse Atlantic files for bankruptcy"),
    (16, "MADRID", "Spain campaign ends; vote on Sunday"),
    (17, "BELGRADE", "Students pick chemist Saicic for president"),
    (18, "SEOUL", "Seoul returns six North Koreans found adrift"),
    (19, "MADURAI", "Top court orders lamp lit on disputed hill"),
    (20, "LUSAIL", "Antonelli fastest in Qatar GP practice"),
    (21, "MELBOURNE", "North Melbourne win AFLW three-peat, 44-18"),
    (22, "MARSEILLE", "Fan violence: UEFA opens inquiry"),
    (23, "EAST DARFUR", "RSF raids kill 14 in Darfur and Kordofan"),
    (24, "WALLDORF", "SAP weighs 10,000+ job cuts in AI push"),
    (25, "MARIANA TRENCH", "Deepest eruption found 6.5 km down"),
    (26, "MEXICO CITY", "Mexico protests US drug tip line"),
    (27, "BOGOR", "Search ends for 14 lost miners"),
    (28, "BLACK FRIDAY", "Half of sale prices no cheaper"),
    (29, "AI", "Anthropic turns Claude artifacts into apps"),
    (30, "MALI", "300+ Russians killed backing junta"),
    (31, "INDIA", "Politician hosts a 400,000-guest wedding"),
    (32, "GERMANY", "Two Iraqis held over synagogue attack plot"),
    (33, "USA", "Judge: FCC violated ABC's free speech"),
    (34, "INDIA", "Cabinet backs Rs 11,000-cr factory scheme"),
    (35, "TECH", "Nvidia halts chip sales to 4 SE Asian states"),
    (36, "SOUTH KOREA", "Bank of Korea lifts rates on AI boom"),
    (37, "NORTH KOREA", "Kim vows permanent nuclear armament"),
    (38, "MEDITERRANEAN", "65 terror suspects held in sweep"),
    (39, "USA", "Flights to Washington DCA grounded in storm"),
    (40, "FIFA", "Hackers accessed limited personal data"),
    (41, "RUGBY", "Barrett to captain All Blacks vs England"),
    (42, "NFL", "Rams beat Packers 26-13; Corum runs 184 yards"),
    (43, "CHESS", "Gukesh, Sindarov draw Game 3, 1.5-1.5"),
    (44, "FRANCE", "Macron slams Le Pen as mainstream falters"),
    (45, "USA", "Musk: every US child gets 2 SpaceX shares"),
    (46, "WASHINGTON", "Trump seeks probe into 'fake' GDP"),
    (47, "NEW DELHI", "India court: judge must sit on PMLA bench"),
    (48, "NEPAL", "Nepal declares 4,000 landslide missing dead"),
    (49, "BELGIUM", "Europe's biggest satellite factory opens"),
    (50, "BERLIN", "Bundestag passes 2027 budget"),
    (51, "KARACHI", "Collapse toll rises to 6; rescue goes on"),
    (52, "MAR-A-LAGO", "Trump welcomes Putin to G20"),
]

REGIONS = [
    ("EUROPE", 14, (176, 42, 30)), ("N. AMERICA", 9, (20, 38, 74)),
    ("EAST ASIA", 6, (0, 140, 160)), ("SOUTH ASIA", 6, (150, 60, 140)),
    ("OCEANIA", 4, (60, 120, 200)), ("AFRICA", 4, (200, 130, 20)),
    ("GLOBAL", 4, (110, 108, 100)), ("MIDDLE EAST", 2, (0, 122, 61)),
    ("SE ASIA", 2, (200, 90, 0)), ("LATIN AMERICA", 1, (90, 140, 90)),
]

STATS = [
    ("65/130", "NZ coalition seats: one short of a majority"),
    ("+4.2%", "CSI 300, best day in two years"),
    ("155", "Russian drones fired at Ukraine overnight"),
    ("114.81", "Malinin's world-record short program"),
    ("$97.71", "Brent intraday as Gulf attacks lift oil"),
    ("12,021", "Ebola cases in Congo, and still rising"),
]

# (UTC time, event) for the wire-times strip. Times are the hour the
# event was reported or the market closed, all on Friday 27 Nov.
TIMELINE = [
    ("01:00", "NZ final count"),
    ("06:00", "Nikkei +2.11%"),
    ("07:45", "Brent $97.71"),
    ("11:22", "Zelenskyy to BBC"),
    ("16:21", "Norse bankrupt"),
    ("18:00", "S&P 500 +1.60%"),
]

# (lon, lat) pins for pictured stories 1-13 on the dotted map.
PINS = {1: (174.8, -41.3), 2: (121.5, 31.2), 3: (30.5, 50.45),
        4: (36.2, 49.99), 5: (39.7, -4.05), 6: (139.7, 35.7),
        7: (56.3, 26.6), 8: (-74.0, 40.7), 9: (127.0, 37.5),
        10: (-77.0, 38.9), 11: (30.25, 1.57), 12: (4.35, 50.85),
        13: (-75.7, 45.4)}

# Leader offsets (dx, dy) for pins that would collide at map scale.
PIN_OFFSET = {1: (0, 0), 2: (0, 0), 3: (-14, -10), 4: (12, 12),
              5: (0, 0), 6: (0, 0), 7: (0, 0), 8: (-12, -10),
              9: (14, -8), 10: (12, 12), 11: (0, 0), 12: (-14, 10),
              13: (0, 0)}

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


def point_in_poly(px, py, poly):
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > py) != (y1 > py):
            xin = x0 + (py - y0) * (x1 - x0) / (y1 - y0)
            if px < xin:
                inside = not inside
    return inside


# ---------------------------------------------------------------- layout
def draw(cv):
    cv.rect(0, 0, W, H, PAPER)

    # --- top bar
    cv.rect(0, 0, W, 24, NAVY)
    cv.text_c(W // 2, 8, "THE WORLD IN ONE DAY  •  52 STORIES  •  10 REGIONS  •  "
              "ALL FIRST REPORTED FRIDAY 27 NOVEMBER 2026", WHITE, 1, True)

    # --- masthead
    cv.text_c(W // 2, 30, "Friday 27 November 2026", INK, 6, True)
    cv.rect(60, 80, W - 120, 3, RED)

    # --- ticker
    cv.text_c(W // 2, 88,
              "NZ coalition one short  •  China stocks +4.2%  •  "
              "Zelenskyy: press Putin harder", RED, 2, True)

    # --- six key figures
    y0 = 112
    cv.hline(8, y0 - 2, W - 16, INK, 2)
    bw = (W - 16) // 6
    for i, (num, label) in enumerate(STATS):
        bx = 8 + i * bw
        if i:
            cv.vline(bx, y0 + 2, 52, GREY, 1)
        cv.text_c(bx + bw // 2, y0 + 2, num, RED, 4, True)
        for j, ln in enumerate(wrap_text(label, bw - 10, 1)):
            cv.text_c(bx + bw // 2, y0 + 34 + j * 8, ln, INK, 1)
    cv.hline(8, y0 + 56, W - 16, INK, 2)

    # --- region strip
    y0 = 174
    x = 8
    chip_w = (W - 16) // len(REGIONS)
    for name, n, col in REGIONS:
        cv.rect(x, y0, chip_w - 3, 20, col)
        cv.text_c(x + (chip_w - 3) // 2, y0 + 6, "%s %d" % (name, n),
                  WHITE, 1, True)
        x += chip_w

    # --- wire-times strip
    y0 = 200
    cv.text(8, y0 + 2, "WIRE TIMES, UTC", INK, 1, True)
    tx = 118
    slot = (W - 8 - tx) // len(TIMELINE)
    for t, ev in TIMELINE:
        cv.text(tx, y0 + 2, t, RED, 1, True)
        cv.text(tx + 36, y0 + 2, ev, INK, 1)
        tx += slot
    cv.hline(8, y0 + 18, W - 16, INK, 1)

    # --- three hero stories
    hy, hh = 226, 244
    hw = (W - 16 - 12) // 3
    for i, (scene, kicker, head, body, src) in enumerate(HEROES):
        hx = 8 + i * (hw + 6)
        cv.rect(hx, hy, hw, hh, WHITE)
        cv.rect(hx, hy, hw, 1, INK)
        cv.rect(hx, hy + hh - 1, hw, 1, INK)
        cv.rect(hx, hy, 1, hh, INK)
        cv.rect(hx + hw - 1, hy, 1, hh, INK)
        sy = hy + 4
        cv.set_clip(hx + 4, sy, hw - 8, 104)
        if scene == "parliament":
            scene_parliament(cv, hx + 4, sy, hw - 8, 104)
        elif scene == "market":
            scene_market(cv, hx + 4, sy, hw - 8, 104)
        else:
            scene_interview(cv, hx + 4, sy, hw - 8, 104)
        cv.clear_clip()
        ty = sy + 108
        cv.rect(hx + 4, ty, 22, 14, RED)
        cv.text(hx + 7, ty + 3, str(i + 1), WHITE, 1, True)
        cv.text(hx + 30, ty + 3, kicker, RED, 1, True)
        ty += 18
        for ln in wrap_text(head, hw - 12, 3):
            cv.text(hx + 6, ty, ln, INK, 3, True)
            ty += 24
        ty += 2
        for ln in wrap_text(body, hw - 12, 1)[:3]:
            cv.text(hx + 6, ty, ln, INK, 1)
            ty += 8
        ty += 4
        cv.text(hx + 6, ty, src, GREY, 1)

    # --- ten pictured panels, 5 x 2
    gy = 478
    pw, ph = 200, 128
    for idx, (num, kind, kicker, head, body, src) in enumerate(PANELS):
        px = 4 + (idx % 5) * (pw + 4)
        py = gy + (idx // 5) * (ph + 4)
        cv.rect(px, py, pw, ph, WHITE)
        cv.rect(px, py, pw, 1, INK)
        cv.rect(px, py + ph - 1, pw, 1, INK)
        cv.rect(px, py, 1, ph, INK)
        cv.rect(px + pw - 1, py, 1, ph, INK)
        cv.set_clip(px + 3, py + 3, pw - 6, 34)
        scene_mini(cv, kind, px + 3, py + 3, pw - 6, 34)
        cv.clear_clip()
        ty = py + 40
        cv.rect(px + 3, ty, 16, 12, NAVY)
        cv.text(px + 5, ty + 2, str(num), WHITE, 1, True)
        cv.text(px + 22, ty + 2, kicker, RED, 1, True)
        ty += 15
        for ln in wrap_text(head, pw - 8, 2)[:2]:
            cv.text(px + 4, ty, ln, INK, 2, True)
            ty += 15
        ty += 1
        for ln in wrap_text(body, pw - 8, 1)[:2]:
            cv.text(px + 4, ty, ln, INK, 1)
            ty += 8
        cv.text(px + 4, py + ph - 12, src, GREY, 1)

    # --- dotted map + also list
    my = 746
    mh = 232
    cv.rect(4, my, 296, mh, WHITE)
    cv.rect(4, my, 296, 1, INK)
    cv.rect(4, my + mh - 1, 296, 1, INK)
    cv.rect(4, my, 1, mh, INK)
    cv.rect(299, my, 1, mh, INK)
    cv.text(12, my + 6, "WHERE IT HAPPENED", INK, 1, True)
    cv.text(12, my + 16, "dots = story numbers 1-13", GREY, 1)
    mx, myy = 4, my + 28
    for gy2 in range(0, 170, 7):
        for gx2 in range(0, 296, 7):
            if any(point_in_poly(gx2, gy2, poly) for poly in CONTINENTS):
                cv.rect(mx + gx2, myy + gy2, 2, 2, (150, 142, 122))
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
    cv.text(12, my + mh - 30,
            "HOW SURE: REPORTED = the day's wires;", GREY, 1)
    cv.text(12, my + mh - 20,
            "CLAIM = one side, unconfirmed; OFFICIAL =", GREY, 1)
    cv.text(12, my + mh - 10,
            "authority's own count or ruling.", GREY, 1)

    ax = 312
    cv.text(ax, my + 6, "ALSO ON FRIDAY 27 NOVEMBER — 39 MORE STORIES",
            INK, 1, True)
    cv.hline(ax, my + 18, W - ax - 8, INK, 2)
    col_w = (W - ax - 8) // 2
    for idx, (num, place, text) in enumerate(ALSO):
        col = idx // 20
        row = idx % 20
        lx = ax + col * col_w
        ly = my + 26 + row * 10
        cv.rect(lx, ly, 18, 10, NAVY)
        cv.text(lx + 2 if num < 10 else lx + 1, ly + 2, str(num),
                WHITE, 1, True)
        line = place + " — " + text
        while text_w(line, 1) > col_w - 24 and " " in line:
            line = line.rsplit(" ", 1)[0]
        cv.text(lx + 22, ly + 2, line, INK, 1)

    # --- footer
    fy = 986
    cv.rect(0, fy, W, H - fy, NAVY)
    cv.text(8, fy + 5,
            "DATE CHECK  Every story above happened or was first reported "
            "on Friday 27 November 2026.", WHITE, 1, True)
    cv.text(8, fy + 15,
            "NOT 27 NOV: Kuwait drone strike kills 2 (Thu 26)  •  Gaza "
            "strikes kill 10 (Thu 26)  •  Ibiza tanker sinks, 1 dead "
            "(Thu 26)  •  Bangkok refinery blast (Thu 26)", (200, 205, 215), 1)
    cv.text(8, fy + 25,
            "NOT 27 NOV: Depardieu sent to trial (Thu 26)  •  ONS "
            "migration 77,000 (Thu 26)  •  Karachi collapse (Wed 25)  •  "
            "US tariff plan (25 Nov)  •  Sources: AP, Reuters, BBC.",
            (200, 205, 215), 1)


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
