 
import os
from io import BytesIO
 
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
 
API_URL = "https://fortnite-api.com/v2/shop?language=en"
OUT_DIR = "stories"
 
WIDTH = 1080
HEIGHT = 1920
 
BACKGROUND = (18, 20, 34)
CARD_COLOR = (35, 39, 59)
WHITE = (255, 255, 255)
MUTED = (190, 197, 218)
 
 
def load_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
 
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
 
    return ImageFont.load_default()
 
 
def get_json():
    try:
        response = requests.get(
            API_URL,
            timeout=30,
            headers={"User-Agent": "FortniteShopStory/1.0"},
        )
        response.raise_for_status()
        result = response.json()
    except Exception as exc:
        raise RuntimeError(
            f"Could not download shop data: {exc}"
        ) from exc
 
    data = result.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(
            "The API did not return shop data. Check the API response."
        )
 
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError(
            "The shop contains no entries in the API response."
        )
 
    return entries
 
 
def download_image(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        return None
 
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return Image.open(
            BytesIO(response.content)
        ).convert("RGB")
    except Exception:
        return None
 
 
def get_cosmetics(entry):
    for key in (
        "br",
        "brItems",
        "tracks",
        "instruments",
        "cars",
        "legoKits",
        "lego_kits",
    ):
        values = entry.get(key)
        if isinstance(values, list) and values:
            return values
 
    return []
 
 
def get_image_url(entry, cosmetic):
    images = cosmetic.get("images") or {}
 
    for key in ("featured", "icon", "smallIcon", "large"):
        url = images.get(key)
        if isinstance(url, str) and url.startswith("https://"):
            return url
 
    assets = entry.get("displayAssets") or []
    if isinstance(assets, list):
        for asset in assets:
            if isinstance(asset, dict):
                url = asset.get("url")
                if isinstance(url, str) and url.startswith("https://"):
                    return url
 
    new_asset = entry.get("newDisplayAsset") or {}
    render_images = new_asset.get("renderImages") or []
 
    if isinstance(render_images, list):
        for image in render_images:
            if isinstance(image, dict):
                url = image.get("image")
                if isinstance(url, str) and url.startswith("https://"):
                    return url
 
    return None
 
 
def prepare_items(entries):
    items = []
 
    for entry in entries:
        if not isinstance(entry, dict):
            continue
 
        cosmetics = get_cosmetics(entry)
        cosmetic = cosmetics[0] if cosmetics else {}
 
        name = (
            cosmetic.get("name")
            or (entry.get("bundle") or {}).get("name")
            or entry.get("devName")
            or entry.get("dev_name")
            or "Fortnite Item"
        )
 
        price = entry.get("finalPrice")
        if price is None:
            price = entry.get("final_price")
 
        items.append({
            "name": str(name),
            "price": price,
            "image_url": get_image_url(entry, cosmetic),
        })
 
    if not items:
        raise RuntimeError(
            "The API returned entries, but no usable shop items."
        )
 
    return items
 
 
def make_story(items, page_number, total_pages):
    image = Image.new(
        "RGB", (WIDTH, HEIGHT), BACKGROUND
    )
    draw = ImageDraw.Draw(image)
 
    draw.text(
        (WIDTH // 2, 55),
        "FORTNITE ITEM SHOP",
        font=load_font(46),
        fill=WHITE,
        anchor="mt",
    )
 
    draw.text(
        (WIDTH // 2, 120),
        f"DAILY SHOP  -  {page_number}/{total_pages}",
        font=load_font(27),
        fill=MUTED,
        anchor="mt",
    )
 
    margin = 38
    gap = 22
    top = 205
    card_width = (WIDTH - 2 * margin - gap) // 2
    card_height = 385
 
    for index, item in enumerate(items):
        column = index % 2
        row = index // 2
 
        x = margin + column * (card_width + gap)
        y = top + row * (card_height + gap)
 
        draw.rounded_rectangle(
            (x, y, x + card_width, y + card_height),
            radius=24,
            fill=CARD_COLOR,
        )
 
        picture = download_image(item["image_url"])
 
        if picture is not None:
            picture = ImageOps.fit(
                picture,
                (card_width - 24, 265),
                method=Image.Resampling.LANCZOS,
            )
            image.paste(picture, (x + 12, y + 12))
        else:
            draw.text(
                (x + card_width // 2, y + 140),
                "IMAGE UNAVAILABLE",
                font=load_font(22),
                fill=MUTED,
                anchor="mm",
            )
 
        name = item["name"]
        if len(name) > 26:
            name = name[:23] + "..."
 
        draw.text(
            (x + card_width // 2, y + 292),
            name,
            font=load_font(23),
            fill=WHITE,
            anchor="mt",
        )
 
        price = item["price"]
        if isinstance(price, (int, float)):
            price_text = f"{int(price):,} V-BUCKS"
        else:
            price_text = "ITEM SHOP"
 
        draw.text(
            (x + card_width // 2, y + 335),
            price_text,
            font=load_font(21),
            fill=MUTED,
            anchor="mt",
        )
 
    draw.text(
        (WIDTH // 2, HEIGHT - 42),
        "Unofficial fan-made shop overview",
        font=load_font(18),
        fill=MUTED,
        anchor="ms",
    )
 
    return image
 
 
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
 
    entries = get_json()
    items = prepare_items(entries)
 
    per_page = 8
    pages = [
        items[index:index + per_page]
        for index in range(0, len(items), per_page)
    ]
 
    for page_number, page_items in enumerate(pages, start=1):
        story = make_story(
            page_items, page_number, len(pages)
        )
 
        filename = os.path.join(
            OUT_DIR, f"shop-{page_number}.jpg"
        )
        story.save(filename, "JPEG", quality=92)
 
        print(f"Created {filename}")
 
    print(f"SUCCESS: Created {len(pages)} story image(s).")
 
 
if __name__ == "__main__":
    main()
