import easyocr
import requests
from bs4 import BeautifulSoup

# Etape 1 : Récupérer l'URL de l'image depuis sephijin.fr
url = "https://sephijin.fr/mavuika"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

image_url = None
for a in soup.find_all("a", href=True):
    if "guide-synthese" in a["href"] and (".webp" in a["href"] or ".png" in a["href"]):
        image_url= a["href"]
        break
    
print(f"Image trouvée : {image_url}")

# Etape 2 : OCR sur l'image
reader = easyocr.Reader(["fr"], gpu=False)
results = reader.readtext(image_url)

print("\n=== Texte extrait ===")
for (bbox, text, confidence) in results:
    if confidence > 0.3:
        print(f"[{confidence:.2f}] {text}")
        
