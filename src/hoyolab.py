import requests
import os
import io
from PIL import Image

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Origin": "https://act.hoyolab.com",
    "Referer": "https://act.hoyolab.com/",
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
    "X-Rpc-App_version": "1.5.0",
    "X-Rpc-Client_type": "5",
    "X-Rpc-Lang": "fr-fr",
    "X-Rpc-Language": "fr-fr",
    "X-Rpc-Platform": "5",
}


def get_user_info(cookies):
    """
    Récupère les infos du compte connecté depuis les cookies.
    Retourne le nickname et l'uid du compte Genshin.
    """
    # Récupération de l'UID depuis account_id dans les cookies
    uid = cookies.get("account_id_v2") or cookies.get("ltuid_v2")

    # Récupération de toutes les infos du compte avec l'API
    url = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/index"
    params = {
        "server": "os_euro",
        "role_id": uid,
        "lang": "fr-fr"
    }
    response = requests.get(url, params=params, cookies=cookies, headers=HEADERS)
    data = response.json()
    
    print(data)
    
    if data["retcode"] != 0:
        raise Exception(f"Erreur AAPI : {data['message']}")
    
    # Extraction du nickname depuis la réponse
    nickname = data["data"]["role"]["nickname"]
    
    
    
    return {
        "uid": uid,
        "nickname": nickname
    }
    


def get_all_characters(cookies, uid, server="os_euro"):
    """Récupère la liste complète de tous les personnages du joueur."""
    url = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/character/list"
    payload = {
        "server": server,
        "role_id": str(uid),
    }
    response = requests.post(url, json=payload, cookies=cookies, headers=HEADERS)
    data = response.json()
    if data["retcode"] != 0:
        raise Exception(f"Erreur API : {data['message']}")
    return data["data"]["list"]


def get_character_details(cookies, uid, character_ids, server="os_euro"):
    url = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/character/detail"
    all_characters = []
    property_map = {}
    
    # Découper en lots de 8
    for i in range(0, len(character_ids), 8):
        batch = character_ids[i:i+8]
        payload = {
            "server": server,
            "role_id": str(uid),
            "character_ids": batch,
            "lang": "fr-fr"
        }
        response = requests.post(url, json=payload, cookies=cookies, headers=HEADERS)
        data = response.json()
        if data["retcode"] != 0:
            raise Exception(f"Erreur API : {data['message']}")
        all_characters.extend(data["data"]["list"])
        property_map.update(data["data"]["property_map"])
    
    return all_characters, property_map


def get_icon(url):
    """Télécharge et met en cache une icône depuis une URL."""
    os.makedirs("assets", exist_ok=True)
    filename = url.split("/")[-1]
    cache_path = f"assets/{filename}"

    if os.path.exists(cache_path):
        return Image.open(cache_path)

    response = requests.get(url)
    img = Image.open(io.BytesIO(response.content))
    img.save(cache_path)
    return img