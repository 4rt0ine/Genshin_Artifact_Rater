import requests
import easyocr
import io
from PIL import Image
from bs4 import BeautifulSoup

CHARACTERS = ["mavuika", "furina", "nefer", "lauma"]

def get_image_url(slug):
    url = f"https://sephijin.fr/{slug}/"
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    for a in soup.find_all("a", href=True):
        if "guide-synthese" in a["href"] and (".webp" in a["href"] or ".png" in a["href"]):
            return a["href"]
    return None

reader = easyocr.Reader(["fr"], gpu=False)

for slug in CHARACTERS:
    print(f"\n{'='*50}")
    print(f"=== {slug.upper()} ===")
    print(f"{'='*50}")

    image_url = get_image_url(slug)
    if not image_url:
        print("  ✗ Image non trouvée")
        continue

    img_data = requests.get(image_url).content
    img = Image.open(io.BytesIO(img_data))
    img_height, img_width = img.size[1], img.size[0]

    results = reader.readtext(image_url, detail=1)

    for (bbox, text, conf) in results:
        if conf > 0.4:
            y_avg = sum(p[1] for p in bbox) / 4
            x_avg = sum(p[0] for p in bbox) / 4
            y_rel = round(y_avg / img_height, 2)
            x_rel = round(x_avg / img_width,  2)
            # On affiche seulement la zone BUILD (x entre 0.45 et 0.80)
            if 0.45 <= x_rel <= 0.80:
                print(f"[y={y_rel} x={x_rel}] {text}")