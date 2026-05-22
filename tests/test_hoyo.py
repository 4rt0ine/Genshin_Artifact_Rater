import json
from src.hoyolab import get_user_info, get_all_characters, get_character_details

# Charger les cookies
with open("data/cookies.json", "r") as f:
    print(json.load(f))
    data = json.load(f)
    # Récupère les cookies de la session active
    cookies = data.get("_session") or data
    
UID = "720978846"

# Test 1 : get_user_info
print("=== Test get_user_info ===")
try:
    info = get_user_info(cookies)
    print(f"✓ Nickname : {info['nickname']}")
    print(f"✓ UID: {info['uid']}")
except Exception as e:
    print(f"✗ Erreur : {e}")
    
# Test 2 : get_all_characters
print("\n=== Test get_all_characters ===")
try:
    avatars = get_all_characters(cookies, info["uid"])
    print(f"✓ {len(avatars)} personnages récupérés")
except Exception as e:
    print(f"✗ Erreur : {e}")
    
# Test 3 : get_character_details
print("\n=== Test get_character_details ===")
try:
    ids = [a["id"]for a in avatars[:2]]
    details, property_map = get_character_details(cookies, info["uid"], ids)
    print(f"✓ {len(details)} personnages détaillés")
    print(f"✓ {len(property_map)} propriétés dans le property_map")
except Exception as e:
    print(f"✗ Erreur : {e}")