import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.hoyolab import get_all_game_characters
import json
with open("data/cookies.json") as f:
    data = json.load(f)
cookies = data.get("accounts", {})
active = data.get("active")
active_cookies = cookies.get(active, {})


print("=== Test get_all_game_characters ===")
try:
    characters = get_all_game_characters(cookies=active_cookies)
    print(f"✓ {len(characters)} personnages récupérés")
    
    # Afficher les 5 premiers
    print("\n── 5 premiers ──")
    for c in characters[:5]:
        print(f"  {c['name']} | {c['element']} | {c['rarity']} | {c['icon_url'][:50]}...")
        
except Exception as e:
    print(f"✗ Erreur : {e}")