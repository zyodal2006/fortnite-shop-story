import os
import io
import math
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# =========================
# KOINZ - FORTNITE ITEM SHOP
# Generates story images only. Upload them manually from GitHub Actions.
# =========================

W, H = 1080, 1920
OUT_DIR = "stories"
LOGO_PATH = "fortmite pfp.png"
COLS = 6
MAX_ROWS = 10
MAX_ITEMS_PER_PAGE = COLS * MAX_ROWS

BG = (8, 7, 18)
PURPLE = (153, 70, 255)
WHITE = (255, 255, 255)
MUTED = (220, 210, 235)
API_URL = "https://fortnite-api.com/v2/shop?language=en"

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
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def centered(draw, xy, text, font, fill, arabic=False, stroke_width=0, stroke_fill=(0, 0, 0)):
    if arabic:
        text = arabic_text(text)
    try:
        draw.text(xy, text, font=font, fill=fill, anchor="mm",
                  direction="rtl" if arabic else "ltr",
                  stroke_width=stroke_width, stroke_fill=stroke_fill)
    except (TypeError, ValueError):
        draw.text(xy, text, font=font, fill=fill, anchor="mm",
                  stroke_width=stroke_width, stroke_fill=stroke_fill)


def make_background():
    img = Image.new("RGBA", (W, H), BG + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-320, -240, 620, 460), fill=(125, 35, 255, 100))
    gd.ellipse((610, 1270, 1400, 2050), fill=(85, 20, 220, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(145))
    return Image.alpha_composite(img, glow).convert("RGB")


def entry_objects(entry):
    # brItems contains the Battle Royale items in a shop entry; keep the whole
    # entry together so a skin and its included back bling remain one card.
    value = entry.get("brItems")
    if isinstance(value, list) and value:
        return value
    for key in ("items", "instruments", "beans", "legoKits"):
        value = entry.get(key)
        if isinstance(value, list) and value:
            return value
    return []


def item_details(obj):
    item_type = obj.get("type") or {}
    return " ".join(str(v) for v in (
        item_type.get("value", ""), item_type.get("displayValue", ""),
        obj.get("name", ""), obj.get("description", "")
    ) if v).lower()


def get_category(entry):
    objects = entry_objects(entry)
    details = " ".join(item_details(obj) for obj in objects)
    # Prefer the main item in a bundle, but classify by any included item.
    if any(word in details for word in ("outfit", "skin")):
        return "SKINS"
    if any(word in details for word in ("emote", "dance")):
        return "EMOTES"
    if any(word in details for word in ("backpack", "back bling", "backbling")):
        return "BACK BLINGS"
    if any(word in details for word in ("shoe", "sneaker", "footwear")):
        return "SNEAKERS"
    if any(word in details for word in ("pickaxe", "harvesting tool")):
        return "PICKAXES"
    if any(word in details for word in ("glider", "wrap", "contrail", "toy", "spray", "emoji", "banner")):
        return "OTHER"
    return "OTHER"


def is_excluded(entry):
    objects = entry_objects(entry)
    details = " ".join(item_details(obj) for obj in objects)
    details += " " + str(entry.get("devName", "")).lower()
    # Exclude music and vehicle-related cosmetics/items.
    excluded = (
        "jam track", "music track", "instrument", "car body", "vehicle",
        "wheel", "wheels", "tire", "tyre", "boost", "vehicle wrap",
        "car skin", "car paint", "sports car", " suv", "truck", "motorcycle",
    )
    return any(word in details for word in excluded)


def best_image_url(obj):
    images = obj.get("images") or {}
    # Use larger artwork first to avoid blurry cards when zooming in.
    for key in ("featured", "background", "large", "icon", "smallIcon"):
        if images.get(key):
            return images[key]
    return None


def get_entry_image_urls(entry):
    urls = []
    for obj in entry_objects(entry):
        url = best_image_url(obj)
        if url and url not in urls:
            urls.append(url)
    if not urls:
        images = entry.get("images") or {}
        for key in ("featured", "background", "large", "icon", "smallIcon"):
            if images.get(key):
                urls.append(images[key])
                break
    bundle_image = (entry.get("bundle") or {}).get("image")
    if not urls and bundle_image:
        urls.append(bundle_image)
    return urls[:4]


def get_entry_name(entry):
    objects = entry_objects(entry)
    if objects:
        # Prefer a skin name when the entry contains a skin + accessories.
        for obj in objects:
            details = item_details(obj)
            if "outfit" in details or "skin" in details:
                return obj.get("name") or obj.get("title") or "Fortnite Bundle"
        names = [obj.get("name") or obj.get("title") for obj in objects]
        names = [str(n).strip() for n in names if n]
        if names:
            return " + ".join(names[:2])
    return entry.get("devName") or entry.get("name") or "Fortnite Item"


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

    items, seen, skipped = [], set(), 0
    for entry in entries:
        if is_excluded(entry):
            skipped += 1
            continue
        urls = get_entry_image_urls(entry)
        if not urls:
            continue
        name = str(get_entry_name(entry)).strip()
        category = get_category(entry)
        key = (name, tuple(urls))
        if key in seen:
            continue
        seen.add(key)
        items.append({"name": name, "images": urls, "category": category})

    order = {"SKINS": 0, "EMOTES": 1, "BACK BLINGS": 2,
             "SNEAKERS": 3, "PICKAXES": 4, "OTHER": 5}
    items.sort(key=lambda item: order.get(item["category"], 5))
    if not items:
        raise RuntimeError("No eligible shop items with usable images were found.")
    print(f"Excluded music/vehicle entries: {skipped}")
    print(f"Eligible shop entries: {len(items)}")
    return items


def split_into_pages(items):
    return [items[start:start + MAX_ITEMS_PER_PAGE]
            for start in range(0, len(items), MAX_ITEMS_PER_PAGE)]


def download_image(url):
    try:
        response = requests.get(url, timeout=25)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception as exc:
        print(f"Image download failed: {exc}")
        return None


def draw_header(img):
    draw = ImageDraw.Draw(img)
    logo_size = 108
    logo_x, logo_y = 38, 27
    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH).convert("RGB")
            side = min(logo.width, logo.height)
            left = (logo.width - side) // 2
            top = (logo.height - side) // 2
            logo = logo.crop((left, top, left + side, top + side))
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS).convert("RGBA")
            mask = Image.new("L", (logo_size, logo_size), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, logo_size - 1, logo_size - 1), radius=25, fill=255)
            img.paste(logo, (logo_x, logo_y), mask)
            draw = ImageDraw.Draw(img)
        except Exception as exc:
            print(f"Store logo could not be loaded: {exc}")

    name_x = logo_x + logo_size + 24
    centered(draw, (name_x + 2, logo_y + 37), "Koinz.1", get_font(43, True), WHITE)
    centered(draw, (name_x + 2, logo_y + 78), "شوب فورتنايت", get_font(27, True), (225, 205, 255), arabic=True,
             stroke_width=1, stroke_fill=(0, 0, 0))
    draw.rounded_rectangle((34, 155, W - 34, 161), radius=3, fill=PURPLE)
    centered(draw, (W // 2, 192), "متجر فورتنايت اليومي", get_font(27, True), WHITE, arabic=True,
             stroke_width=1, stroke_fill=(0, 0, 0))


def fit_item_image(source, width, height):
    bbox = source.getchannel("A").getbbox()
    if bbox:
        source = source.crop(bbox)
    source.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    x = (width - source.width) // 2
    y = (height - source.height) // 2
    canvas.alpha_composite(source, (x, y))
    return canvas


def fit_name_font(draw, name, max_width):
    for size in range(24, 13, -1):
        font = get_font(size, True)
        bbox = draw.textbbox((0, 0), name, font=font, stroke_width=0)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return get_font(13, True)


def draw_item(img, item, index, rows, cols, layout, image_cache):
    left, right = 24, 24
    gap_x, gap_y = 7, 7
    cell_w = (W - left - right - gap_x * (cols - 1)) // cols
    available_cell_h = (layout["height"] - gap_y * (rows - 1)) // rows
    cell_size = min(cell_w, available_cell_h)
    grid_height = rows * cell_size + (rows - 1) * gap_y
    top = layout["top"] + max(0, (layout["height"] - grid_height) // 2)
    row, col = divmod(index, cols)
    x = left + col * (cell_w + gap_x) + (cell_w - cell_size) // 2
    y = top + row * (cell_size + gap_y)

    # Soft glass-like light card over the dark background.
    card = Image.new("RGBA", (cell_size, cell_size), (245, 241, 255, 242))
    card_draw = ImageDraw.Draw(card)
    card_draw.rounded_rectangle((0, 0, cell_size - 1, cell_size - 1), radius=20,
                                fill=(242, 239, 250, 242), outline=(255, 255, 255, 255), width=3)
    img.paste(card, (x, y), card)

    label_height = 33
    pad = 5
    image_top = y + pad
    image_bottom = y + cell_size - label_height - 5
    image_w = cell_size - pad * 2
    image_h = max(1, image_bottom - image_top)
    urls = item["images"]
    loaded = []
    for url in urls:
        if url not in image_cache:
            image_cache[url] = download_image(url)
        if image_cache[url] is not None:
            loaded.append(image_cache[url])

    # Show multiple objects from the same bundle together in the same card.
    if loaded:
        if len(loaded) == 1:
            fitted = fit_item_image(loaded[0], image_w, image_h)
            img.paste(fitted, (x + pad, image_top), fitted)
        else:
            slots = min(4, len(loaded))
            sub_w = (image_w - 4 * (slots - 1)) // slots
            for j, source in enumerate(loaded[:slots]):
                fitted = fit_item_image(source, sub_w, image_h)
                px = x + pad + j * (sub_w + 4) + (sub_w - fitted.width) // 2
                py = image_top + (image_h - fitted.height) // 2
                img.paste(fitted, (px, py), fitted)

    draw = ImageDraw.Draw(img)
    name = str(item["name"]).strip()
    # Long bundle names are shortened so the title remains legible at story size.
    if len(name) > 28:
        name = name[:26].rstrip() + "…"
    name_font = fit_name_font(draw, name, cell_size - 12)
    centered(draw, (x + cell_size // 2, y + cell_size - label_height // 2), name,
             name_font, (24, 20, 34), stroke_width=0)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for filename in os.listdir(OUT_DIR):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(OUT_DIR, filename))

    if not os.path.exists(LOGO_PATH):
        print(f"WARNING: {LOGO_PATH} not found; header will show without the logo.")

    items = load_items()
    pages = split_into_pages(items)
    print(f"Generating {len(pages)} story image(s), maximum {MAX_ROWS} rows each...")
    image_cache = {}

    for page_num, page_items in enumerate(pages, start=1):
        img = make_background()
        draw_header(img)
        rows = max(1, math.ceil(len(page_items) / COLS))
        if rows > MAX_ROWS:
            raise RuntimeError(f"Page {page_num} has {rows} rows; maximum is {MAX_ROWS}.")
        layout = {"top": 220, "height": 1665}
        for index, item in enumerate(page_items):
            draw_item(img, item, index, rows, COLS, layout, image_cache)
        output = os.path.join(OUT_DIR, f"shop-{page_num:02d}.jpg")
        img.save(output, "JPEG", quality=97, subsampling=0, optimize=True)
        print(f"Saved {output}: {len(page_items)} entries, {rows} rows")

    print(f"Done: {len(pages)} story image(s) generated.")
    print("Manual mode: download the 'fortnite-shop-stories' artifact from GitHub Actions and post the images to Instagram Stories.")


if __name__ == "__main__":
    main()
    
