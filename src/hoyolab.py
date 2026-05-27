"""
hoyolab.py
==========
Gestion des appels à l'API HoYoLAB pour récupérer les données du joueur.

Endpoints utilisés :
    - POST /character/list   → liste de tous les personnages du compte
    - POST /character/detail → artefacts détaillés par lot de 8 personnages
    - GET  /api/index        → infos du profil (nickname) via account_id_v2
    - GET  (externe)         → téléchargement et cache des icônes

Headers :
    Les headers reproduisent ceux envoyés par le site HoYoLAB en version
    mobile (Android), ce qui est nécessaire pour que l'API accepte les requêtes.
    Le cookie mi18nLang est ajouté côté app.py pour forcer le français.
"""

import requests
import os
import io
from PIL import Image


# ── Headers communs à toutes les requêtes HoYoLAB ────────────────────────────
# Ces valeurs reproduisent exactement ce qu'envoie le navigateur sur HoYoLAB
# en mode mobile Android. Ne pas modifier sans vérifier dans le Network.
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


# ── Infos du compte connecté ──────────────────────────────────────────────────

def get_hoyolab_nickname(cookies):
    """
    Récupère le nickname HoYoLAB du compte connecté.
    Utilise account_id_v2 comme role_id — c'est l'identifiant HoYoverse,
    pas l'UID Genshin. Cet appel fonctionne juste après la connexion
    Playwright, sans avoir à demander l'UID Genshin à l'utilisateur.

    Retourne un dict {"nickname": str} ou None en cas d'erreur.
    L'UID Genshin n'est pas inclus car account_id_v2 ≠ UID Genshin.
    """
    # account_id_v2 est l'identifiant HoYoverse (commun à tous les jeux HoYo)
    uid = cookies.get("account_id_v2") or cookies.get("ltuid_v2")

    url = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/index"
    params = {
        "server":  "os_euro",
        "role_id": uid,
        "lang":    "fr-fr",
    }

    try:
        response = requests.get(url, params=params, cookies=cookies,
                                headers=HEADERS, timeout=10)
        data = response.json()

        if data["retcode"] != 0:
            print(f"get_hoyolab_nickname : retcode {data['retcode']} — {data['message']}")
            return None

        nickname = data["data"]["role"]["nickname"]
        return {"nickname": nickname}

    except Exception as e:
        print(f"get_hoyolab_nickname : erreur — {e}")
        return None


# ── Personnages ───────────────────────────────────────────────────────────────

def get_all_characters(cookies, uid, server="os_euro"):
    """
    Récupère la liste complète de tous les personnages du joueur.
    Utilise l'endpoint /character/list (POST) qui retourne TOUS les persos,
    contrairement à /api/index qui ne retourne que la vitrine (12 max).

    Retourne une liste de dicts avec id, name, image, element, level, weapon.
    """
    
    url = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/character/list"
    payload = {
        "server":  server,
        "role_id": str(uid),
    }

    response = requests.post(url, json=payload, cookies=cookies, headers=HEADERS)
    data     = response.json()

    if data["retcode"] != 0:
        raise Exception(f"Erreur API : {data['message']}")

    return data["data"]["list"]


def get_character_details(cookies, uid, character_ids, server="os_euro"):
    """
    Récupère les artefacts détaillés pour une liste de personnages.
    L'API limite à 8 personnages par requête — on découpe en lots.

    Retourne un tuple (characters, property_map) :
        - characters   : liste des personnages avec leurs artefacts détaillés
        - property_map : dict {property_type: {name, ...}} pour nommer les stats
                         ex: {"20": {"name": "Taux CRIT"}, "22": {"name": "DGT CRIT"}}
    """
    
    url            = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/character/detail"
    all_characters = []
    property_map   = {}

    # Découper en lots de 8 (limite de l'API HoYoLAB)
    for i in range(0, len(character_ids), 8):
        batch   = character_ids[i:i + 8]
        payload = {
            "server":        server,
            "role_id":       str(uid),
            "character_ids": batch,
            "lang":          "fr-fr",  # Forcer les noms en français
        }

        response = requests.post(url, json=payload, cookies=cookies, headers=HEADERS)
        data     = response.json()

        if data["retcode"] != 0:
            raise Exception(f"Erreur API : {data['message']}")

        all_characters.extend(data["data"]["list"])

        # Le property_map est retourné dans chaque réponse — on fusionne
        # (les clés sont les mêmes pour tous les lots, pas de risque de conflit)
        property_map.update(data["data"]["property_map"])

    return all_characters, property_map


# ── Cache des icônes ──────────────────────────────────────────────────────────

def get_icon(url):
    """
    Télécharge une icône depuis une URL et la met en cache dans assets/.
    Si l'icône est déjà en cache, elle est chargée depuis le disque
    sans faire de requête réseau.

    Le nom du fichier cache est extrait depuis l'URL (dernier segment).
    Retourne un objet PIL.Image.
    """
    os.makedirs("assets", exist_ok=True)

    # Extraire le nom de fichier depuis l'URL
    filename   = url.split("/")[-1]
    cache_path = f"assets/{filename}"

    # Charger depuis le cache si disponible
    if os.path.exists(cache_path):
        return Image.open(cache_path)

    # Télécharger et mettre en cache
    response = requests.get(url, timeout=10)
    img      = Image.open(io.BytesIO(response.content))
    img.save(cache_path)

    return img