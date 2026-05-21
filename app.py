import customtkinter as ctk
import threading
import json
import os
from PIL import Image
from hoyolab import get_all_characters, get_character_details, get_icon
from scoring import get_rolls_detail
from auth import login_and_get_cookies

GOLD  = "#c8a96e"
BEIGE = "#f0e6d3"
DARK  = "#1a1a2e"
COOKIES_FILE = "data/cookies.json"


class App:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.window = ctk.CTk()
        self.window.title("Genshin Artifact Rater")
        self.window.geometry("1200x800")
        self.window.configure(fg_color=DARK)
        
        self.active_cookies = self._load_cookies()
        
        if self.active_cookies:
            self._build_header()
        else:
            self._build_login_page()

    # ── Cookies ──────────────────────────────────────────────────────────────

    def _load_cookies(self):
        """
        Charge les cookies depuis le fichier.
        Retourne None si absent ou invalide.
        """
        
        if not os.path.exists(COOKIES_FILE):
            return None
        
        try:
            with open(COOKIES_FILE, "r") as f:
                data = json.load(f)
                
            # Vérifier que les clés essentielles sont présentes
            required = ["ltuid_v2", "ltoken_v2", "cookie_token_v2"]
            if all(k in data for k in required):
                return data
        except Exception as e:
            pass
        return None
    

    def _save_cookies(self, cookies, uid=None, nickname=None):
        """
        Sauvegarde les cookies avec l'UID et le Pseudo(nickname) si disponibles.
        """
        
        os.makedirs("data", exist_ok=True)
        data = dict(cookies)
        if uid:
            data["uid"] = uid
        if nickname:
            data["nickname"] = nickname
        with open(COOKIES_FILE, "w") as f:
            json.dump(data, f, indent=2)
            

    # ── Page de connexion ────────────────────────────────────────────────────
    
    
    def _build_login_page(self):
        self.login_frame = ctk.CTkFrame(self.window, fg_color=DARK)
        self.login_frame.pack(fill="both", expand=True)
        
        # Titre
        ctk.CTkLabel(self.login_frame,
                     text="✦ Genshin Artifact Rater ✦",
                     font=ctk.CTkFont(size=14),
                     text_color=BEIGE).pack(pady=(0, 60))
        
        # Bouton connexion
        self.connect_btn = ctk.CTkButton(
            self.login_frame,
            text="Se connecter avec HoyoLAB",
            width=300, height=52,
            fg_color=GOLD, text_color=DARK,
            hover_color="#a08050",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._do_login
        )
        self.connect_btn.pack()
        
        ctk.CTkLabel(self.login_frame,
                     text="Une fenêtre de connexion HoyoLAB s'ouvrira",
                     font=ctk.CTkFont(size=11),
                     text_color="#888888").pack(pady=(12, 0))
        
    def _do_login(self):
        self.connect_btn.configure(text="Connexion en cours...", state="disabled")
        
        def do():
            cookies = login_and_get_cookies()
            if cookies:
                self._save_cookies(cookies)
                self.active_cookies = cookies
                self.window.after(0, lambda: self.connect_btn.configure(
                    text="Se connecter avec HoyoLAB", state="normal"))
        
        threading.Thread(target=do, daemon=True).start()
    
    
    def _on_login_success(self):
        self.login_frame.destroy()
        self._build_header()

    
    # ── Header ───────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self.window, fg_color="#0d0d1a", height=80, corner_radius=0)
        header.pack(fill="x")

        # Titre
        ctk.CTkLabel(header, text="✦ Genshin Artifact Rater ✦",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=GOLD).pack(side="left", padx=20, pady=20)
        
        #Nickname si disponible
        nickname = self.active_cookies.get("nickname")
        uid = self.active_cookies.get("uid")
        if nickname:
            ctk.CTkLabel(header,
                         text=f"Connecté : {nickname}",
                         font=ctk.CTkFont(size=13),
                         text_color=BEIGE).pack(side="left", padx=10)
        
        
        # Bouton charger
        self.load_btn = ctk.CTkButton(header, text="Charger",
                                      width=100, height=36,
                                      fg_color=GOLD, text_color=DARK,
                                      hover_color="#a08050",
                                      command=self._on_load)
        self.load_btn.pack(side="right", padx=5, pady=20)
        
        # Bouton changer de compte
        ctk.CTkButton(header, text="Changer de compte",
                      width=100, height=36,
                      fg_color=GOLD, text_color=DARK,
                      hover_color="#a08050",
                      command=self._change_account).pack(side="right", padx=10, pady=20)
        
        
        # Champ UID
        self.uid_entry = ctk.CTkEntry(header, placeholder_text="UID Genshin",
                                     width=140, height=36,
                                     fg_color="#2a2a3e", border_color=GOLD,
                                     text_color=BEIGE)
        
        self.uid_entry.pack(side="right", padx=5, pady=20)
        
        # Pré-remplir l'UID si sauvegardé
        if uid:
            self.uid_entry.insert(0, uid)
        
        
    def _change_account(self):
        """
        Supprime les cookies et retourne à la page de connexion.
        """
        
        if os.path.exists(COOKIES_FILE):
            os.remove(COOKIES_FILE)
        self.active_cookies = None
        
        # Détruire tout et reconstruire
        for widget in self.window.winfo_children():
            widget.destroy()
        self._build_login_page()
        
    def _on_load(self):
        uid = self.uid_entry.get().strip()
        if not uid:
            return
        
        # Construire les cookies actifs
        cookies = {
            "ltuid_v2":        self.active_cookies["ltuid_v2"],
            "ltoken_v2":       self.active_cookies["ltoken_v2"],
            "cookie_token_v2": self.active_cookies["cookie_token_v2"],
            "account_mid_v2":  self.active_cookies["account_mid_v2"],
            "account_id_v2":   self.active_cookies["account_id_v2"],
            "mi18nLang":       "fr-fr",   
        }
    
        self.load_btn.configure(text="Chargement...", state="disabled")

        def load_data():
            try:
                avatars = get_all_characters(cookies, uid)
                ids = [a["id"] for a in avatars]
                details, property_map = get_character_details(cookies, uid, ids)
                self.property_map = property_map
                
                self.characters = []
                for d in details:
                    self.characters.append({
                        "id":       d["base"]["id"],
                        "name":     d["base"]["name"],
                        "image":    d["base"]["image"],
                        "element":  d["base"]["element"],
                        "level":    d["base"]["level"],
                        "relics":   d["relics"],
                    })
                    
                # Sauvegarder l'UID
                self._save_cookies(self.active_cookies, uid=uid)
                
                # Pré_télécharger toutes les icônes en parallèle
                def prefetch(url):
                    try:
                        get_icon(url)
                    except Exception:
                        pass
                threads = []
                for c in self.characters:
                    t = threading.Thread(target=prefetch, args=(c["image"],), daemon=True)
                    t.start()
                    threads.append(t)
                for t in threads:
                    t.join()
                
                self.window.after(0, self._build_tabs)
                
            except Exception as e:
                print(f"Erreur : {e}")
                
                # Si erreur d'auth -> reproposer la connexion
                if "login" in str(e).lower():
                    self.window.after(0,self._change_account)
            finally:
                self.window.after(0, lambda: self.load_btn.configure(
                    text="Charger", state="normal"))

        threading.Thread(target=load_data, daemon=True).start()

    # ── Onglets ───────────────────────────────────────────────────────────────

    def _build_tabs(self):
        if hasattr(self, "tab_bar_frame"):
            self.tab_bar_frame.destroy()
        if hasattr(self, "content_frame"):
            self.content_frame.destroy()

        # Barre d'onglets scrollable
        self.tab_bar_frame = ctk.CTkFrame(self.window, fg_color="#0d0d1a", height=120)
        self.tab_bar_frame.pack(fill="x", padx=10, pady=(5, 0))

        self.tab_scroll = ctk.CTkScrollableFrame(
            self.tab_bar_frame, orientation="horizontal",
            fg_color="#0d0d1a", height=100
        )
        self.tab_scroll.pack(fill="x", expand=True)

        # Zone de contenu
        self.content_frame = ctk.CTkFrame(self.window, fg_color=DARK)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_buttons = []

        for i, character in enumerate(self.characters):
            btn_frame = ctk.CTkFrame(self.tab_scroll, fg_color="transparent")
            btn_frame.pack(side="left", padx=4)

            # Image du perso
            try:
                pil_img = get_icon(character["image"])
                pil_img = pil_img.resize((64, 64))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(64, 64))
                
            except Exception:
                ctk_img = None

            btn = ctk.CTkButton(
                btn_frame,
                image=ctk_img,
                text=character["name"],
                compound="top",
                width=80, height=90,
                fg_color="transparent",
                hover_color="#2a2a3e",
                text_color=BEIGE,
                font=ctk.CTkFont(size=11),
                command=lambda idx=i: self._show_character(idx)
            )
            btn.pack()
            self.tab_buttons.append(btn)

        # Afficher le premier perso par défaut
        if self.characters:
            self._show_character(0)


    # ── Affichage personnage ──────────────────────────────────────────────────

    def _show_character(self, idx):
        # Highlight le bouton sélectionné
        for i, btn in enumerate(self.tab_buttons):
            btn.configure(fg_color=GOLD if i == idx else "transparent",
                        text_color=DARK if i == idx else BEIGE)

        # Vider le contenu
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        character = self.characters[idx]
        scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color=DARK)
        scroll.pack(fill="both", expand=True)

        for relic in character["relics"]:
            card = ctk.CTkFrame(scroll, fg_color="#0d0d1a", corner_radius=8)
            card.pack(fill="x", padx=10, pady=5)

            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill="x", padx=10, pady=8)

            try:
                pil_img = get_icon(relic["icon"])
                pil_img = pil_img.resize((64, 64))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(64, 64))
                ctk.CTkLabel(card_inner, image=ctk_img, text="").pack(side="left", padx=(0, 10))
                
            except Exception:
                pass

            info = ctk.CTkFrame(card_inner, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)

            # Mainstat
            main = relic.get("main_property") or {}
            main_type = str(main.get("property_type", "?"))
            main_name = self.property_map.get(main_type, {}).get("name", main_type)
            main_val = main.get("value", "?")
            
            ctk.CTkLabel(info,
                        text=f"{relic['pos_name']}  —  {relic['name']}  |  {main_name} : {main_val}",
                        text_color=GOLD,
                        font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
            
            #Substats
            for sub in relic.get("sub_property_list", []):
                prop_type = str(sub.get("property_type", "?"))
                stat_name = self.property_map.get(prop_type, {}).get("name", prop_type)
                times = sub.get("times", 0)
                detail = get_rolls_detail(prop_type, sub["value"], times)
                detail_str = f" {detail}" if detail else ""
                
                ctk.CTkLabel(info,
                            text=f"  • {stat_name} : {sub['value']}   (x{times} rolls{detail_str})",
                            text_color=BEIGE,
                            font=ctk.CTkFont(size=12)).pack(anchor="w", pady=1)

            ctk.CTkLabel(card, text="", height=5).pack()

    # ── Run ──────────────────────────────────────────────────────────────────

    def run(self):
        self.window.mainloop()