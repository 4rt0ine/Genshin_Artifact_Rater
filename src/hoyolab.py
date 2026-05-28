"""
hoyolab.py
==========
Gestion des appels à l'API HoYoLAB pour récupérer les données du joueur.

Endpoints utilisés :
    - POST /character/list   → liste de tous les personnages du compte
    - POST /character/detail → artefacts détaillés par lot de 8 personnages
    - GET  /api/index        → nickname via UID Genshin réel
    - POST hoyowiki/get_entry_page_list → tous les persos du jeu (wiki)
    - GET  (externe)         → téléchargement et cache des icônes
"""

import requests
import os
import io
from PIL import Image

# ── Headers communs ───────────────────────────────────────────────────────────
HEADERS = {
    "Accept":            "application/json, text/plain, */*",
    "Accept-Language":   "fr-FR,fr;q=0.9",
    "Origin":            "https://act.hoyolab.com",
    "Referer":           "https://act.hoyolab.com/",
    "User-Agent":        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
    "X-Rpc-App_version": "1.5.0",
    "X-Rpc-Client_type": "5",
    "X-Rpc-Lang":        "fr-fr",
    "X-Rpc-Language":    "fr-fr",
    "X-Rpc-Platform":    "5",
}


# ── Nickname HoYoLAB ──────────────────────────────────────────────────────────

def get_hoyolab_nickname(cookies, uid=None, server="os_euro"):
    """
    Récupère le nickname HoYoLAB depuis /api/index.
    Nécessite le vrai UID Genshin (pas account_id_v2 qui est différent).
    Retourne {"nickname": str} ou None en cas d'erreur.
    """
    if not uid:
        return None

    url    = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/index"
    params = {"server": server, "role_id": uid, "lang": "fr-fr"}

    try:
        response = requests.get(url, params=params, cookies=cookies,
                                headers=HEADERS, timeout=10)
        data = response.json()

        if data["retcode"] != 0:
            print(f"get_hoyolab_nickname : retcode {data['retcode']} — {data['message']}")
            return None

        return {"nickname": data["data"]["role"]["nickname"]}

    except Exception as e:
        print(f"get_hoyolab_nickname : erreur — {e}")
        return None


# ── Personnages du compte ─────────────────────────────────────────────────────

def get_all_characters(cookies, uid, server="os_euro"):
    """
    Récupère la liste complète de tous les personnages du joueur.
    Utilise /character/list (POST) qui retourne TOUS les persos,
    contrairement à /api/index qui ne retourne que la vitrine (12 max).
    """
    url     = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/character/list"
    payload = {"server": server, "role_id": str(uid)}

    response = requests.post(url, json=payload, cookies=cookies, headers=HEADERS)
    data     = response.json()

    if data["retcode"] != 0:
        raise Exception(f"Erreur API : {data['message']}")

    return data["data"]["list"]


def get_character_details(cookies, uid, character_ids, server="os_euro"):
    """
    Récupère les artefacts détaillés pour une liste de personnages.
    Découpe en lots de 8 (limite API HoYoLAB).

    Retourne (characters, property_map) :
        - characters   : liste des persos avec artefacts
        - property_map : {property_type: {name, ...}} pour nommer les stats
    """
    url            = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/character/detail"
    all_characters = []
    property_map   = {}

    for i in range(0, len(character_ids), 8):
        batch   = character_ids[i:i + 8]
        payload = {
            "server":        server,
            "role_id":       str(uid),
            "character_ids": batch,
            "lang":          "fr-fr",
        }

        response = requests.post(url, json=payload, cookies=cookies, headers=HEADERS)
        data     = response.json()

        if data["retcode"] != 0:
            raise Exception(f"Erreur API : {data['message']}")

        all_characters.extend(data["data"]["list"])
        property_map.update(data["data"]["property_map"])

    return all_characters, property_map


# ── Personnages du jeu (wiki) ─────────────────────────────────────────────────

def get_all_game_characters(cookies=None, lang="fr-fr"):
    """
    Récupère la liste de tous les personnages du jeu depuis le wiki HoYoLAB.
    Pagine automatiquement pour récupérer les 122+ personnages.
    Nécessite les cookies de session HoYoLAB.

    Retourne une liste de dicts : {name, icon_url, element, rarity}
    """
    url     = "https://sg-act-public-api.hoyolab.com/hoyowiki/genshin/wapi/get_entry_page_list"
    headers = {
        "Content-Type":   "application/json",
        "Origin":         "https://wiki.hoyolab.com",
        "Referer":        "https://wiki.hoyolab.com/pc/genshin/aggregate/character",
        "x-rpc-language": lang,
        "x-rpc-lang":     lang,
        "x-rpc-wiki_app": "hoyowiki",
    }

    characters = []
    page_num   = 1
    total      = None

    while True:
        payload = {
            "filters":   [],
            "menu_id":   "2",
            "page_num":  page_num,
            "page_size": 30,
            "use_es":    True,
        }

        response = requests.post(url, json=payload, headers=headers,
                                 cookies=cookies, timeout=10)
        data     = response.json()

        if data["retcode"] != 0:
            raise Exception(f"Erreur wiki API : {data['message']}")

        if total is None:
            total = int(data["data"]["total"])

        for entry in data["data"]["list"]:
            filters = entry.get("filter_values", {})
            element = filters.get("character_vision", {}).get("values", [""])[0]
            rarity  = filters.get("character_rarity", {}).get("values", [""])[0]
            characters.append({
                "name":     entry["name"],
                "icon_url": entry["icon_url"],
                "element":  element,
                "rarity":   rarity,
            })

        if len(characters) >= total:
            break

        page_num += 1

    return characters


# ── Cache des icônes ──────────────────────────────────────────────────────────

def get_icon(url):
    """
    Télécharge une icône et la met en cache dans assets/.
    Si déjà en cache, la charge depuis le disque sans requête réseau.
    Retourne un objet PIL.Image.
    """
    os.makedirs("assets", exist_ok=True)

    filename   = url.split("/")[-1]
    cache_path = f"assets/{filename}"

    if os.path.exists(cache_path):
        return Image.open(cache_path)

    response = requests.get(url, timeout=10)
    img      = Image.open(io.BytesIO(response.content))
    img.save(cache_path)

    return img