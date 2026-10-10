import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
 
API_URL = "https://fortnite-api.com/v2/shop?language=en"
OUT = "stories"
W, H = 1080, 1920
BG = (18, 20, 34)
CARD = (35, 39, 59)
WHITE = (255, 255, 255)
MUTED = (190, 197, 218)
 
 
def font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()
 
 
def get_image(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception:
        return None
 
 
def main():
    os.makedirs(OUT, exist_ok=True)
 
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json().get("data") or {}
    entries = data.get("entries") or []
 
    if not entries:
        raise RuntimeError(
            "No shop entries found. Check the API response."
        )
 
    items = []
    for entry in entries:
        group = []
        for key in ("brItems", "tracks", "instruments", "cars"):
            group.extend(entry.get(key) or [])
 
        if not group:
            group = [entry]
 
        item = group[0]
        images = item.get("images") or {}
        image_url = (
            images.get("featured")
            or images.get("icon")
            or images.get("smallIcon")
        )
 
        assets = entry.get("displayAssets") or []
        if not image_url and assets:
            image_url = assets[0].get("url")
 
        items.append({
            "name": item.get("name") or "Fortnite Item",
            "image": image_url,
            "price": entry.get("finalPrice"),
        })
 
    # Eight shop offers per story, four rows and two columns.
    per_page = 8
    pages = [items[i:i + per_page]
             for i in range(0, len(items), per_page)]
 
    for page_no, page_items in enumerate(pages, start=1):
        canvas = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(canvas)
 
        draw.text((W // 2, 55), "FORTNITE ITEM SHOP",
                  font=font(48), fill=WHITE, anchor="mt")
        draw.text((W // 2, 120), f"DAILY SHOP  •  {page_no}/{len(pages)}",
                  font=font(27), fill=MUTED, anchor="mt")
 
        margin = 38
        gap = 22
        top = 205
        card_w = (W - 2 * margin - gap) // 2
        card_h = 385
 
        for i, item in enumerate(page_items):
            col = i % 2
            row = i // 2
            x = margin + col * (card_w + gap)
            y = top + row * (card_h + gap)
 
            draw.rounded_rectangle(
                (x, y, x + card_w, y + card_h),
                radius=24, fill=CARD
            )
 
            picture = get_image(item["image"])
            if picture:
                picture = ImageOps.fit(
                    picture, (card_w - 24, 275),
                    method=Image.Resampling.LANCZOS
                )
                canvas.paste(picture, (x + 12, y + 12))
            else:
                draw.text(
                    (x + card_w // 2, y + 135),
                    "FORTNITE",
                    font=font(30), fill=MUTED, anchor="mm"
                )
 
            name = str(item["name"])
            if len(name) > 23:
                name = name[:20] + "..."
 
            draw.text(
                (x + card_w // 2, y + 305),
                name, font=font(25), fill=WHITE, anchor="mt"
            )
 
            price = item["price"]
            price_text = (
                f"{price:,} V-BUCKS"
                if isinstance(price, (int, float))
                else "ITEM SHOP"
            )
            draw.text(
                (x + card_w // 2, y + 345),
                price_text, font=font(21), fill=MUTED, anchor="mt"
            )
 
        draw.text(
            (W // 2, H - 42),
            "Unofficial fan-made shop overview",
            font=font(20), fill=MUTED, anchor="ms"
        )
 
        filename = os.path.join(OUT, f"shop-{page_no}.jpg")
        canvas.save(filename, quality=92)
 
    print(f"Created {len(pages)} story image(s) in {OUT}/")
 
 
if __name__ == "__main__":
    main()
 
Advertisement
Hottest instagram selfies
Hello! Wanna date me?
Your ISP is logging you. Block them now
Add Comment
Please, Sign In to add comment
Public Pastes
Free Crypto Method
CSS | 18 min ago | 0.72 KB
+12,000$ in 2 days
CSS | 18 min ago | 0.72 KB
Documents
18 min ago | 0.43 KB
Crypto admin access
19 min ago | 0.43 KB
Silk
12 hours ago | 3.74 KB
fleet_agent
20 hours ago | 5.04 KB
Altur Song Lyrics
1 day ago | 13.27 KB
CC:T GPS Beacon
1 day ago | 0.49 KB

