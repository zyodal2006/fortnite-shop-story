import os
import io
import math
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
 
# =========================
# KOINZ - FORTNITE SHOP
# =========================
 
W, H = 1080, 1920
OUT_DIR = "stories"
TOTAL_PAGES = 3
COLS = 6
 
BG = (8, 7, 18)
PURPLE = (153, 70, 255)
WHITE = (255, 255, 255)
MUTED = (190, 180, 210)
 
API_URL = "https://fortnite-api.com/v2/shop?language=en"
 
 
def get_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()
 
 
def centered(draw, xy, text, font, fill):
    # Pillow uses libraqm for connected Arabic text when available.
    try:
        draw.text(
            xy, text, font=font, fill=fill, anchor="mm",
            direction="rtl"
        )
    except (TypeError, ValueError):
        draw.text(xy, text, font=font, fill=fill, anchor="mm")
 
 
def make_background():
    img = Image.new("RGBA", (W, H), BG + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
 
    d.ellipse((-300, -240, 600, 450), fill=(125, 35, 255, 105))
    d.ellipse((600, 1250, 1400, 2050), fill=(85, 20, 220, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(145))
 
    return Image.alpha_composite(img, glow).convert("RGB")
 
 
def get_objects(entry):
    for key in (
        "brItems", "tracks", "instruments", "cars",
        "legoKits", "beans", "items"
    ):
        value = entry.get(key)
        if isinstance(value, list) and value:
            return value
    return []
 
 
def get_name(entry):
    objects = get_objects(entry)
 
    if objects:
        obj = objects[0]
        return (
            obj.get("name")
            or obj.get("title")
            or entry.get("devName")
            or "Fortnite Item"
        )
 
    return (
        entry.get("devName")
        or entry.get("name")
        or "Fortnite Item"
    )
 
 
def get_category(entry):
    objects = get_objects(entry)
 
    if not objects:
        return "OTHER"
 
    obj = objects[0]
    typ = obj.get("type") or {}
    raw = (
        str(typ.get("value", "")) + " " +
        str(typ.get("displayValue", ""))
    ).lower()
 
    if "outfit" in raw or "skin" in raw:
        return "SKINS"
    if "emote" in raw:
        return "EMOTES"
    if "pickaxe" in raw or "harvesting tool" in raw:
        return "PICKAXES"
    if "backpack" in raw or "back bling" in raw:
        return "BACK BLINGS"
    if "glider" in raw:
        return "GLIDERS"
    if "wrap" in raw:
        return "WRAPS"
    if "contrail" in raw:
        return "CONTRAILS"
    if "shoe" in raw or "sneaker" in raw:
        return "SNEAKERS"
    if "instrument" in raw:
        return "INSTRUMENTS"
    if "jam track" in raw or "music" in raw:
        return "MUSIC"
 
    return "OTHER"
 
 
def get_image_url(entry):
    objects = get_objects(entry)
 
    for obj in objects:
        images = obj.get("images") or {}
 
        # Prefer the locker-style icon.
        for key in ("icon", "smallIcon", "featured", "large"):
            if images.get(key):
                return images[key]
 
    images = entry.get("images") or {}
    for key in ("icon", "smallIcon", "featured", "large"):
        if images.get(key):
            return images[key]
 
    bundle = entry.get("bundle") or {}
    if bundle.get("image"):
        return bundle["image"]
 
    return None
 
 
def load_items():
    print("Fetching Fortnite item shop...")
 
    response = requests.get(API_URL, timeout=40)
    response.raise_for_status()
    payload = response.json()
 
    if payload.get("status") != 200:
        raise RuntimeError("Fortnite API returned an error.")
 
    entries = (payload.get("data") or {}).get("entries") or []
 
    if not entries:
        raise RuntimeError("No shop entries found in API response.")
 
    items = []
    seen = set()
 
    for entry in entries:
        image_url = get_image_url(entry)
        if not image_url:
            continue
 
        name = get_name(entry).strip()
        key = (name, image_url)
 
        if key in seen:
            continue
        seen.add(key)
 
        items.append({
            "name": name,
            "image": image_url,
            "category": get_category(entry),
        })
 
    if not items:
        raise RuntimeError("No items with usable images were found.")
 
    # Skins first, then the remaining item types.
    order = {
        "SKINS": 0,
        "EMOTES": 1,
        "PICKAXES": 2,
        "BACK BLINGS": 3,
        "GLIDERS": 4,
        "WRAPS": 5,
        "CONTRAILS": 6,
        "SNEAKERS": 7,
        "INSTRUMENTS": 8,
        "MUSIC": 9,
        "OTHER": 10,
    }
 
    items.sort(key=lambda item: order.get(item["category"], 10))
    return items
 
 
def split_into_three_pages(items):
    # Divide all collected entries across exactly 3 pages.
    total = len(items)
    return [
        items[page * total // TOTAL_PAGES:
              (page + 1) * total // TOTAL_PAGES]
        for page in range(TOTAL_PAGES)
    ]
 
 
def download_image(url):
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception as exc:
        print(f"Image download failed: {exc}")
        return None
 
 
def draw_brand(img, page):
    draw = ImageDraw.Draw(img)
 
    centered(
        draw, (W // 2, 57), "Koinz",
        get_font(55, True), WHITE
    )
 
    centered(
        draw, (W // 2, 117), "متجر فورتنايت",
        get_font(29, True), (202, 157, 255)
    )
 
    draw.rounded_rectangle(
        (36, 160, W - 36, 165),
        radius=2,
        fill=PURPLE
    )
 
    centered(
        draw, (W // 2, 193),
        f"الصفحة {page} من {TOTAL_PAGES}",
        get_font(22, True), MUTED
    )
 
 
def fit_item_image(source, size):
    # Remove transparent borders so the item appears larger.
    alpha = source.getchannel("A")
    bbox = alpha.getbbox()
 
    if bbox:
        source = source.crop(bbox)
 
    source.thumbnail((size, size), Image.Resampling.LANCZOS)
 
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - source.width) // 2
    y = (size - source.height) // 2
    canvas.alpha_composite(source, (x, y))
 
    return canvas
 
 
def draw_item(img, item, index, rows, cols):
    draw = ImageDraw.Draw(img)
 
    left, right = 22, 22
    top, bottom = 225, 1680
    gap_x, gap_y = 8, 9
 
    cell_w = (
        W - left - right - gap_x * (cols - 1)
    ) // cols
 
    cell_h = (
        bottom - top - gap_y * (rows - 1)
    ) // rows
 
    row = index // cols
    col = index % cols
 
    x = left + col * (cell_w + gap_x)
    y = top + row * (cell_h + gap_y)
 
    draw.rounded_rectangle(
        (x, y, x + cell_w, y + cell_h),
        radius=13,
        fill=(22, 17, 39),
        outline=(88, 47, 139),
        width=2
    )
 
    label_height = min(39, max(25, cell_h // 4))
    image_size = max(
        30,
        min(cell_w - 10, cell_h - label_height - 10)
    )
 
    source = download_image(item["image"])
 
    if source:
        icon_img = fit_item_image(source, image_size)
        px = x + (cell_w - image_size) // 2
        py = y + 3 + max(
            0,
            (cell_h - label_height - image_size - 5) // 2
        )
        img.paste(icon_img, (px, py), icon_img)
 
    # English item name only. No price labels.
    name = item["name"].strip()
    max_chars = max(9, cell_w // 9)
 
    if len(name) > max_chars:
        name = name[:max_chars - 1].rstrip() + "…"
 
    font_size = max(13, min(18, cell_w // 9))
 
    centered(
        draw,
        (x + cell_w // 2, y + cell_h - label_height // 2 - 1),
        name,
        get_font(font_size, True),
        WHITE
    )
 
 
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
 
    # Delete old images so old extra pages are not left over.
    for filename in os.listdir(OUT_DIR):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(OUT_DIR, filename))
 
    items = load_items()
    pages = split_into_three_pages(items)
 
    print(f"Items with usable images: {len(items)}")
    print("Generating exactly 3 story images...")
 
    for page_num, page_items in enumerate(pages, start=1):
        img = make_background()
        draw_brand(img, page_num)
 
        cols = COLS
        rows = max(1, math.ceil(len(page_items) / cols))
 
        for index, item in enumerate(page_items):
            draw_item(img, item, index, rows, cols)
 
        draw = ImageDraw.Draw(img)
 
        draw.rounded_rectangle(
            (30, 1725, W - 30, 1810),
            radius=22,
            fill=(36, 20, 62),
            outline=PURPLE,
            width=2
        )
 
        centered(
            draw,
            (W // 2, 1768),
            "متجر العناصر اليوم",
            get_font(32, True),
            WHITE
        )
 
        output = os.path.join(OUT_DIR, f"shop-{page_num:02d}.jpg")
        img.save(output, "JPEG", quality=94, optimize=True)
 
        print(f"Saved {output}: {len(page_items)} items")
 
    print("Done: exactly 3 story images generated.")
 
 
if __name__ == "__main__":
    main()
