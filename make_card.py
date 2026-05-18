#!/usr/bin/env python3
"""
make_card.py  –  Docket Duel nutrition card generator
======================================================
Layout
------
  Top-left  corner  : product image (thumbnail)
  Top-right corner  : Aldi logo
  Bottom-left corner: Aldi logo
  Bottom-right corner: product image (thumbnail)
  Centre panel      : product name + nutrition stats table + price

Usage – single card
-------------------
  python make_card.py products.json --id goldenvale-just-bran

Usage – batch (all products in JSON)
--------------------------------------
  python make_card.py products.json

The JSON is the Docket Duel products.json format.
Cards are written to  ./cards/<product-id>.png
"""

import argparse
import json
import os
import re
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Missing dependency — run:  pip install Pillow")

# ── card dimensions ──────────────────────────────────────────────────────────
W, H         = 630, 880
CARD_R       = 40          # outer corner radius
BORDER_W     = 6
INNER_OFF    = 16          # inner border inset
INNER_R      = 32

# ── corner thumbnails ────────────────────────────────────────────────────────
CORNER_SZ    = 150         # square size of each corner block
CORNER_PAD   = 28          # distance from card edge
CORNER_R     = 12          # corner block radius

# ── colour palette ────────────────────────────────────────────────────────────
ALDI_BLUE    = (0,  61, 165)
ALDI_ORANGE  = (255, 102, 0)
HEADER_BG    = ALDI_BLUE
HEADER_FG    = (255, 255, 255)
ROW_A        = (240, 245, 255)   # alternating row colours
ROW_B        = (255, 255, 255)
ROW_FG       = (30,  30,  30)
PRICE_BG     = ALDI_ORANGE
PRICE_FG     = (255, 255, 255)
CARD_BG      = (250, 250, 255)
BORDER_COL   = (0,   0,   0)

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR    = os.path.join(SCRIPT_DIR, "cards")
ALDI_PNG     = os.path.join(SCRIPT_DIR, "aldi.png")


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def rounded_rect_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size[0]-1, size[1]-1], radius=radius, fill=255)
    return mask


def paste_rounded(base, img, xy, size, radius):
    thumb = img.resize(size, Image.LANCZOS)
    mask  = rounded_rect_mask(size, radius)
    base.paste(thumb, xy, mask)


def best_font(size, bold=False):
    candidates_bold = [
        "arialbd.ttf", "Arial Bold.ttf", "Arial_Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    candidates_reg = [
        "arial.ttf", "Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in (candidates_bold if bold else candidates_reg):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def fit_font_width(text, start_size, max_width, min_size=14, bold=False):
    size = start_size
    while size >= min_size:
        font = best_font(size, bold)
        bbox = font.getbbox(text)
        if (bbox[2] - bbox[0]) <= max_width:
            return font
        size -= 1
    return best_font(min_size, bold)


def parse_price(raw):
    """Accept numeric or '$X.XX' string, return float."""
    if isinstance(raw, (int, float)):
        return float(raw)
    return float(re.sub(r"[^\d.]", "", str(raw)))


# ─────────────────────────────────────────────────────────────────────────────
# core card builder
# ─────────────────────────────────────────────────────────────────────────────

def make_card(product: dict, json_dir: str) -> str:
    pid        = product["id"]
    name       = product["name"]
    pack_size  = product.get("pack_size", "")
    nutr       = product.get("nutrition_per", {})
    price      = parse_price(product.get("pricing", {}).get("price_aud", 0))

    image_path = os.path.join(json_dir, product["image"].lstrip("./"))
    if not os.path.exists(image_path):
        print(f"WARN  image not found, skipping: {image_path}")
        return None

    # ── base card ─────────────────────────────────────────────────────────────
    card = Image.new("RGBA", (W, H), CARD_BG + (255,))
    draw = ImageDraw.Draw(card)

    # ── load assets ───────────────────────────────────────────────────────────
    prod_img = Image.open(image_path).convert("RGBA")
    aldi_img = Image.open(ALDI_PNG).convert("RGBA") if os.path.exists(ALDI_PNG) else None

    cs  = CORNER_SZ
    cp  = CORNER_PAD
    cr  = CORNER_R

    def corner_block(img, bg=(255, 255, 255)):
        block = Image.new("RGBA", (cs, cs), bg + (255,))
        copy  = img.copy()
        copy.thumbnail((cs - 10, cs - 10), Image.LANCZOS)
        cw, ch = copy.size
        block.paste(copy, ((cs - cw) // 2, (cs - ch) // 2), copy)
        return block

    prod_block = corner_block(prod_img)
    aldi_block = corner_block(aldi_img) if aldi_img else prod_block

    # top-left  = product image
    paste_rounded(card, prod_block.convert("RGB"), (cp, cp), (cs, cs), cr)
    # top-right = aldi logo
    paste_rounded(card, aldi_block.convert("RGB"), (W - cp - cs, cp), (cs, cs), cr)
    # bottom-left  = aldi logo
    paste_rounded(card, aldi_block.convert("RGB"), (cp, H - cp - cs), (cs, cs), cr)
    # bottom-right = product image
    paste_rounded(card, prod_block.convert("RGB"), (W - cp - cs, H - cp - cs), (cs, cs), cr)

    # corner outlines
    for xy in [
        (cp, cp, cp+cs, cp+cs),
        (W-cp-cs, cp, W-cp, cp+cs),
        (cp, H-cp-cs, cp+cs, H-cp),
        (W-cp-cs, H-cp-cs, W-cp, H-cp),
    ]:
        draw.rounded_rectangle(xy, radius=cr, outline=(180, 180, 180), width=1)

    # ── centre stats panel ────────────────────────────────────────────────────
    # Panel sits between the corner blocks, with a little breathing room
    panel_x1 = cp + cs + 12
    panel_x2 = W - cp - cs - 12
    panel_y1 = cp + 8
    panel_y2 = H - cp - 8
    panel_w  = panel_x2 - panel_x1

    # product name header
    header_h = 56
    draw.rounded_rectangle(
        [panel_x1, panel_y1, panel_x2, panel_y1 + header_h],
        radius=10, fill=HEADER_BG)

    name_font = fit_font_width(name, 18, panel_w - 10, min_size=10, bold=True)
    # wrap name if it still overflows (rare but safe)
    draw.text(
        (panel_x1 + panel_w // 2, panel_y1 + header_h // 2),
        name, font=name_font, fill=HEADER_FG, anchor="mm")

    # pack size sub-header
    sub_y = panel_y1 + header_h + 4
    sub_font = best_font(13)
    draw.text(
        (panel_x1 + panel_w // 2, sub_y + 8),
        pack_size, font=sub_font, fill=(80, 80, 80), anchor="mm")

    # ── nutrition rows ─────────────────────────────────────────────────────────
    rows = [
        ("Energy",         f"{nutr.get('energy_kj', '-')} kJ"),
        ("Protein",        f"{nutr.get('protein_g', '-')} g"),
        ("Fat Total",      f"{nutr.get('fat_total_g', '-')} g"),
        ("Saturated Fat",  f"{nutr.get('saturated_fat_g', '-')} g"),
        ("Carbohydrate",   f"{nutr.get('carbohydrate_g', '-')} g"),
        ("Sugars",         f"{nutr.get('sugars_g', '-')} g"),
        ("Dietary Fibre",  f"{nutr.get('dietary_fibre_g', '-')} g"),
        ("Sodium",         f"{nutr.get('sodium_mg', '-')} mg"),
    ]

    table_top   = sub_y + 20
    # how much vertical space remains above the price banner?
    price_h     = 50
    price_gap   = 10
    table_bot   = panel_y2 - price_h - price_gap
    row_count   = len(rows)
    row_h       = max(26, (table_bot - table_top) // row_count)

    # clamp so table doesn't overflow
    if table_top + row_h * row_count > table_bot:
        row_h = (table_bot - table_top) // row_count

    label_font = best_font(13, bold=False)
    val_font   = best_font(13, bold=True)
    per_font   = best_font(10)

    # "per 100g" label
    draw.text(
        (panel_x2, table_top - 2),
        "per 100g", font=per_font, fill=(120, 120, 120), anchor="rs")

    for i, (label, value) in enumerate(rows):
        ry   = table_top + i * row_h
        fill = ROW_A if i % 2 == 0 else ROW_B
        draw.rectangle([panel_x1, ry, panel_x2, ry + row_h - 1], fill=fill)
        # left label
        draw.text((panel_x1 + 6, ry + row_h // 2),
                  label, font=label_font, fill=ROW_FG, anchor="lm")
        # right value
        draw.text((panel_x2 - 6, ry + row_h // 2),
                  value, font=val_font, fill=ALDI_BLUE, anchor="rm")

    # divider line under table
    div_y = table_top + row_count * row_h + 3
    draw.line([(panel_x1, div_y), (panel_x2, div_y)], fill=(200, 200, 200), width=1)

    # ── price banner ──────────────────────────────────────────────────────────
    price_y1 = panel_y2 - price_h
    draw.rounded_rectangle(
        [panel_x1, price_y1, panel_x2, panel_y2],
        radius=10, fill=PRICE_BG)
    price_font = best_font(22, bold=True)
    draw.text(
        (panel_x1 + panel_w // 2, price_y1 + price_h // 2),
        f"${price:.2f}", font=price_font, fill=PRICE_FG, anchor="mm")

    # ── outer borders ─────────────────────────────────────────────────────────
    draw.rounded_rectangle(
        [2, 2, W-3, H-3], radius=CARD_R, outline=BORDER_COL, width=BORDER_W)
    draw.rounded_rectangle(
        [INNER_OFF, INNER_OFF, W-INNER_OFF-1, H-INNER_OFF-1],
        radius=INNER_R, outline=BORDER_COL, width=2)

    # ── save with rounded mask ────────────────────────────────────────────────
    os.makedirs(CARDS_DIR, exist_ok=True)
    out_path = os.path.join(CARDS_DIR, f"{pid}.png")
    card_mask = rounded_rect_mask((W, H), CARD_R)
    out = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    out.paste(card, (0, 0), card_mask)
    out.convert("RGB").save(out_path, "PNG")
    print(f"OK   {out_path}")
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# JSON loading  (tolerates the slightly-malformed source file)
# ─────────────────────────────────────────────────────────────────────────────

def load_products(json_path: str) -> list:
    with open(json_path, encoding="utf-8") as f:
        raw = f.read()

    # Fix bare $X.XX values → "X.XX" strings so json.loads doesn't choke
    raw = re.sub(r':\s*\$(\d+\.?\d*)', r': "\1"', raw)

    # Wrap the whole thing in [ … ] if it isn't already an array
    stripped = raw.strip()
    if not stripped.startswith("["):
        # The file is a sequence of objects separated by whitespace/commas
        # Wrap in array brackets
        stripped = "[" + stripped + "]"
        # Remove any double commas that might appear between top-level objects
        stripped = re.sub(r'\}\s*\{', '},{', stripped)

    return json.loads(stripped)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate Docket Duel nutrition cards from products.json")
    parser.add_argument("json", help="Path to products.json")
    parser.add_argument(
        "--id", default=None,
        help="Generate a single card by product id (omit for batch)")
    args = parser.parse_args()

    json_dir  = os.path.dirname(os.path.abspath(args.json))
    products  = load_products(args.json)

    if args.id:
        matches = [p for p in products if p["id"] == args.id]
        if not matches:
            sys.exit(f"No product found with id '{args.id}'")
        make_card(matches[0], json_dir)
    else:
        ok = fail = 0
        for p in products:
            result = make_card(p, json_dir)
            if result:
                ok += 1
            else:
                fail += 1
        print(f"\nDone — {ok} cards generated, {fail} skipped.")


if __name__ == "__main__":
    main()