import os
import io
import math
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
 
# =========================
# KOINZ - FORTNITE ITEM SHOP
# =========================
 
W, H = 1080, 1920
OUT_DIR = "stories"
TOTAL_PAGES = 3
COLS = 6
 
BG = (8, 7, 18)
PURPLE = (153, 70, 255)
WHITE = (255, 255, 255)
MUTED = (205, 190, 225)
 
API_URL = "https://fortnite-api.com/v2/shop?language=en"
 
# Optional Arabic shaping libraries.
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
 
 
def centered(draw, xy, text, font, fill, arabic=False):
    if arabic:
        text = arabic_text(text)
 
    try:
        draw.text(
            xy,
            text,
            font=font,
            fill=fill,
            anchor="mm",
            direction="rtl" if arabic else "ltr"
        )
    except (TypeError, ValueError):
        draw.text(xy, text, font=font, fill=fill, anchor="mm")
 
 
def make_background():
    img = Image.new("RGBA", (W, H), BG + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
 
    draw.ellipse(
        (-300, -240, 600, 450),
        fill=(125, 35, 255, 105)
    )
    draw.ellipse(
        (600, 1250, 1400, 2050),
        fill=(85, 20, 220, 90)
    )
 
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
 
        # Prefer the close-up locker icon.
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
        raise RuntimeError("No items with usable images were found.")
 
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
 
    # Store name.
    centered(
        draw,
        (W // 2, 48),
        "Koinz",
        get_font(55, True),
        WHITE
    )
 
    # Main Arabic heading.
    centered(
        draw,
        (W // 2, 108),
        "الشوب اليوم",
        get_font(38, True),
        (215, 175, 255),
        arabic=True
    )
 
    # Divider under the heading.
    draw.rounded_rectangle(
        (35, 150, W - 35, 155),
        radius=3,
        fill=PURPLE
    )
 
    # Store's message.
    centered(
        draw,
        (W // 2, 183),
        "شحن فيبوكس حياكم الله علخاص",
        get_font(23, True),
        WHITE,
        arabic=True
    )
 
    # Page indicator.
    centered(
        draw,
        (W // 2, 222),
        f"الصفحة {page} من {TOTAL_PAGES}",
        get_font(20, True),
        MUTED,
        arabic=True
    )
 
 
def fit_item_image(source, size):
    # Crop empty transparent borders to enlarge the icon.
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
 
    cell_w = (
        W - left - right - gap_x * (cols - 1)
    ) // cols
 
    # Make each card square.
    cell_h = cell_w
 
    grid_height = rows * cell_h + (rows - 1) * gap_y
    top = layout["top"] + max(
        0,
        (layout["height"] - grid_height) // 2
    )
 
    row = index // cols
    col = index % cols
 
    x = left + col * (cell_w + gap_x)
    y = top + row * (cell_h + gap_y)
 
    # Square card with subtle purple border.
    draw.rounded_rectangle(
        (x, y, x + cell_w, y + cell_h),
        radius=10,
        fill=(22, 17, 39),
        outline=(88, 47, 139),
        width=2
    )
 
    label_height = 35
    image_size = cell_w - 12
 
    source = download_image(item["image"])
 
    if source:
        icon_img = fit_item_image(source, image_size)
 
        px = x + (cell_w - image_size) // 2
        py = y + 3
 
        img.paste(icon_img, (px, py), icon_img)
 
    # Item name only. No prices.
    name = item["name"].strip()
    max_chars = max(9, cell_w // 9)
 
    if len(name) > max_chars:
        name = name[:max_chars - 1].rstrip() + "…"
 
    font_size = 15 if len(name) > 15 else 17
 
    centered(
        draw,
        (x + cell_w // 2, y + cell_h - label_height // 2 - 2),
        name,
        get_font(font_size, True),
        WHITE
    )
 
 
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
 
    # Remove old images to prevent extra pages.
    for filename in os.listdir(OUT_DIR):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(OUT_DIR, filename))
 
    items = load_items()
    pages = split_into_three_pages(items)
 
    print(f"Items with usable images: {len(items)}")
    print("Generating 3 square-grid story images...")
 
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
 
        img.save(
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
