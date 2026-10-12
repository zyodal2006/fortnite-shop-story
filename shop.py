import os
import io
import math
import time
import hashlib
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# =========================
# KOINZ - FORTNITE ITEM SHOP
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
MUTED = (205, 190, 225)

API_URL = "https://fortnite-api.com/v2/shop?language=en"
GRAPH_API_VERSION = "v25.0"

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
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def centered(draw, xy, text, font, fill, arabic=False, stroke_width=0, stroke_fill=(0, 0, 0)):
    if arabic:
        text = arabic_text(text)
    try:
        draw.text(
            xy, text, font=font, fill=fill, anchor="mm",
            direction="rtl" if arabic else "ltr",
            stroke_width=stroke_width, stroke_fill=stroke_fill
        )
    except (TypeError, ValueError):
        draw.text(xy, text, font=font, fill=fill, anchor="mm",
                  stroke_width=stroke_width, stroke_fill=stroke_fill)


def make_background():
    img = Image.new("RGBA", (W, H), BG + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.ellipse((-300, -240, 600, 450), fill=(125, 35, 255, 105))
    draw.ellipse((600, 1250, 1400, 2050), fill=(85, 20, 220, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(145))
    return Image.alpha_composite(img, glow).convert("RGB")


def get_objects(entry):
    for key in ("brItems", "tracks", "instruments", "cars", "legoKits", "beans", "items"):
        value = entry.get(key)
        if isinstance(value, list) and value:
            return value
    return []


def get_name(entry):
    objects = get_objects(entry)
    if objects:
        obj = objects[0]
        return obj.get("name") or obj.get("title") or entry.get("devName") or "Fortnite Item"
    return entry.get("devName") or entry.get("name") or "Fortnite Item"


def get_category(entry):
    objects = get_objects(entry)
    if not objects:
        return "OTHER"
    obj = objects[0]
    item_type = obj.get("type") or {}
    raw = (str(item_type.get("value", "")) + " " + str(item_type.get("displayValue", ""))).lower()
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
    objects = get_objects(entry)
    for obj in objects:
        item_type = obj.get("type") or {}
        details = " ".join(str(value) for value in (
            item_type.get("value", ""), item_type.get("displayValue", ""),
            obj.get("name", ""), obj.get("title", ""), entry.get("devName", "")
        ) if value).lower()
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
    return (entry.get("bundle") or {}).get("image")


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

    items, seen, skipped_music = [], set(), 0
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
        items.append({"name": name, "image": image_url, "category": get_category(entry)})

    if not items:
        raise RuntimeError("No items with usable images were found.")
    order = {"SKINS": 0, "EMOTES": 1, "PICKAXES": 2, "BACK BLINGS": 3,
             "GLIDERS": 4, "WRAPS": 5, "CONTRAILS": 6, "SNEAKERS": 7,
             "INSTRUMENTS": 8, "OTHER": 9}
    items.sort(key=lambda item: order.get(item["category"], 9))
    print(f"Excluded music entries: {skipped_music}")
    print(f"Items with usable images: {len(items)}")
    return items


def split_into_pages(items):
    return [items[start:start + MAX_ITEMS_PER_PAGE]
            for start in range(0, len(items), MAX_ITEMS_PER_PAGE)]


def download_image(url):
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception as exc:
        print(f"Image download failed: {exc}")
        return None


def draw_header(img):
    draw = ImageDraw.Draw(img)
    logo_size = 112
    logo_x, logo_y = 42, 30
    radius = 27
    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH).convert("RGB")
            side = min(logo.width, logo.height)
            left = (logo.width - side) // 2
            top = (logo.height - side) // 2
            logo = logo.crop((left, top, left + side, top + side))
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS).convert("RGBA")
            mask = Image.new("L", (logo_size, logo_size), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, logo_size - 1, logo_size - 1), radius=radius, fill=255
            )
            shadow = Image.new("RGBA", (logo_size + 18, logo_size + 18), (0, 0, 0, 0))
            shadow_mask = Image.new("L", shadow.size, 0)
            ImageDraw.Draw(shadow_mask).rounded_rectangle(
                (8, 8, logo_size + 8, logo_size + 8), radius=radius, fill=105
            )
            shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(8))
            shadow.putalpha(shadow_mask)
            img.paste(shadow, (logo_x - 8, logo_y - 3), shadow)
            img.paste(logo, (logo_x, logo_y), mask)
            draw = ImageDraw.Draw(img)
        except Exception as exc:
            print(f"Store logo could not be loaded: {exc}")

    name_x = logo_x + logo_size + 24
    centered(draw, (name_x + 2, logo_y + 43), "Koinz.1", get_font(43, True), WHITE)
    centered(draw, (name_x + 2, logo_y + 83), "Ø§ÙØ´ÙØ¨ Ø§ÙÙÙÙ", get_font(27, True), (215, 175, 255), arabic=True,
             stroke_width=1, stroke_fill=(0, 0, 0))
    draw.rounded_rectangle((35, 165, W - 35, 170), radius=3, fill=PURPLE)
    centered(draw, (W // 2, 199), "Ø´ØÙ ÙÙØ¨ÙÙØ³ ØÙØ§ÙÙ Ø§ÙÙÙ Ø¹ÙØ®Ø§Øµ",
             get_font(23, True), WHITE, arabic=True, stroke_width=1, stroke_fill=(0, 0, 0))


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
    for size in range(23, 11, -1):
        font = get_font(size, True)
        bbox = draw.textbbox((0, 0), name, font=font, stroke_width=0)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return get_font(12, True)


def draw_item(img, item, index, rows, cols, layout):
    left, right = 22, 22
    gap_x, gap_y = 5, 5
    cell_w = (W - left - right - gap_x * (cols - 1)) // cols
    available_cell_h = (layout["height"] - gap_y * (rows - 1)) // rows
    cell_size = min(cell_w, available_cell_h)
    grid_height = rows * cell_size + (rows - 1) * gap_y
    top = layout["top"] + max(0, (layout["height"] - grid_height) // 2)
    row = index // cols
    col = index % cols
    x = left + col * (cell_w + gap_x)
    y = top + row * (cell_size + gap_y)
    x += (cell_w - cell_size) // 2
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (x, y, x + cell_size - 1, y + cell_size - 1),
        radius=25, fill=(22, 17, 39), outline=(88, 47, 139), width=2
    )
    label_height = 35
    image_top = y + 4
    image_bottom = y + cell_size - label_height - 3
    image_w = cell_size - 10
    image_h = max(1, image_bottom - image_top)
    source = download_image(item["image"])
    if source:
        icon_img = fit_item_image(source, image_w, image_h)
        px = x + (cell_size - icon_img.width) // 2
        py = image_top + (image_h - icon_img.height) // 2
        img.paste(icon_img, (px, py), icon_img)
    name = str(item["name"]).strip()
    name_font = fit_name_font(draw, name, cell_size - 10)
    centered(draw, (x + cell_size // 2, y + cell_size - label_height // 2),
             name, name_font, WHITE, stroke_width=1, stroke_fill=(0, 0, 0))


def cloudinary_upload(image_path):
    """Upload an image using Cloudinary's signed upload API and return its public URL."""
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
    if not all((cloud_name, api_key, api_secret)):
        raise RuntimeError(
            "Missing Cloudinary secrets. Set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in GitHub Actions."
        )

    timestamp = str(int(time.time()))
    signature_base = f"timestamp={timestamp}{api_secret}"
    signature = hashlib.sha1(signature_base.encode("utf-8")).hexdigest()
    endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    with open(image_path, "rb") as image_file:
        response = requests.post(
            endpoint,
            data={"timestamp": timestamp, "api_key": api_key, "signature": signature},
            files={"file": image_file},
            timeout=90,
        )
    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(f"Cloudinary returned non-JSON response (HTTP {response.status_code}).")
    if not response.ok or not result.get("secure_url"):
        raise RuntimeError(f"Cloudinary upload failed: {result}")
    return result["secure_url"]


def instagram_post_story(image_path, access_token, account_id):
    public_url = cloudinary_upload(image_path)
    print(f"Image uploaded to Cloudinary: {os.path.basename(image_path)}")

    base_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{account_id}"
    create_response = requests.post(
        f"{base_url}/media",
        data={"image_url": public_url, "media_type": "STORIES", "access_token": access_token},
        timeout=60,
    )
    try:
        create_data = create_response.json()
    except ValueError:
        raise RuntimeError(f"Instagram container response was not JSON: HTTP {create_response.status_code}")
    if not create_response.ok or not create_data.get("id"):
        raise RuntimeError(f"Instagram could not create the Story container: {create_data}")

    creation_id = create_data["id"]
    print(f"Story container created for {os.path.basename(image_path)}; waiting for processing...")

    # Wait for Meta to finish fetching and processing the image before publishing.
    status_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"
    ready = False
    for attempt in range(12):
        status_response = requests.get(
            status_url,
            params={"fields": "status_code,status", "access_token": access_token},
            timeout=30,
        )
        try:
            status_data = status_response.json()
        except ValueError:
            status_data = {}
        if not status_response.ok or status_data.get("error"):
            raise RuntimeError(f"Could not check Instagram container status: {status_data}")
        status_code = str(status_data.get("status_code", "")).upper()
        print(f"Instagram processing status ({attempt + 1}/12): {status_code or status_data.get('status', 'unknown')}")
        if status_code == "FINISHED":
            ready = True
            break
        if status_code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container failed: {status_data}")
        time.sleep(5)
    if not ready:
        raise RuntimeError("Instagram did not finish processing the Story within 60 seconds.")

    publish_response = requests.post(
        f"{base_url}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=60,
    )
    try:
        publish_data = publish_response.json()
    except ValueError:
        raise RuntimeError(f"Instagram publish response was not JSON: HTTP {publish_response.status_code}")
    if not publish_response.ok or not publish_data.get("id"):
        raise RuntimeError(f"Instagram failed to publish the Story: {publish_data}")
    print(f"SUCCESS: Published {os.path.basename(image_path)} as Instagram Story. ID: {publish_data['id']}")


def post_to_instagram():
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
    if not access_token or not account_id:
        raise RuntimeError(
            "Instagram secrets are missing. Add INSTAGRAM_ACCESS_TOKEN and "
            "INSTAGRAM_ACCOUNT_ID to GitHub Actions secrets and pass both to the workflow."
        )

    if not os.path.isdir(OUT_DIR):
        raise RuntimeError(f"Stories directory not found: {OUT_DIR}")
    image_files = sorted(
        os.path.join(OUT_DIR, filename)
        for filename in os.listdir(OUT_DIR)
        if filename.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if not image_files:
        raise RuntimeError("No story images found to publish.")

    print(f"Publishing {len(image_files)} image(s) to Instagram Stories...")
    failures = []
    for index, image_path in enumerate(image_files, start=1):
        print(f"Publishing Story {index}/{len(image_files)}: {image_path}")
        try:
            instagram_post_story(image_path, access_token, account_id)
        except Exception as exc:
            failures.append(f"{image_path}: {exc}")
            print(f"FAILED to publish {image_path}: {exc}")
        if index < len(image_files):
            time.sleep(5)
    if failures:
        raise RuntimeError("One or more Stories failed to publish:\n" + "\n".join(failures))
    print("All Story images published successfully.")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for filename in os.listdir(OUT_DIR):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(OUT_DIR, filename))

    if not os.path.exists(LOGO_PATH):
        print(f"WARNING: {LOGO_PATH} not found; header will show without the logo.")

    items = load_items()
    pages = split_into_pages(items)
    total_pages = len(pages)
    print(f"Generating {total_pages} story images, with a maximum of {MAX_ROWS} rows each...")

    for page_num, page_items in enumerate(pages, start=1):
        img = make_background()
        draw_header(img)
        rows = max(1, math.ceil(len(page_items) / COLS))
        if rows > MAX_ROWS:
            raise RuntimeError(f"Page {page_num} has {rows} rows; maximum is {MAX_ROWS}.")
        layout = {"top": 220, "height": 1675}
        for index, item in enumerate(page_items):
            draw_item(img, item, index, rows, COLS, layout)
        output = os.path.join(OUT_DIR, f"shop-{page_num:02d}.jpg")
        img.save(output, "JPEG", quality=94, optimize=True)
        print(f"Saved {output}: {len(page_items)} items, {rows} rows")

    print(f"Done: {total_pages} story images generated.")
    post_to_instagram()


if __name__ == "__main__":
    main()
