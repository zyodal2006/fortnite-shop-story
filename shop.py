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
ITEMS_PER_PAGE = 8
 
BG = (8, 7, 18)
PURPLE = (153, 70, 255)
WHITE = (255, 255, 255)
MUTED = (180, 174, 202)
 
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
 
 
def text_center(draw, xy, text, font, fill):
    draw.text(xy, text, font=font, fill=fill, anchor="mm")
 
 
def make_background():
    img = Image.new("RGB", (W, H), BG)
 
    # Purple glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-250, -180, 650, 550), fill=(116, 35, 255, 105))
    gd.ellipse((550, 1250, 1400, 2100), fill=(70, 20, 180, 80))
    glow = glow.filter(ImageFilter.GaussianBlur(150))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
 
    return img.convert("RGB")
 
 
def get_item_type(item):
    """Classify shop items using their API metadata."""
    data = item.get("brItems") or item.get("items") or []
    if not data:
        return "OTHER"
 
    first = data[0] or {}
    typ = first.get("type") or {}
    name = str(typ.get("value", "")).lower()
    display = str(typ.get("displayValue", "")).lower()
    combined = name + " " + display
 
    if "outfit" in combined or "skin" in combined:
        return "SKINS"
    if "emote" in combined:
        return "EMOTES"
    if "pickaxe" in combined or "harvesting tool" in combined:
        return "PICKAXES"
    if "glider" in combined:
        return "GLIDERS"
    if "backpack" in combined or "back bling" in combined:
        return "BACK BLINGS"
    if "wrap" in combined:
        return "WRAPS"
    if "contrail" in combined:
        return "CONTRAILS"
    if "shoe" in combined or "sneaker" in combined:
        return "SNEAKERS"
    if "instrument" in combined:
        return "INSTRUMENTS"
    if "jam track" in combined or "music" in combined:
        return "MUSIC"
 
    return "OTHER"
 
 
def get_item_image_url(item):
    items = item.get("brItems") or item.get("items") or []
    if items:
        images = items[0].get("images") or {}
        for key in ("featured", "icon", "smallIcon", "large"):
            if images.get(key):
                return images[key]
 
    return None
 
 
def get_item_name(item):
    items = item.get("brItems") or item.get("items") or []
    if items:
        return (
            items[0].get("name")
            or item.get("devName")
            or "Fortnite Item"
        )
    return item.get("devName") or "Fortnite Item"
 
 
def get_price(item):
    price = item.get("price") or 0
    try:
        return int(price)
    except (ValueError, TypeError):
        return 0
 
 
def load_items():
    print("Fetching Fortnite item shop...")
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    payload = response.json()
 
    if payload.get("status") != 200:
        raise RuntimeError("Fortnite API returned an unsuccessful response")
 
    shop = payload.get("data") or {}
    entries = shop.get("entries") or []
 
    if not entries:
        raise RuntimeError(
            "No shop entries found. The API may have changed."
        )
 
    items = []
    seen = set()
 
    for entry in entries:
        name = get_item_name(entry)
        image_url = get_item_image_url(entry)
        price = get_price(entry)
 
        if not image_url:
            continue
 
        # Avoid repeated entries with the same name and image.
        key = (name, image_url)
        if key in seen:
            continue
        seen.add(key)
 
        items.append({
            "name": name,
            "image": image_url,
            "price": price,
            "category": get_item_type(entry),
        })
 
    if not items:
        raise RuntimeError(
            "No usable item images were found in the API response."
        )
 
    return items
 
 
def download_image(url):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGBA")
        im.thumbnail((390, 245), Image.Resampling.LANCZOS)
        return im
    except Exception as exc:
        print(f"Could not download item image: {exc}")
        return None
 
 
def draw_brand(img, page, total_pages, category):
    draw = ImageDraw.Draw(img)
 
    # Brand emblem
    draw.rounded_rectangle(
        (48, 42, 122, 116),
        radius=22,
        fill=PURPLE
    )
    text_center(
        draw, (85, 79), "K",
        get_font(48, True), WHITE
    )
 
    draw.text(
        (145, 48), "KOINZ",
        font=get_font(48, True), fill=WHITE
    )
    draw.text(
        (148, 103), "FORTNITE ITEM SHOP",
        font=get_font(22, True), fill=(190, 150, 255)
    )
 
    draw.rounded_rectangle(
        (48, 160, W - 48, 164),
        radius=2,
        fill=PURPLE
    )
 
    draw.text(
        (52, 184), category,
        font=get_font(38, True), fill=WHITE
    )
 
    draw.text(
        (54, 235), f"PAGE {page} / {total_pages}",
        font=get_font(21, True), fill=MUTED
    )
 
 
def draw_card(img, item, index):
    draw = ImageDraw.Draw(img)
 
    cols = 2
    rows = math.ceil(ITEMS_PER_PAGE / cols)
 
    card_w = 474
    card_h = 345
    gap_x = 24
    gap_y = 24
    start_x = 42
    start_y = 300
 
    row = index // cols
    col = index % cols
 
    x = start_x + col * (card_w + gap_x)
    y = start_y + row * (card_h + gap_y)
 
    # Card base
    draw.rounded_rectangle(
        (x, y, x + card_w, y + card_h),
        radius=25,
        fill=(21, 17, 37),
        outline=(91, 47, 145),
        width=3
    )
 
    # Image panel
    image = download_image(item["image"])
    if image:
        iw, ih = image.size
        px = x + (card_w - iw) // 2
        py = y + 12 + (240 - ih) // 2
        img.paste(image, (px, py), image)
 
    # Divider
    draw.rounded_rectangle(
        (x + 20, y + 258, x + card_w - 20, y + 261),
        radius=2,
        fill=(91, 47, 145)
    )
 
    name = item["name"].strip()
    name_font = get_font(23, True)
 
    # Wrap long item names to two lines.
    if len(name) > 31:
        name = name[:29].rstrip() + "…"
 
    text_center(
        draw,
        (x + card_w // 2, y + 286),
        name,
        name_font,
        WHITE
    )
 
    price = f"{item['price']:,} V-BUCKS"
    text_center(
        draw,
        (x + card_w // 2, y + 321),
        price,
        get_font(21, True),
        (198, 145, 255)
    )
 
 
def group_items(items):
    order = [
        "SKINS",
        "EMOTES",
        "PICKAXES",
        "BACK BLINGS",
        "GLIDERS",
        "WRAPS",
        "CONTRAILS",
        "SNEAKERS",
        "INSTRUMENTS",
        "MUSIC",
        "OTHER",
    ]
 
    grouped = {}
    for item in items:
        grouped.setdefault(item["category"], []).append(item)
 
    # Keep related categories together when they are small.
    combined_groups = []
    current = []
    current_label = "FORTNITE COSMETICS"
 
    for category in order:
        group = grouped.get(category, [])
        if not group:
            continue
 
        # Start a new page when the next category would overflow.
        if current and len(current) + len(group) > ITEMS_PER_PAGE:
            combined_groups.append((current_label, current))
            current = []
            current_label = category
        elif not current:
            current_label = category
        elif category != current_label:
            current_label = "MIXED COSMETICS"
 
        # Split large categories into pages.
        while group:
            space = ITEMS_PER_PAGE - len(current)
            current.extend(group[:space])
            group = group[space:]
 
            if len(current) == ITEMS_PER_PAGE:
                combined_groups.append((current_label, current))
                current = []
                current_label = category
 
    if current:
        combined_groups.append((current_label, current))
 
    return combined_groups
 
 
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
 
    # Remove previous images so old pages are not left behind.
    for filename in os.listdir(OUT_DIR):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(OUT_DIR, filename))
 
    items = load_items()
    pages = group_items(items)
 
    print(f"Found {len(items)} items.")
    print(f"Generating {len(pages)} story images...")
 
    for page_number, (category, page_items) in enumerate(pages, start=1):
        img = make_background()
        draw_brand(img, page_number, len(pages), category)
 
        for index, item in enumerate(page_items):
            draw_card(img, item, index)
 
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            (42, 1792, W - 42, 1860),
            radius=22,
            fill=(36, 20, 62),
            outline=PURPLE,
            width=2
        )
        text_center(
            draw,
            (W // 2, 1826),
            "SHOP DAILY WITH KOINZ",
            get_font(25, True),
            WHITE
        )
 
        output = os.path.join(
            OUT_DIR, f"shop-{page_number:02d}.jpg"
        )
        img.save(output, "JPEG", quality=94, optimize=True)
        print(f"Saved {output}")
 
    print("All story images generated successfully!")
 
 
if __name__ == "__main__":
    main()
