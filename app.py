import customtkinter as ctk
import threading
import json
import os
from PIL import Image
from hoyolab import get_all_characters, get_character_details, get_icon
from scoring import get_rolls_detail

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

        self.cookies = self._load_cookies()
        self._build_header()

    # ── Cookies ──────────────────────────────────────────────────────────────

    def _load_cookies(self):
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, "r") as f:
                return json.load(f)
        return {}

    def _save_cookies(self, uid, cookies):
        all_cookies = self._load_cookies()
        all_cookies[uid] = cookies
        with open(COOKIES_FILE, "w") as f:
            json.dump(all_cookies, f)

    # ── Header ───────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self.window, fg_color="#0d0d1a", height=80, corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(header, text="✦ Genshin Artifact Rater ✦",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=GOLD).pack(side="left", padx=20, pady=20)

        # Champs cookies (masqués si déjà sauvegardés)
        self.ltuid_entry = ctk.CTkEntry(header, placeholder_text="ltuid_v2",
                                        width=120, height=36,
                                        fg_color="#2a2a3e", border_color=GOLD,
                                        text_color=BEIGE)
        self.ltuid_entry.pack(side="left", padx=5, pady=20)
        if self.cookies.get("ltuid_v2"):
            self.ltuid_entry.insert(0, self.cookies["ltuid_v2"])

        self.ltoken_entry = ctk.CTkEntry(header, placeholder_text="ltoken_v2",
                                         width=180, height=36, show="*",
                                         fg_color="#2a2a3e", border_color=GOLD,
                                         text_color=BEIGE)
        self.ltoken_entry.pack(side="left", padx=5, pady=20)
        if self.cookies.get("ltoken_v2"):
            self.ltoken_entry.insert(0, self.cookies["ltoken_v2"])

        self.uid_entry = ctk.CTkEntry(header, placeholder_text="UID Genshin",
                                      width=140, height=36,
                                      fg_color="#2a2a3e", border_color=GOLD,
                                      text_color=BEIGE)
        self.uid_entry.pack(side="left", padx=5, pady=20)

        def on_load():
            ltuid  = self.ltuid_entry.get()
            ltoken = self.ltoken_entry.get()
            uid    = self.uid_entry.get()
            if not uid:
                return

            # Si cookies pas remplis, essaye de les charger depuis la sauvegarde
            if not ltuid or not ltoken:
                saved = self.cookies.get(uid)
                if saved:
                    ltuid  = saved["ltuid_v2"]
                    ltoken = saved["ltoken_v2"]
                else:
                    return  # Pas de cookies connus pour cet UID

            cookies = {
                "ltuid_v2": ltuid,
                "ltoken_v2": ltoken,
                "mi18nLang": "fr-fr",
            }
            self._save_cookies(uid, cookies)
            self.cookies = self._load_cookies()

            # ← cookies actifs pour cette session
            active_cookies = cookies

            self.load_btn.configure(text="Chargement...", state="disabled")

            def load_data():
                try:
                    avatars = get_all_characters(active_cookies, uid)
                    ids = [a["id"] for a in avatars]
                    details, property_map = get_character_details(active_cookies, uid, ids)
                    self.property_map = property_map
                    # Fusionner infos de base + détails
                    base_map = {a["id"]: a for a in avatars}
                    self.characters = []
                    for d in details:
                        base = base_map.get(d["base"]["id"], {})
                        self.characters.append({
                            "id":       d["base"]["id"],
                            "name":     d["base"]["name"],
                            "image":    d["base"]["image"],
                            "element":  d["base"]["element"],
                            "level":    d["base"]["level"],
                            "relics":   d["relics"],
                        })
                    self.window.after(0, self._build_tabs)
                except Exception as e:
                    print(f"Erreur : {e}")
                finally:
                    self.window.after(0, lambda: self.load_btn.configure(
                        text="Charger", state="normal"))

            threading.Thread(target=load_data, daemon=True).start()

        self.load_btn = ctk.CTkButton(header, text="Charger",
                                      width=100, height=36,
                                      fg_color=GOLD, text_color=DARK,
                                      hover_color="#a08050", command=on_load)
        self.load_btn.pack(side="left", padx=5, pady=20)
        
        def on_uid_change(event=None):
            uid = self.uid_entry.get()
            saved = self.cookies.get(uid)
            if saved:
                self.ltuid_entry.delete(0, "end")
                self.ltuid_entry.insert(0, saved["ltuid_v2"])
                self.ltoken_entry.delete(0, "end")
                self.ltoken_entry.insert(0, saved["ltoken_v2"])

        self.uid_entry.bind("<KeyRelease>", on_uid_change)

    # ── Onglets ───────────────────────────────────────────────────────────────

    def _build_tabs(self):
        if hasattr(self, "tabview"):
            self.tabview.destroy()
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

        self.current_scroll = None
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