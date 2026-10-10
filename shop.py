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
MUTED = (205, 195, 220)
 
API_URL = "https://fortnite-api.com/v2/shop?language=en"
 
# Arabic text support
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
 
    def arabic_text(text):
        return get_display(arabic_reshaper.reshape(text))
except ImportError:
    def arabic_text(text):
        return text
 
 
def get_font(size, bold=False):
    paths = [
        (
            "/usr/share/fonts/truetype/noto/"
            "NotoSansArabic-Bold.ttf"
            if bold else
            "/usr/share/fonts/truetype/noto/"
            "NotoSansArabic-Regular.ttf"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
            if bold else
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),
        (
            "/usr/share/fonts/truetype/liberation2/"
            "LiberationSans-Bold.ttf"
            if bold else
            "/usr/share/fonts/truetype/liberation2/"
            "LiberationSans-Regular.ttf"
        ),
    ]
 
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
 
    return ImageFont.load_default()
 
 
def centered(draw, xy, text, font, fill,
             arabic=False, shadow=False):
    """
    Center text. Arabic text is shaped first.
    Shadow is black, soft and subtle.
    """
    if arabic:
        text = arabic_text(text)
 
    x, y = xy
 
    if shadow:
        # Create a separate layer for a soft black shadow.
        shadow_layer = Image.new(
            "RGBA", (W, H), (0, 0, 0, 0)
        )
        shadow_draw = ImageDraw.Draw(shadow_layer)
 
        try:
            shadow_draw.text(
                (x + 1, y + 3),
                text,
                font=font,
                fill=(0, 0, 0, 205),
                anchor="mm",
                direction="ltr"
            )
        except (TypeError, ValueError):
            shadow_draw.text(
                (x + 1, y + 3),
                text,
                font=font,
                fill=(0, 0, 0, 205),
                anchor="mm"
            )
 
        shadow_layer = shadow_layer.filter(
            ImageFilter.GaussianBlur(3)
        )
 
        # Composite shadow before drawing the white text.
        if isinstance(draw, ImageDraw.ImageDraw):
            draw._image.alpha_composite(shadow_layer)
 
    try:
        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill,
            anchor="mm",
            direction="ltr"
        )
    except (TypeError, ValueError):
        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill,
            anchor="mm"
        )
 
 
def make_background():
    img = Image.new("RGBA", (W, H), BG + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
 
    draw.ellipse(
        (-300, -240, 600, 450),
        fill=(125, 35, 255, 100)
    )
    draw.ellipse(
        (600, 1250, 1400, 2050),
        fill=(85, 20, 220, 80)
    )
 
    glow = glow.filter(ImageFilter.GaussianBlur(145))
    return Image.alpha_composite(img, glow).convert("RGBA")
 
 
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
    item_type = obj.get("type") or {}
 
    raw = (
        str(item_type.get("value", "")) + " " +
        str(item_type.get("displayValue", ""))
    ).lower()
 
    categories = [
        (("outfit", "skin"), "SKINS"),
        (("emote",), "EMOTES"),
        (("pickaxe", "harvesting tool"), "PICKAXES"),
        (("backpack", "back bling"), "BACK BLINGS"),
        (("glider",), "GLIDERS"),
        (("wrap",), "WRAPS"),
        (("contrail",), "CONTRAILS"),
        (("shoe", "sneaker"), "SNEAKERS"),
        (("instrument",), "INSTRUMENTS"),
        (("jam track", "music"), "MUSIC"),
    ]
 
    for keywords, category in categories:
        if any(word in raw for word in keywords):
            return category
 
    return "OTHER"
 
 
def get_image_url(entry):
    objects = get_objects(entry)
 
    for obj in objects:
        images = obj.get("images") or {}
 
        # Prefer the standard item icon.
        for key in ("icon", "smallIcon", "featured", "large"):
            if images.get(key):
                return images[key]
 
    images = entry.get("images") or {}
 
    for key in ("icon", "smallIcon", "featured", "large"):
        if images.get(key):
            return images[key]
 
    bundle = entry.get("bundle") or {}
    return bundle.get("image")
 
 
def load_items():
    print("Fetching Fortnite item shop...")
 
    response = requests.get(API_URL, timeout=40)
    response.raise_for_status()
    payload = response.json()
 
    if payload.get("status") != 200:
        raise RuntimeError("Fortnite API returned an error.")
 
    entries = (payload.get("data") or {}).get("entries") or []
 
    if not entries:
        raise RuntimeError("No shop entries found.")
 
    items = []
    seen = set()
 
    for entry in entries:
        image_url = get_image_url(entry)
 
        if not image_url:
            continue
 
        name = get_name(entry).strip()
        unique_key = (name, image_url)
 
        if unique_key in seen:
            continue
 
        seen.add(unique_key)
 
        items.append({
            "name": name,
            "image": image_url,
            "category": get_category(entry),
        })
 
    if not items:
        raise RuntimeError("No items with usable images found.")
 
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
 
    items.sort(
        key=lambda item: order.get(item["category"], 10)
    )
 
    return items
 
 
def split_into_three_pages(items):
    total = len(items)
 
    return [
        items[
            page * total // TOTAL_PAGES:
            (page + 1) * total // TOTAL_PAGES
        ]
        for page in range(TOTAL_PAGES)
    ]
 
 
def download_image(url):
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
 
        return Image.open(
            io.BytesIO(response.content)
        ).convert("RGBA")
 
    except Exception as exc:
        print(f"Image download failed: {exc}")
        return None
 
 
def draw_header(img, page):
    draw = ImageDraw.Draw(img)
 
    # Store name
    centered(
        draw,
        (W // 2, 48),
        "Koinz",
        get_font(55, True),
        WHITE,
        shadow=True
    )
 
    # Main Arabic heading
    centered(
        draw,
        (W // 2, 108),
        "الشوب اليوم",
        get_font(40, True),
        WHITE,
        arabic=True,
        shadow=True
    )
 
    # Thin divider
    draw.rounded_rectangle(
        (35, 150, W - 35, 154),
        radius=2,
        fill=PURPLE
    )
 
    # Arabic store message
    centered(
        draw,
        (W // 2, 184),
        "شحن فيبوكس حياكم الله علخاص",
        get_font(24, False),
        WHITE,
        arabic=True,
        shadow=True
    )
 
    # Page indicator
    centered(
        draw,
        (W // 2, 222),
        f"الصفحة {page} من {TOTAL_PAGES}",
        get_font(20, False),
        MUTED,
        arabic=True,
        shadow=True
    )
 
 
def fit_item_image(source, size):
    # Crop transparent borders so the icon looks closer.
    bbox = source.getchannel("A").getbbox()
 
    if bbox:
        source = source.crop(bbox)
 
    source.thumbnail(
        (size, size),
        Image.Resampling.LANCZOS
    )
 
    canvas = Image.new(
        "RGBA",
        (size, size),
        (0, 0, 0, 0)
    )
 
    x = (size - source.width) // 2
    y = (size - source.height) // 2
    canvas.alpha_composite(source, (x, y))
 
    return canvas
 
 
def draw_item(img, item, index, rows, cols, layout):
    draw = ImageDraw.Draw(img)
 
    left, right = 22, 22
    gap_x, gap_y = 6, 6
 
    top_limit = layout["top"]
    bottom_limit = layout["top"] + layout["height"]
 
    available_w = (
        W - left - right - gap_x * (cols - 1)
    )
    available_h = (
        bottom_limit - top_limit - gap_y * (rows - 1)
    )
 
    # Square cells sized to fit the full grid.
    cell = max(
        1,
        min(available_w // cols, available_h // rows)
    )
 
    grid_w = cols * cell + (cols - 1) * gap_x
    grid_h = rows * cell + (rows - 1) * gap_y
 
    start_x = (W - grid_w) // 2
    start_y = top_limit + (layout["height"] - grid_h) // 2
 
    row = index // cols
    col = index % cols
 
    x = start_x + col * (cell + gap_x)
    y = start_y + row * (cell + gap_y)
 
    draw.rounded_rectangle(
        (x, y, x + cell, y + cell),
        radius=10,
        fill=(22, 17, 39),
        outline=(70, 49, 100),
        width=1
    )
 
    label_h = max(28, min(38, cell // 5))
    image_size = max(1, cell - 10 - label_h)
 
    source = download_image(item["image"])
 
    if source:
        icon_img = fit_item_image(source, image_size)
        px = x + (cell - image_size) // 2
        py = y + 3
        img.alpha_composite(icon_img, (px, py))
 
    # Item name only. No price.
    name = item["name"].strip()
    font_size = max(11, min(17, cell // 10))
    font = get_font(font_size, True)
 
    max_text_width = cell - 8
 
    while name and draw.textbbox((0, 0), name, font=font)[2] > max_text_width:
        name = name[:-2].rstrip() + "…"
 
    centered(
        draw,
        (x + cell // 2, y + cell - label_h // 2),
        name,
        font,
        WHITE,
        shadow=True
    )
 
 
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
 
    # Remove previous images so only today's 3 remain.
    for filename in os.listdir(OUT_DIR):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(OUT_DIR, filename))
 
    items = load_items()
    pages = split_into_three_pages(items)
 
    print(f"Items with usable images: {len(items)}")
    print("Generating exactly 3 story images...")
 
    for page_num, page_items in enumerate(pages, start=1):
        img = make_background()
        draw_header(img, page_num)
 
        cols = COLS
        rows = max(1, math.ceil(len(page_items) / cols))
 
        layout = {
            "top": 255,
            "height": 1400,
        }
 
        for index, item in enumerate(page_items):
            draw_item(
                img,
                item,
                index,
                rows,
                cols,
                layout
            )
 
        output = os.path.join(
            OUT_DIR,
            f"shop-{page_num:02d}.jpg"
        )
 
        img.convert("RGB").save(
            output,
            "JPEG",
            quality=94,
            optimize=True
        )
 
        print(
            f"Saved {output}: {len(page_items)} items"
        )
 
    print("Done: exactly 3 story images generated.")
 
 
if __name__ == "__main__":
    main()
 
