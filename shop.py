import os
import requests
from PIL import Image, ImageDraw, ImageFont

API_URL = "https://fortnite-api.com/v2/shop"
OUTPUT_DIR = "stories"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    if not data.get("data"):
        raise RuntimeError("لم تصل بيانات المتجر.")

    entries = data["data"].get("entries", [])
    if not entries:
        raise RuntimeError("لم يتم العثور على عناصر المتجر.")

    print(f"تم العثور على {len(entries)} عنصرًا في المتجر.")
    print("الخطوة التالية ستكون تجهيز الصور الطولية ونشرها.")

if __name__ == "__main__":
    main()
