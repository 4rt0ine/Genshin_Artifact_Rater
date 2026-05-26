"""
update_builds.py
Mise à jour automatique des builds depuis sephijin.fr

Fonctionnement général :
    1. Pour chaque personnage chargé depuis HoYoLAB, on tente de trouver
       une page de guide sur sephijin.fr/{nom_en_minuscule}/
    2. Si la page existe, on récupère l'URL de l'image de synthèse
    3. On calcule le hash MD5 de l'image pour détecter les changements
       (même si l'URL reste identique, le contenu peut avoir changé)
    4. Si le hash a changé ou si le personnage n'est pas encore en cache,
       on lance l'OCR (reconnaissance de texte) sur l'image
    5. On parse le texte extrait en utilisant les positions X/Y des mots
       pour identifier les mainstats et les substats prioritaires
    6. Le résultat est sauvegardé dans data/builds_cache.json
    7. data/builds.py est régénéré automatiquement depuis le cache

Calibration des zones (basée sur les images 1920x1080 de sephijin.fr) :
    Les images ont toujours la même structure. En coordonnées relatives (0.0 à 1.0) :
    - Substats à focus : y entre 0.21 et 0.26, x entre 0.52 et 0.72
    - Mainstat Sables  : y entre 0.26 et 0.34, x entre 0.68 et 0.78
    - Mainstat Coupe   : y entre 0.36 et 0.44, x entre 0.68 et 0.78
    - Mainstat Diadème : y entre 0.45 et 0.52, x entre 0.68 et 0.78
 
Source des builds : sephijin.fr (@sephijin)
"""


import requests
import hashlib
import json
import os
import re
import io
import easyocr
from PIL import Image as PILImage
from bs4 import BeautifulSoup
from datetime import date

# Fichier de cache — stocke les hashs, URLs et builds parsés
CACHE_FILE = "data/builds_cache.json"
 
# ── Zones de l'image (coordonnées relatives 0.0 à 1.0) ───────────────────────
# Ces valeurs ont été calibrées en analysant les positions OCR sur 4 personnages
# (Mavuika, Furina, Nefer, Lauma). Si sephijin.fr change sa mise en page,
# il faudra recalibrer ces valeurs.
 
# Zone X commune à toutes les mainstats (colonne droite de la section BUILD)
MAINSTAT_X_MIN = 0.69
MAINSTAT_X_MAX = 0.76
 
# Zone Y de chaque slot d'artefact
SLOT_ZONES = {
    "Sables du temps":  (0.26, 0.34),  # Icône sablier → stat à sa droite
    "Coupe d'Eonothem": (0.36, 0.44),  # Icône coupe   → stat à sa droite
    "Diadème de Logos": (0.45, 0.52),  # Icône diadème → stat à sa droite
}
 
# Zone des substats à focus (ligne "SUBSTATS À FOCUS : X > Y > Z")
SUBSTATS_ZONE = {
    "y_min": 0.21, "y_max": 0.26,
    "x_min": 0.52, "x_max": 0.72,
}


# ── Mapping texte OCR → nom de stat ──────────────────────────────────────────
# Les abréviations utilisées par sephijin.fr ne correspondent pas toujours
# exactement aux noms dans SUBSTAT_ROLLS de scoring.py, d'où ce mapping.
STAT_MAP = {
    # Substats offensives
    "DC":      "DGT Crit",
    "TC":      "Taux Crit",
    "DC/TC":   "DGT Crit",   # Les deux → on prend DC en priorité
    "TC/DC":   "Taux Crit",  # Les deux → on prend TC en priorité
    "ATQ%":    "ATQ%",
    # Substats défensives
    "PV%":     "PV%",
    "DEF%":    "DEF%",
    # Substats utilitaires
    "ME":      "Maîtrise",
    "RE%":     "Recharge",
    "RE":      "Recharge",
    # Bonus élémentaires (mainstats Coupe uniquement)
    "PYRO":    "Bonus Pyro",
    "HYDRO":   "Bonus Hydro",
    "CRYO":    "Bonus Cryo",
    "ELECTRO": "Bonus Électro",
    "GEO":     "Bonus Géo",
    "ANEMO":   "Bonus Anémo",
    "DENDRO":  "Bonus Dendro",
}
 
# Poids décroissants selon la position dans "X > Y > Z > W"
# Le premier substat reçoit 1.0, le second 0.8, etc.
PRIORITY_WEIGHTS = [1.0, 0.8, 0.6, 0.4]



# ── Cache ─────────────────────────────────────────────────────────────────────

def load_cache():
    """
    Charge le cache depuis le fichier JSON.
    Retourne un dict vide si absent.
    """
    
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
        
    return {}

def save_cache(cache):
    """
    Sauvegarde le cache dans le fichier JSON.
    """
    
    os.makedirs("data", exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    


# ── Scrapping sephijin.fr ─────────────────────────────────────────────────────

def get_image_url(slug):
    """
    Scrape sephijin.fr/{slug}/ pour récupérer l'URL de l'image synthèse.
    L'image synthèse est toujours dans un lein <a> dont l'href contient 
    'guide-synthese' et se termine par .webp ou .png
    Retourne None si la page n'existe pas ou si l'image n'est pas trouvée.
    """
    
    url = f"https://sephijin.fr/{slug}/"
    try:
        response = requests.get(url, timeout=10)
        
        # Sephijin n'aura peut être pas de page pour les personnage les plus récents
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        
        for a in soup.find_all("a", href=True):
            if "guide-synthese" in a["href"] and (".webp" in a["href"] or ".png" in a["href"]):
                return a["href"]
        
    except Exception as e:
        print(f"    Erreur scraping {slug} : {e}")
    return None

def get_image_hash(image_url):
    """
    Calcule le hash MD5 du contenu binaire de l'image.
    Le hash change si un seul pixel est modifié, ce qui permet de détecter
    les mises à jour même si l'URL reste identique.
    """
    
    response = requests.get(image_url, timeout=15)
    return hashlib.md5(response.content).hexdigest()



# ── OCR ───────────────────────────────────────────────────────────────────────

def run_ocr(image_url):
    """
    Lance l'OCR easyocr sur une image distante.
    Retourne une liste de tuples (texte, y_relative, x_relative) pour chaque
    mot détecté avec une confiance > 0.4.
 
    Les coordonnées relatives (entre 0.0 et 1.0) sont calculées en divisant
    la position absolue par les dimensions de l'image, ce qui rend le parsing
    indépendant de la résolution de l'image.
    """
    
     # Télécharger l'image pour connaître ses dimensions
    img_data = requests.get(image_url, timeout=15).content
    img = PILImage.open(io.BytesIO(img_data))
    img_width, img_height = img.size  # Note : PIL retourne (largeur, hauteur)
    
    # Initialiser le reader (les modèles sont mis en cache localement)
    reader = easyocr.Reader(["fr"], gpu=False)
    results = reader.readtext(image_url, detail=1)
    
    texts_with_pos = []
    for (bbox, text, conf) in results:
        if conf > 0.4:
            # bbox = [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            # On calcule le centre du rectangle pour avoir une position unique
            y_avg = sum(point[1] for point in bbox) / 4
            x_avg = sum(point[0] for point in bbox) / 4
            texts_with_pos.append((
                text,
                round(y_avg / img_height, 2),
                round(x_avg / img_width,  2),
            ))
 
    return texts_with_pos
    

# ── Parsing du build ──────────────────────────────────────────────────────────
    
def parse_build_from_ocr(texts_with_pos):
    """
    Parse les textes avec positions pour extraire le build du personnage.
 
    Stratégie :
    - Substats : on filtre les textes dans la zone SUBSTATS_ZONE et on
      cherche le pattern "X > Y > Z" pour construire les weights.
    - Mainstats : on filtre par zone X (colonne droite de BUILD) puis par
      zone Y (différente pour chaque slot) pour associer chaque stat à
      son slot d'artefact.
    """
    
    build = {
        "substats": "",
        "mainstat": {
            "Sables du temps"   : [],
            "Coupe d'Eonothem"  : [],
            "Diadème de Logos"  : [],
        },
        "weights": {
            "Taux Crit": 0.0,
            "DGT Crit": 0.0,
            "ATQ%": 0.0,
            "PV%": 0.0,
            "DEF%": 0.0,
            "Maîtrise": 0.0,
            "Recharge": 0.0,
        }
    }

    # ── Substats à focus ──────────────────────────────────────────────────
    
    # On collecte tous les textes dans la zone des substats et on les fusionne
    substats_texts = []
    for (text, y_rel, x_rel) in texts_with_pos:
        if (SUBSTATS_ZONE["y_min"] <= y_rel <= SUBSTATS_ZONE["y_max"] and
                SUBSTATS_ZONE["x_min"] <= x_rel <= SUBSTATS_ZONE["x_max"]):
            substats_texts.append(text.upper())
 
    substats_raw = " ".join(substats_texts)
    
    # Extraire uniquement la partie après "FOCUS :" (ex: "DC/TC > ATQ% > ME")
    match = re.search(r"FOCUS\s*[:\-]?\s*(.+)", substats_raw)
    if match:
        build["substats"] = match.group(1).strip()
    elif substats_raw:
        
        # Si on n'a pas trouvé "FOCUS", on garde tout ce qu'on a
        build["substats"] = substats_raw
        
        
    # Construire les weights depuis l'ordre des substats (X > Y > Z)
    # Chaque stat reçoit un poids décroissant selon sa position
    parts = re.split(r"\s*[>\s]\s*", build["substats"]) # → sépare par > OU par espace simple
    for i, part in enumerate(parts[:4]):
        part = part.strip()
        for key, stat_name in STAT_MAP.items():
            
            # On vérifie que la clé est bien présente dans la partie
            # et que le stat_name correspond à un weight connu
            if key in part and stat_name in build["weights"]:
                
                # On ne remplace que si le poids actuel est inférieur
                # (évite d'écraser DC avec TC si les deux sont dans la même partie)
                new_weight = PRIORITY_WEIGHTS[i] if i < len(PRIORITY_WEIGHTS) else 0.2
                if build["weights"][stat_name] < new_weight:
                    build["weights"][stat_name] = new_weight
                    
                    
    # ── Mainstats par slot ────────────────────────────────────────────────
    
    # Pour chaque texte dans la colonne X des mainstats, on identifie
    # son slot selon sa position Y, puis on mappe le texte vers un nom de stat
    for (text, y_rel, x_rel) in texts_with_pos:
        
        # Filtrer par zone X (colonne des mainstats)
        if not (MAINSTAT_X_MIN <= x_rel <= MAINSTAT_X_MAX):
            continue
        
        text_upper = text.upper().strip()
 
        # Identifier le slot selon la zone Y
        for slot, (y_min, y_max) in SLOT_ZONES.items():
            if y_min <= y_rel <= y_max:
                
                # Chercher la stat correspondante dans le texte
                for key, stat_name in STAT_MAP.items():
                    if key in text_upper:
                        if stat_name not in build["mainstat"][slot]:
                            build["mainstat"][slot].append(stat_name)
                break  # Un texte ne peut appartenir qu'à un seul slot
 
    return build


# ── Mise à jour d'un personnage ───────────────────────────────────────────────

def update_character(name, cache):
    """
    Vérifie si le build d'un personnage est à jour et le met à jour si besoin.
 
    Paramètres :
        name  : nom HoYoLAB du personnage ex "Mavuika"
        cache : dict du cache actuel
 
    Retourne le cache mis à jour.
    """
    
    # Le slug est le nom en minuscules pour l'URL sephijin.fr
    slug = name.lower()
    print(f"\n── {name} ──")
 
    # Étape 1 : vérifier si sephijin.fr a une page pour ce personnage
    image_url = get_image_url(slug)
    if not image_url:
        print(f"  ✗ Pas de page sur sephijin.fr/{slug}/")
        return cache
 
    print(f"  Image : {image_url}")
 
    # Étape 2 : calculer le hash de l'image actuelle
    current_hash = get_image_hash(image_url)
    cached = cache.get(name, {})
 
    # Étape 3 : comparer avec le hash en cache
    if cached.get("image_hash") == current_hash:
        print(f"  ✓ Déjà à jour (image inchangée)")
        return cache
 
    # Étape 4 : image modifiée ou nouveau personnage → lancer l'OCR
    print(f"  → Image modifiée ou nouveau personnage, lancement OCR...")
    texts_with_pos = run_ocr(image_url)
    print(f"  → {len(texts_with_pos)} textes extraits")
 
    # Étape 5 : parser le build depuis les textes avec positions
    build = parse_build_from_ocr(texts_with_pos)
    print(f"  → Substats  : {build['substats']}")
    print(f"  → Mainstats : {build['mainstat']}")
    print(f"  → Weights   : {build['weights']}")
 
    # Étape 6 : mettre à jour le cache
    cache[name] = {
        "image_url":   image_url,
        "image_hash":  current_hash,
        "last_update": str(date.today()),
        "build":       build,
    }
 
    return cache

# ── Génération de builds.py ───────────────────────────────────────────────────
 
def generate_builds_py(cache):
    """
    Génère data/builds.py depuis le cache.
    Ce fichier est importé par scoring.py et app.py pour récupérer les weights
    et les mainstats recommandées par personnage.
    Ne pas modifier manuellement — relancer update_builds.py à la place.
    """
    
    lines = [
        '"""',
        "builds.py — Généré automatiquement par update_builds.py",
        "Source : sephijin.fr (@sephijin) — utilisé avec accord de l'auteur",
        "Ne pas modifier manuellement, relancer update_builds.py à la place.",
        '"""',
        "",
        "BUILDS = {",
    ]
 
    for name, data in cache.items():
        build = data.get("build", {})
        lines += [
            f'    "{name}": {{',
            f'        # Dernière mise à jour : {data.get("last_update", "?")}',
            f'        "substats":    "{build.get("substats", "")}",',
            f'        "mainstat":    {json.dumps(build.get("mainstat", {}), ensure_ascii=False)},',
            f'        "weights":     {json.dumps(build.get("weights",  {}), ensure_ascii=False)},',
            f'        "image":       "{data.get("image_url",   "")}",',
            f'        "last_update": "{data.get("last_update", "")}",',
            f'    }},',
        ]
 
    lines += [
        "}",
        "",
        "# Weights génériques par rôle — utilisés quand le personnage n'est pas",
        "# référencé dans BUILDS (pas de page sur sephijin.fr ou pas encore parsé)",
        "GENERIC_WEIGHTS = {",
        '    "dps":     {"Taux Crit": 1.0, "DGT Crit": 1.0, "ATQ%": 0.6, "Maîtrise": 0.3},',
        '    "support": {"Recharge":  1.0, "Taux Crit": 0.7, "DGT Crit": 0.7, "PV%": 0.5},',
        '    "healer":  {"Recharge":  1.0, "PV%": 1.0,  "Taux Crit": 0.4, "DGT Crit": 0.4},',
        "}",
        "",
        "",
        "def get_build(character_name):",
        '    """Retourne le build complet d\'un personnage, ou None si non référencé."""',
        "    return BUILDS.get(character_name)",
        "",
        "",
        "def get_weights(character_name, role='dps'):",
        '    """',
        '    Retourne les weights d\'un personnage pour le scoring.',
        '    Si le personnage n\'est pas dans BUILDS, retourne des weights génériques',
        '    selon le rôle spécifié (dps, support, healer).',
        '    """',
        "    build = BUILDS.get(character_name)",
        "    if build:",
        '        return build["weights"]',
        '    return GENERIC_WEIGHTS.get(role, GENERIC_WEIGHTS["dps"])',
    ]
 
    with open("data/builds.py", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    # ── Point d'entrée ────────────────────────────────────────────────────────────
 
def update_builds(character_names):
    """
    Met à jour les builds pour une liste de personnages HoYoLAB.
    Appelé depuis app.py après le chargement des personnages, dans un thread
    séparé pour ne pas bloquer l'interface graphique.
 
    Paramètres :
        character_names : liste de noms HoYoLAB ex ["Nefer", "Furina", "Bennett"]
    """
    print("\n=== Mise à jour des builds depuis sephijin.fr ===")
    cache = load_cache()
 
    for name in character_names:
        cache = update_character(name, cache)
 
    save_cache(cache)
    generate_builds_py(cache)
    print("\n✓ Builds mis à jour — data/builds.py régénéré")
 
 
if __name__ == "__main__":
    # Mode test standalone : on passe une liste de persos manuellement
    # En production, cette liste vient des personnages chargés depuis HoYoLAB
    test_characters = ["Nefer", "Lauma", "Furina", "Mavuika", "Sucrose", "Aino"]
    update_builds(test_characters)