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

COLS = 6
MAX_ROWS = 10
MAX_ITEMS_PER_PAGE = COLS * MAX_ROWS

BG = (8, 7, 18)
PURPLE = (153, 70, 255)
WHITE = (255, 255, 255)
MUTED = (205, 190, 225)

API_URL = "https://fortnite-api.com/v2/shop?language=en"


# Arabic shaping support.
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


def is_music_entry(entry):
    # Exclude purchasable Jam Tracks/music from the story.
    objects = get_objects(entry)

    for obj in objects:
        item_type = obj.get("type") or {}

        details = " ".join(
            str(value)
            for value in (
                item_type.get("value", ""),
                item_type.get("displayValue", ""),
                obj.get("name", ""),
                obj.get("title", ""),
                entry.get("devName", ""),
            )
            if value
        ).lower()

        if "jam track" in details or "music track" in details:
            return True

    return get_category(entry) == "MUSIC"


def get_image_url(entry):
    objects = get_objects(entry)

    for obj in objects:
        images = obj.get("images") or {}

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
    skipped_music = 0

    for entry in entries:
        if is_music_entry(entry):
            skipped_music += 1
            continue

        image_url = get_image_url(entry)

        if not image_url:
            continue

        name = str(get_name(entry)).strip()
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
        "OTHER": 9,
    }

    items.sort(
        key=lambda item: order.get(item["category"], 9)
    )

    print(f"Excluded music entries: {skipped_music}")
    print(f"Items with usable images: {len(items)}")

    return items


def split_into_pages(items):
    # Six columns x ten rows = 60 items maximum per image.
    return [
        items[start:start + MAX_ITEMS_PER_PAGE]
        for start in range(0, len(items), MAX_ITEMS_PER_PAGE)
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


def draw_header(img):
    draw = ImageDraw.Draw(img)

    centered(
        draw,
        (W // 2, 48),
        "Koinz",
        get_font(55, True),
        WHITE
    )

    centered(
        draw,
        (W // 2, 108),
        "الشوب اليوم",
        get_font(38, True),
        (215, 175, 255),
        arabic=True
    )

    draw.rounded_rectangle(
        (35, 150, W - 35, 155),
        radius=3,
        fill=PURPLE
    )

    centered(
        draw,
        (W // 2, 183),
        "شحن فيبوكس حياكم الله علخاص",
        get_font(23, True),
        WHITE,
        arabic=True
    )

    # Page indicator removed to make more room for items.


def fit_item_image(source, width, height):
    # Remove transparent borders so the item looks closer.
    bbox = source.getchannel("A").getbbox()

    if bbox:
        source = source.crop(bbox)

    source.thumbnail(
        (width, height),
        Image.Resampling.LANCZOS
    )

    canvas = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    x = (width - source.width) // 2
    y = (height - source.height) // 2

    canvas.alpha_composite(source, (x, y))
    return canvas


def fit_name_font(draw, name, max_width):
    # Keep the existing font style; shrink only for long names.
    for size in range(17, 9, -1):
        font = get_font(size, True)
        bbox = draw.textbbox((0, 0), name, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            return font

    return get_font(10, True)


def draw_item(img, item, index, rows, cols, layout):
    left, right = 22, 22
    gap_x, gap_y = 6, 6

    cell_w = (
        W - left - right - gap_x * (cols - 1)
    ) // cols

    # Fit all rows inside the available canvas area.
    available_cell_h = (
        layout["height"] - gap_y * (rows - 1)
    ) // rows

    cell_h = min(cell_w, available_cell_h)

    grid_height = rows * cell_h + (rows - 1) * gap_y

    top = layout["top"] + max(
        0,
        (layout["height"] - grid_height) // 2
    )

    row = index // cols
    col = index % cols

    x = left + col * (cell_w + gap_x)
    y = top + row * (cell_h + gap_y)

    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        (x, y, x + cell_w, y + cell_h),
        radius=10,
        fill=(22, 17, 39),
        outline=(88, 47, 139),
        width=2
    )

    # Reserve space for names while maximizing the image area.
    label_height = 30
    image_top = y + 3
    image_bottom = y + cell_h - label_height - 2
    image_w = cell_w - 8
    image_h = max(1, image_bottom - image_top)

    source = download_image(item["image"])

    if source:
        icon_img = fit_item_image(
            source,
            image_w,
            image_h
        )

        px = x + (cell_w - image_w) // 2
        py = image_top + (image_h - icon_img.height) // 2

        img.paste(icon_img, (px, py), icon_img)

    name = str(item["name"]).strip()

    name_font = fit_name_font(
        draw,
        name,
        cell_w - 8
    )

    centered(
        draw,
        (
            x + cell_w // 2,
            y + cell_h - label_height // 2
        ),
        name,
        name_font,
        WHITE
    )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Remove old images to prevent stale story files.
    for filename in os.listdir(OUT_DIR):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(OUT_DIR, filename))

    items = load_items()
    pages = split_into_pages(items)
    total_pages = len(pages)

    print(
        f"Generating {total_pages} story images, "
        f"with a maximum of {MAX_ROWS} rows each..."
    )

    for page_num, page_items in enumerate(pages, start=1):
        img = make_background()
        draw_header(img)

        rows = max(
            1,
            math.ceil(len(page_items) / COLS)
        )

        if rows > MAX_ROWS:
            raise RuntimeError(
                f"Page {page_num} has {rows} rows; "
                f"maximum is {MAX_ROWS}."
            )

        # Use the space freed by removing the page indicator.
        layout = {
            "top": 210,
            "height": 1680,
        }

        for index, item in enumerate(page_items):
            draw_item(
                img,
                item,
                index,
                rows,
                COLS,
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
            f"Saved {output}: "
            f"{len(page_items)} items, {rows} rows"
        )

    print(f"Done: {total_pages} story images generated.")


if __name__ == "__main__":
    main()
