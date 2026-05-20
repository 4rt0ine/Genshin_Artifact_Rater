from playwright.sync_api import sync_playwright
import time

HOYOLAB_URL = "https://www.hoyolab.com/home"
COOKIES_NEEDED = ["ltuid_v2", "ltoken_v2", "account_mid_v2", "account_id_v2", "cookie_token_v2"]

def login_and_get_cookies():
    """
    Ouvre une fenêtre Chromium sur HoyoLAB.
    Attend que l'utilisateur se connecte.
    Retourne les cookies une fois connecté.
    """
    
    with sync_playwright() as p :
        browser = p.chromium.launch(headless=False, args=["--window-size=500,700"])
        context = browser.new_context()
        page = context.new_page()
        page.goto(HOYOLAB_URL)
        
        # Attendre que les cookies nécessaire apparaissent (max 3 minutes)
        for _ in range (180):
            # Récuperer les cookies de tous les domaines
            all_cookies = context.cookies()
            cookies = {c["name"]: c["value"] for c in all_cookies}
            print(list(cookies.keys()))
            if all(k in cookies for k in COOKIES_NEEDED):
                browser.close()
                return {k: cookies[k] for k in cookies if k in ["ltuid_v2", "ltoken_v2", "account_mid_v2", "account_id_v2", "cookie_token_v2"]}
            time.sleep(1)
        browser.close()
        return None
    