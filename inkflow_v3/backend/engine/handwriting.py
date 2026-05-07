"""InkFlow v3 — Handwriting Engine"""
import io, math, random
from typing import Optional
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageEnhance

CELL_PAD_FRAC = 0.08

# Characters that have descenders (parts below the baseline)
DESCENDERS = set("gjpqyÖÄÜöäüß")
# Characters that are typically short (x-height only)
SHORT_CHARS = set("acemnorsuvwxz.,-:;")

def _clean_cell(cell_bgr):
    pad = int(min(cell_bgr.shape[:2]) * CELL_PAD_FRAC)
    cropped = cell_bgr[pad:-pad, pad:-pad] if pad > 0 else cell_bgr.copy()
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    _, t1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    t2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 11, 6)
    thresh = cv2.bitwise_or(t1, t2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((2,2), np.uint8))
    if np.count_nonzero(thresh) < 30: return None
    coords = cv2.findNonZero(thresh)
    x, y, bw, bh = cv2.boundingRect(coords)
    m = 6
    x, y = max(0,x-m), max(0,y-m)
    bw = min(cropped.shape[1]-x, bw+2*m)
    bh = min(cropped.shape[0]-y, bh+2*m)
    char_crop = cropped[y:y+bh, x:x+bw]
    alpha = thresh[y:y+bh, x:x+bw]
    bgra = cv2.cvtColor(char_crop, cv2.COLOR_BGR2BGRA)
    bgra[:,:,3] = alpha
    return bgra

def segment_single_char(img_bgr):
    return _clean_cell(img_bgr)

def _colorize(img, hex_color):
    r,g,b = int(hex_color[1:3],16), int(hex_color[3:5],16), int(hex_color[5:7],16)
    alpha = img.split()[3]
    colored = Image.new("RGBA", img.size, (r,g,b,255))
    colored.putalpha(alpha)
    return colored

def _jitter(v, var): return v * (1.0 + random.uniform(-var, var))

def _make_paper(paper, line_height=None):
    """Create paper background. If line_height is provided, use it for line spacing."""
    img = Image.new("RGBA", (paper.width, paper.height), paper.color)
    draw = ImageDraw.Draw(img)
    if paper.type == "lined":
        # Use configured line height for line spacing, matching the text rendering
        lh = int(line_height) if line_height else 80
        for y in range(paper.margin_top + lh, paper.height - 60, lh):
            draw.line([(paper.margin_left, y), (paper.width - paper.margin_left, y)],
                      fill=paper.line_color, width=1)
    elif paper.type == "grid":
        for y in range(0, paper.height, 60):
            draw.line([(0,y),(paper.width,y)], fill=paper.line_color, width=1)
        for x in range(0, paper.width, 60):
            draw.line([(x,0),(x,paper.height)], fill=paper.line_color, width=1)
    elif paper.type == "dot":
        for y in range(60, paper.height, 60):
            for x in range(60, paper.width, 60):
                draw.ellipse([(x-2,y-2),(x+2,y+2)], fill=paper.line_color)
    arr = np.array(img).astype(np.float32)
    noise = np.random.normal(0, 2.0, arr.shape[:2])
    for c in range(3): arr[:,:,c] = np.clip(arr[:,:,c]+noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def _compute_baseline_offset(char: str, char_height: int, variant_baseline: int) -> int:
    """
    Compute vertical offset so characters sit on the baseline correctly.
    - Descenders (g, y, p, q, j): extend below baseline
    - Normal characters: bottom aligned to baseline
    """
    if variant_baseline != 0:
        # Use stored baseline offset from training
        return variant_baseline

    # Auto-compute: descenders get ~25% of their height below baseline
    if char in DESCENDERS:
        return -int(char_height * 0.25)

    return 0


def render_text_to_pages(profile, settings):
    paper = settings.paper
    pages, words, wi = [], settings.text.split(), 0

    # Use line_height_override if set, otherwise profile default
    base_line_height = (settings.line_height_override
                        if hasattr(settings, 'line_height_override') and settings.line_height_override
                        else profile.line_height)

    while wi < len(words):
        page = _make_paper(paper, line_height=base_line_height * settings.font_size_scale)
        x, y = float(paper.margin_left), float(paper.margin_top)
        line_h = base_line_height * settings.font_size_scale
        max_x, max_y = paper.width - paper.margin_left, paper.height - paper.margin_top
        while wi < len(words) and y + line_h < max_y:
            word = words[wi]
            ww = sum((
                (sum(v.width for v in profile.characters.get(c,[])) /
                 max(len(profile.characters.get(c,[])),1)
                 if profile.characters.get(c) else profile.avg_char_width
                ) * settings.font_size_scale + profile.char_spacing
                for c in word
            ))
            if x > paper.margin_left and x + ww > max_x:
                x = float(paper.margin_left)
                y += line_h * _jitter(1.0, 0.08)
            if y + line_h > max_y: break
            x = _render_word(page, word, x, y, line_h, profile, settings)
            x += profile.word_spacing * _jitter(1.0, settings.spacing_variation)
            wi += 1
        pages.append(page)
    return pages or [_make_paper(paper, line_height=base_line_height * settings.font_size_scale)]

def _render_word(page, word, x, y, line_h, profile, settings):
    for char in word:
        variants = profile.characters.get(char, [])
        if not variants:
            x += profile.avg_char_width * settings.font_size_scale
            continue
        variant = random.choice(variants)
        try: char_img = Image.open(variant.image_path).convert("RGBA")
        except: x += profile.avg_char_width * settings.font_size_scale; continue

        scale = settings.font_size_scale * _jitter(1.0, settings.size_variation)
        new_w, new_h = max(4,int(char_img.width*scale)), max(4,int(char_img.height*scale))
        char_img = char_img.resize((new_w,new_h), Image.LANCZOS)

        # Subtle micro-rotation for human touch (±0.5°) — layered on top of user-configured rotation
        micro_rotation = random.uniform(-0.5, 0.5)
        angle = random.uniform(-settings.rotation_variation, settings.rotation_variation) + micro_rotation
        if abs(angle) > 0.3:
            char_img = char_img.rotate(angle, expand=True, resample=Image.BICUBIC)

        if settings.ink_pressure_variation > 0:
            alpha = char_img.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(
                max(0.3, _jitter(1.0, settings.ink_pressure_variation)))
            char_img.putalpha(alpha)

        char_img = _colorize(char_img, profile.ink_color)

        # Baseline alignment: place character so its bottom sits on the baseline
        # baseline is at y + line_h (bottom of the line)
        baseline_y = y + line_h
        baseline_offset = _compute_baseline_offset(char, new_h, variant.baseline_offset)

        # Y position: baseline minus character height, plus any descender offset
        y_pos = baseline_y - char_img.height + baseline_offset

        # Subtle micro-jitter for position (±1px) — human touch layer
        micro_jitter_x = random.uniform(-1.0, 1.0)
        micro_jitter_y = random.uniform(-1.0, 1.0)

        # User-configured vertical jitter
        vy = random.uniform(-settings.vertical_jitter, settings.vertical_jitter)

        page.paste(char_img, (int(x + micro_jitter_x), int(y_pos + vy + micro_jitter_y)), char_img)
        x += char_img.width + profile.char_spacing * _jitter(1.0, 0.3)
        if random.random() < settings.word_break_probability:
            x += random.uniform(2, 5)
    return x
