"""
from auth import login_and_get_cookies
from hoyolab import get_user_info
import json
import os

print("=== Test auth.py ===")
print("Une fenêtre Chromium va s'ouvrir, connecte-toi sur HoyoLAB ...")

cookies = login_and_get_cookies()

if cookies:
    print(f"\n✓ Cookies récupérés :")
    
    # Récupérer le nickname et l'UID depuis l'API
    print("Récupération des infos du compte...")
    try:
        info = get_user_info(cookies)
        print(f"✓ Nickname : {info['nickname']}")
        print(f"✓ UID : {info['UID']}")
        
        
        # Sauvegarder dans data/cookies.json
        os.makedirs("data", exist_ok=True)
        data = {
            "nickname":         info["nickname"],
            "uid":              info["uid"],
            "ltuid_v2":         cookies["ltuid_v2"],
            "ltoken_v2":        cookies["ltoken_v2"],
            "cookie_token_v2":  cookies["cookie_token_v2"],
            "account_mid_v2":   cookies["account_mid_v2"],
            "account_id_v2":    cookies["account_id_v2"],
        }
    
        with open("data/cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)
        print("\n✓ Cookies sauvegardés dans data/cookies.json")
    except Exception as e:
        print(f"✗ Erreur get_user_info : {e}")
else:
    print("\n✗ Échec - aucun cookie récupéré (timeout ?)")
    
"""

from auth import login_and_get_cookies
import json, os

cookies = login_and_get_cookies()

if cookies:
    os.makedirs("data", exist_ok=True)
    with open("data/cookies.json", "w") as f:
        json.dump(cookies, f, indent=2)
    print("✓ Cookies sauvegardés !")
    print(cookies.keys())
else:
    print("✗ Échec")