"""
app.py
======
Orchestration principale de Genshin Artifact Rater.

Responsabilités :
    - Gestion des cookies (multi-comptes, sauvegarde, migration)
    - Header fixe avec menu déroulant au survol
    - Navigation entre les pages (Login, Profil, Persos, Rater)
    - Chargement des données via l'API HoYoLAB

Les pages sont dans des fichiers séparés :
    src/login_page.py      → connexion HoYoLAB
    src/profile_page.py    → profil compte
    src/characters_view.py → onglets persos + artefacts
    src/rater_page.py      → rating manuel d'artefact
"""

import customtkinter as ctk
import threading
import json
import os
from src.hoyolab import get_all_characters, get_character_details
from src.scoring import get_rolls_detail  # noqa — importé ici pour vérif au démarrage

# ── Palette DA ────────────────────────────────────────────────────────────────
BG      = "#f0ebe0"
CARD    = "#faf7f2"
CARD2   = "#f0e8d8"
GOLD    = "#c8a96e"
TEXT    = "#3d3226"
MUTED   = "#9b8e7e"
BTN     = "#2d2520"
BTN_TXT = "#c8a96e"

HEADER_H     = 60   # Hauteur fixe du header en pixels
COOKIES_FILE = "data/cookies.json"

SERVERS = {
    "EU":  "os_euro",
    "AS":  "os_asia",
    "USA": "os_usa",
    "CHT": "os_cht",
}


class App:
    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("dark-blue")

        self.window = ctk.CTk()
        self.window.title("Genshin Artifact Rater")
        self.window.geometry("1200x800")
        self.window.configure(fg_color=BG)

        self.all_cookies    = self._load_all_cookies()
        self.active_cookies = self._get_active_account()
        self.characters     = []
        self.property_map   = {}
        self._menu_open     = False
        self._close_timer   = None

        self._show_login_page()

    # ── Gestion des cookies ───────────────────────────────────────────────────

    def _load_all_cookies(self):
        """
        Charge cookies.json complet.
        Gère l'ancien format mono-compte pour la rétrocompatibilité.
        """
        if not os.path.exists(COOKIES_FILE):
            return {}
        try:
            with open(COOKIES_FILE, "r") as f:
                data = json.load(f)
            # Ancien format → migration automatique vers multi-comptes
            if "ltuid_v2" in data:
                ltuid    = data.get("ltuid_v2", "unknown")
                migrated = {"active": ltuid, "accounts": {ltuid: data}}
                self._save_all_cookies(migrated)
                return migrated
            if "accounts" in data:
                return data
        except Exception as e:
            print(f"Erreur lecture cookies : {e}")
        return {}

    def _save_all_cookies(self, data):
        os.makedirs("data", exist_ok=True)
        with open(COOKIES_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _get_active_account(self):
        """Retourne le dict de cookies du compte actif, ou None."""
        active_id = self.all_cookies.get("active")
        accounts  = self.all_cookies.get("accounts", {})
        if not active_id or active_id not in accounts:
            return None
        account  = accounts[active_id]
        required = ["ltuid_v2", "ltoken_v2", "cookie_token_v2"]
        return account if all(k in account for k in required) else None

    def _save_account(self, cookies, uid=None, nickname=None, server=None):
        """
        Sauvegarde ou met à jour un compte dans cookies.json.
        Reconstruit le header si un nouveau nickname est obtenu.
        """
        ltuid   = cookies.get("ltuid_v2", "unknown")
        account = dict(cookies)
        if uid:
            account["uid"] = uid
        if nickname:
            account["nickname"] = nickname
        if server:
            account["server"] = server
        self.all_cookies.setdefault("accounts", {})[ltuid] = account
        self.all_cookies["active"] = ltuid
        self._save_all_cookies(self.all_cookies)
        self.active_cookies = account
        # Mettre à jour le bouton du header avec le nouveau nickname
        if nickname and hasattr(self, "header") and self.header.winfo_exists():
            self.window.after(0, self._build_header)

    # ── Zone de contenu ───────────────────────────────────────────────────────

    def _clear_content(self):
        """
        Détruit et recrée la zone de contenu principale (sous le header).
        Le header (place()) n'est jamais touché par cette méthode.
        """
        self._close_menu()
        if hasattr(self, "content_area") and self.content_area.winfo_exists():
            self.content_area.destroy()
        self.content_area = ctk.CTkFrame(self.window, fg_color=BG, corner_radius=0)
        self.content_area.pack(fill="both", expand=True)

    # ── Page de connexion ─────────────────────────────────────────────────────

    def _show_login_page(self):
        """Instancie et affiche LoginPage."""
        from src.login_page import LoginPage
        self.login_page = LoginPage(
            window=self.window,
            all_cookies=self.all_cookies,
            on_success=self._on_login_success
        )

    def _on_login_success(self, cookies, uid, server):
        """
        Callback après connexion réussie.
        Construit le header, crée la zone de contenu et affiche le profil.
        """
        self._save_account(cookies, uid=uid, server=server)
        self.active_cookies = self._get_active_account()
        self.all_cookies    = self._load_all_cookies()

        self.login_page.destroy()
        self._build_header()
        self._clear_content()
        self._show_profile_page()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        """
        Header fixe en haut avec place().
        Titre à gauche, bouton [nickname ▼] à droite.
        Le menu s'ouvre au survol du bouton.
        """
        if hasattr(self, "header") and self.header.winfo_exists():
            self.header.destroy()

        self.header = ctk.CTkFrame(self.window, fg_color=CARD2,
                                   corner_radius=0, height=HEADER_H)
        self.header.place(x=0, y=0, relwidth=1.0)
        self.header.pack_propagate(False)

        # Séparateur doré en bas du header
        ctk.CTkFrame(self.header, fg_color=GOLD, height=1,
                     corner_radius=0).pack(fill="x", side="bottom")

        # Titre
        ctk.CTkLabel(self.header,
                     text="✦ Genshin Artifact Rater ✦",
                     font=ctk.CTkFont(family="Georgia", size=20, weight="bold"),
                     text_color=TEXT).pack(side="left", padx=20, pady=12)

        # Bouton [nickname ▼]
        nickname = "Mon compte"
        if self.active_cookies:
            nickname = self.active_cookies.get("nickname", "Mon compte")

        self.menu_btn = ctk.CTkButton(
            self.header,
            text=f"{nickname}  ▼",
            width=160, height=34,
            fg_color=BTN, text_color=BTN_TXT,
            hover_color="#1a1510",
            font=ctk.CTkFont(family="Georgia", size=13),
            corner_radius=3,
            command=None  # Ouverture au survol uniquement
        )
        self.menu_btn.pack(side="right", padx=20, pady=13)

        self.menu_btn.bind("<Enter>", lambda e: self._open_menu())
        self.menu_btn.bind("<Leave>", lambda e: self._schedule_close())

        self._menu_open = False

        # S'assurer que content_area est visible sous le header
        if hasattr(self, "content_area") and self.content_area.winfo_exists():
            self.content_area.lift()

    # ── Menu déroulant ────────────────────────────────────────────────────────

    def _open_menu(self):
        """Affiche le menu déroulant sous le bouton compte."""
        self._cancel_close()

        if hasattr(self, "dropdown") and self.dropdown.winfo_exists():
            return

        self._menu_open = True

        # Forcer le rendu avant de calculer les positions du bouton
        self.window.update_idletasks()

        x = self.menu_btn.winfo_rootx() - self.window.winfo_rootx()
        y = (self.menu_btn.winfo_rooty() - self.window.winfo_rooty()
             + self.menu_btn.winfo_height() + 2)

        self.dropdown = ctk.CTkFrame(self.window, fg_color=CARD,
                                      corner_radius=4, border_width=1,
                                      border_color=GOLD)
        self.dropdown.place(x=x, y=y)
        self.dropdown.lift()

        self.dropdown.bind("<Enter>", lambda e: self._cancel_close())
        self.dropdown.bind("<Leave>", lambda e: self._schedule_close())

        def item(text, command, sep=False):
            btn = ctk.CTkButton(
                self.dropdown, text=text,
                width=190, height=36,
                fg_color="transparent", hover_color="#e8e0d0",
                text_color=TEXT, anchor="w",
                font=ctk.CTkFont(family="Georgia", size=13),
                corner_radius=0,
                command=lambda: [self._close_menu(), command()]
            )
            btn.pack(fill="x", padx=2, pady=1)
            btn.bind("<Enter>", lambda e: self._cancel_close())
            btn.bind("<Leave>", lambda e: self._schedule_close())
            if sep:
                ctk.CTkFrame(self.dropdown, fg_color=GOLD, height=1,
                             corner_radius=0).pack(fill="x", padx=8, pady=2)

        item("👤  Profil",            self._show_profile_page,  sep=True)
        item("🎯  Rater un artefact", self._open_rater_page,    sep=True)
        item("🔄  Changer de compte", self._change_account)
        item("➕  Ajouter un compte", self._add_account,         sep=True)
        item("🚪  Se déconnecter",    self._disconnect)

    def _schedule_close(self):
        """Ferme le menu après 200ms — annulable si la souris revient."""
        self._close_timer = self.window.after(200, self._close_menu)

    def _cancel_close(self):
        """Annule la fermeture programmée."""
        if self._close_timer:
            self.window.after_cancel(self._close_timer)
            self._close_timer = None

    def _close_menu(self):
        """Ferme et détruit le menu déroulant."""
        self._menu_open   = False
        self._close_timer = None
        if hasattr(self, "dropdown") and self.dropdown.winfo_exists():
            self.dropdown.destroy()

    # ── Actions du menu ───────────────────────────────────────────────────────

    def _show_profile_page(self):
        """Affiche la page profil."""
        self._clear_content()
        from src.profile_page import ProfilePage
        self.profile_page = ProfilePage(
            parent=self.content_area,
            active_cookies=self.active_cookies,
            on_load=self._on_load_characters
        )

    def _open_rater_page(self):
        """Ouvre le rater en popup CTkToplevel."""
        from src.rater_page import RaterPage
        RaterPage(self.window, cookies=self.active_cookies)

    def _change_account(self):
        """Retourne à la page de connexion pour changer de compte."""
        for widget in self.window.winfo_children():
            widget.destroy()
        self._show_login_page()

    def _add_account(self):
        """Retourne à la page de connexion pour ajouter un compte."""
        for widget in self.window.winfo_children():
            widget.destroy()
        self._show_login_page()

    def _disconnect(self):
        """Supprime les cookies et retourne à la page de connexion."""
        if os.path.exists(COOKIES_FILE):
            os.remove(COOKIES_FILE)
        self.all_cookies    = {}
        self.active_cookies = None
        self.characters     = []
        for widget in self.window.winfo_children():
            widget.destroy()
        self._show_login_page()

    # ── Chargement des personnages ────────────────────────────────────────────

    def _on_load_characters(self, uid, server):
        """
        Lancé par ProfilePage au clic sur Charger.
        Récupère les persos via l'API HoYoLAB dans un thread séparé.
        Affiche CharactersView immédiatement, icônes en arrière-plan.
        """
        cookies = {
            "ltuid_v2":        self.active_cookies["ltuid_v2"],
            "ltoken_v2":       self.active_cookies["ltoken_v2"],
            "cookie_token_v2": self.active_cookies["cookie_token_v2"],
            "account_mid_v2":  self.active_cookies["account_mid_v2"],
            "account_id_v2":   self.active_cookies["account_id_v2"],
            "mi18nLang":       "fr-fr",
        }

        def load_data():
            try:
                avatars = get_all_characters(cookies, uid, server=server)
                ids     = [a["id"] for a in avatars]
                details, property_map = get_character_details(
                    cookies, uid, ids, server=server)

                self.property_map = property_map
                self.characters   = []
                for d in details:
                    self.characters.append({
                        "id":      d["base"]["id"],
                        "name":    d["base"]["name"],
                        "icon":    d["base"]["icon"],
                        "image":   d["base"]["image"],
                        "element": d["base"]["element"],
                        "level":   d["base"]["level"],
                        "relics":  d["relics"],
                    })

                self._save_account(self.active_cookies, uid=uid, server=server)

                # Récupérer le nickname avec le vrai UID (première fois qu'on l'a)
                def fetch_nickname():
                    try:
                        from src.hoyolab import get_hoyolab_nickname
                        result = get_hoyolab_nickname(cookies, uid=uid, server=server)
                        if result:
                            self._save_account(self.active_cookies,
                                               nickname=result["nickname"])
                    except Exception as e:
                        print(f"Nickname non récupéré : {e}")
                threading.Thread(target=fetch_nickname, daemon=True).start()

                # Afficher les personnages immédiatement
                self.window.after(0, self._show_characters_view)

            except Exception as e:
                error_msg = str(e)
                print(f"Erreur chargement : {error_msg}")
                if "login" in error_msg.lower() or "please" in error_msg.lower():
                    self.window.after(0, self._show_login_page)
                else:
                    self.window.after(0, lambda: self._show_error(
                        f"Erreur : {error_msg}"))

            finally:
                # Réactiver le bouton si ProfilePage est encore visible
                if hasattr(self, "profile_page"):
                    try:
                        self.window.after(
                            0, lambda: self.profile_page.set_loading(False))
                    except Exception:
                        pass

        threading.Thread(target=load_data, daemon=True).start()

    def _show_characters_view(self):
        """Instancie CharactersView dans la zone de contenu."""
        self._clear_content()
        from src.characters_view import CharactersView
        self.chars_view = CharactersView(
            parent=self.content_area,
            characters=self.characters,
            property_map=self.property_map
        )

    def _show_error(self, message):
        """Affiche un message d'erreur temporaire dans la zone de contenu."""
        if hasattr(self, "error_label") and self.error_label.winfo_exists():
            self.error_label.destroy()
        if hasattr(self, "content_area") and self.content_area.winfo_exists():
            self.error_label = ctk.CTkLabel(
                self.content_area, text=f"⚠ {message}",
                text_color="#c0392b",
                font=ctk.CTkFont(family="Georgia", size=12))
            self.error_label.pack(pady=10)
            self.window.after(5000, lambda: self.error_label.destroy()
                              if hasattr(self, "error_label") and
                              self.error_label.winfo_exists() else None)

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        """Lance la boucle principale de l'interface graphique."""
        self.window.mainloop()