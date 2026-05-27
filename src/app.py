"""
app.py
======
Interface graphique principale de Genshin Artifact Rater.
Construit avec CustomTkinter (thème doré/sombre).

Flux général :
    1. Au démarrage, on tente de charger les cookies depuis data/cookies.json
    2. Si plusieurs comptes → on charge le compte actif
    3. Si aucun compte → page de connexion HoYoLAB (Playwright)
    4. Une fois connecté → header avec sélecteur de compte, serveur, champ UID
    5. Au clic sur Charger → récupération des personnages via l'API HoYoLAB
    6. Affichage des artefacts avec icônes, mainstats et substats détaillées
"""

import customtkinter as ctk
import threading
import json
import os
from PIL import Image
from src.hoyolab import get_all_characters, get_character_details, get_icon
from src.scoring import get_rolls_detail
from src.auth import login_and_get_cookies

# ── Constantes visuelles ──────────────────────────────────────────────────────
GOLD  = "#c8a96e"
BEIGE = "#f0e6d3"
DARK  = "#1a1a2e"

COOKIES_FILE = "data/cookies.json"

# ── Serveurs disponibles ──────────────────────────────────────────────────────
# Clé : label affiché dans le dropdown
# Valeur : identifiant serveur pour l'API HoYoLAB
SERVERS = {
    "EU":  "os_euro",
    "AS":  "os_asia",
    "USA": "os_usa",
    "CHT": "os_cht",
}


class App:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.window = ctk.CTk()
        self.window.title("Genshin Artifact Rater")
        self.window.geometry("1200x800")
        self.window.configure(fg_color=DARK)

        # Chargement des cookies — structure multi-comptes
        self.all_cookies = self._load_all_cookies()
        self.active_cookies = self._get_active_account()

        if self.active_cookies:
            self._build_header()
        else:
            self._build_login_page()


    # ── Gestion des cookies (multi-comptes) ───────────────────────────────────

    def _load_all_cookies(self):
        """
        Charge le fichier cookies.json complet.
        Format attendu :
        {
            "active": "ltuid_du_compte_actif",
            "accounts": {
                "137283572": {
                    "nickname": "4rt0ine",
                    "uid": "720978846",
                    "server": "os_euro",
                    "ltuid_v2": "...",
                    ...
                }
            }
        }
        Gère aussi l'ancien format à compte unique pour la rétrocompatibilité.
        Retourne un dict vide si le fichier est absent ou invalide.
        """
        if not os.path.exists(COOKIES_FILE):
            return {}

        try:
            with open(COOKIES_FILE, "r") as f:
                data = json.load(f)

            # Ancien format (compte unique à la racine) → migration automatique
            if "ltuid_v2" in data:
                ltuid = data.get("ltuid_v2", "unknown")
                migrated = {
                    "active": ltuid,
                    "accounts": {ltuid: data}
                }
                self._save_all_cookies(migrated)
                return migrated

            # Nouveau format multi-comptes
            if "accounts" in data:
                return data

        except Exception as e:
            print(f"Erreur lecture cookies : {e}")

        return {}

    def _save_all_cookies(self, data):
        """
        Sauvegarde le dict complet des cookies (tous les comptes).
        """
        os.makedirs("data", exist_ok=True)
        with open(COOKIES_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _get_active_account(self):
        """
        Retourne le dict de cookies du compte actif.
        Retourne None si aucun compte n'est enregistré ou si les clés
        essentielles sont manquantes.
        """
        active_id = self.all_cookies.get("active")
        accounts  = self.all_cookies.get("accounts", {})

        if not active_id or active_id not in accounts:
            return None

        account  = accounts[active_id]
        required = ["ltuid_v2", "ltoken_v2", "cookie_token_v2"]
        if all(k in account for k in required):
            return account

        return None

    def _save_account(self, cookies, uid=None, nickname=None, server=None):
        """
        Ajoute ou met à jour un compte dans cookies.json.
        Le compte devient automatiquement le compte actif.
        Si nickname est fourni, reconstruit le header pour mettre à jour
        le dropdown avec le vrai pseudo.
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

        # Mettre à jour active_cookies en mémoire
        self.active_cookies = account

        # Reconstruire le header si le nickname vient d'être obtenu
        if nickname and hasattr(self, "header"):
            self.window.after(0, self._build_header)

    def _switch_account(self, ltuid):
        """
        Change le compte actif sans se reconnecter.
        Reconstruit le header pour mettre à jour l'UID et le serveur pré-remplis.
        """
        self.all_cookies["active"] = ltuid
        self._save_all_cookies(self.all_cookies)
        self.active_cookies = self._get_active_account()

    # ── Page de connexion ─────────────────────────────────────────────────────

    def _build_login_page(self):
        """
        Affiche la page de connexion initiale.
        Apparaît au premier lancement ou quand tous les comptes sont supprimés.
        """
        # Détruire les widgets existants si on revient à la page de connexion
        for widget in self.window.winfo_children():
            widget.destroy()

        self.login_frame = ctk.CTkFrame(self.window, fg_color=DARK)
        self.login_frame.pack(fill="both", expand=True)

        # Titre centré
        ctk.CTkLabel(self.login_frame,
                     text="✦ Genshin Artifact Rater ✦",
                     font=ctk.CTkFont(size=32, weight="bold"),
                     text_color=GOLD).pack(pady=(120, 10))

        ctk.CTkLabel(self.login_frame,
                     text="Évalue tes artefacts Genshin Impact",
                     font=ctk.CTkFont(size=14),
                     text_color=BEIGE).pack(pady=(0, 60))

        # Bouton de connexion principal
        self.connect_btn = ctk.CTkButton(
            self.login_frame,
            text="Se connecter avec HoYoLAB",
            width=300, height=52,
            fg_color=GOLD, text_color=DARK,
            hover_color="#a08050",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._do_login
        )
        self.connect_btn.pack()

        ctk.CTkLabel(self.login_frame,
                     text="Une fenêtre de connexion HoYoLAB s'ouvrira",
                     font=ctk.CTkFont(size=11),
                     text_color="#888888").pack(pady=(12, 0))

    def _do_login(self):
        """
        Lance la connexion HoYoLAB via Playwright.
        L'appel est direct (pas de thread) car Playwright doit tourner
        dans le thread principal sur Windows.
        On force un rafraîchissement de l'UI avant de bloquer.
        Après connexion, tente de récupérer le nickname HoYoLAB.
        """
        self.connect_btn.configure(text="Connexion en cours...", state="disabled")
        self.window.update()  # Affiche le texte avant de bloquer

        cookies = login_and_get_cookies()

        if cookies:
            # Sauvegarder les cookies bruts d'abord
            self._save_account(cookies)
            self.active_cookies = cookies
            self.all_cookies    = self._load_all_cookies()
            self.login_frame.destroy()
            self._build_header()

            # Tenter de récupérer le nickname HoYoLAB en arrière-plan
            # On utilise account_id_v2 comme role_id pour l'appel /api/index
            def fetch_nickname():
                try:
                    from src.hoyolab import get_hoyolab_nickname
                    result = get_hoyolab_nickname(cookies)
                    if result:
                        self._save_account(
                            cookies,
                            nickname=result["nickname"],
                            uid=result.get("uid")
                        )
                except Exception as e:
                    print(f"Impossible de récupérer le nickname : {e}")

            threading.Thread(target=fetch_nickname, daemon=True).start()
        else:
            # Échec ou timeout → réactiver le bouton
            self.connect_btn.configure(
                text="Se connecter avec HoYoLAB", state="normal")

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        """
        Construit le header de l'application.
        Contient : titre, sélecteur de compte, sélecteur de serveur,
                   bouton + compte, champ UID, bouton Charger.
        Peut être appelé plusieurs fois (switch de compte, mise à jour nickname).
        """
        # Détruire l'ancien header si existant
        if hasattr(self, "header"):
            self.header.destroy()

        self.header = ctk.CTkFrame(self.window, fg_color="#0d0d1a", height=80, corner_radius=0)
        self.header.pack(fill="x")

        # Titre à gauche
        ctk.CTkLabel(self.header,
                     text="✦ Genshin Artifact Rater ✦",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=GOLD).pack(side="left", padx=20, pady=20)

        # ── Éléments à droite (packés right→left) ────────────────────────────

        # Bouton Charger
        self.load_btn = ctk.CTkButton(
            self.header, text="Charger",
            width=100, height=36,
            fg_color=GOLD, text_color=DARK,
            hover_color="#a08050",
            command=self._on_load
        )
        self.load_btn.pack(side="right", padx=5, pady=20)

        # Champ UID
        self.uid_entry = ctk.CTkEntry(
            self.header, placeholder_text="UID Genshin",
            width=140, height=36,
            fg_color="#2a2a3e", border_color=GOLD,
            text_color=BEIGE
        )
        self.uid_entry.pack(side="right", padx=5, pady=20)

        # Pré-remplir l'UID si sauvegardé pour ce compte
        uid = self.active_cookies.get("uid") if self.active_cookies else None
        if uid:
            self.uid_entry.insert(0, uid)

        # Sélecteur de serveur
        # Pré-sélectionner le serveur sauvegardé pour ce compte (défaut : EU)
        saved_server = self.active_cookies.get("server", "os_euro") if self.active_cookies else "os_euro"
        default_server_label = next(
            (lbl for lbl, val in SERVERS.items() if val == saved_server), "EU"
        )
        self.server_var = ctk.StringVar(value=default_server_label)
        ctk.CTkOptionMenu(
            self.header,
            values=list(SERVERS.keys()),
            variable=self.server_var,
            width=80, height=36,
            fg_color="#2a2a3e",
            button_color=GOLD,
            button_hover_color="#a08050",
            text_color=BEIGE,
        ).pack(side="right", padx=5, pady=20)

        # Bouton + Compte (ajouter un nouveau compte)
        ctk.CTkButton(
            self.header, text="+ Compte",
            width=90, height=36,
            fg_color="#2a2a3e", text_color=BEIGE,
            hover_color="#3a3a5e",
            command=self._add_account
        ).pack(side="right", padx=5, pady=20)

        # Sélecteur de compte (dropdown)
        # Affiche le nickname si disponible, sinon "Nouveau compte"
        accounts = self.all_cookies.get("accounts", {})
        if accounts:
            account_labels = {}
            for ltuid, acc in accounts.items():
                nickname = acc.get("nickname", "")
                label    = nickname if nickname else "Nouveau compte"
                # Gérer les doublons de label (ex: deux comptes sans nickname)
                if label in account_labels:
                    label = f"{label} ({ltuid[:6]})"
                account_labels[label] = ltuid

            self._account_labels = account_labels

            # Trouver le label du compte actif
            active_ltuid   = self.all_cookies.get("active", "")
            active_label   = next(
                (lbl for lbl, lid in account_labels.items() if lid == active_ltuid),
                list(account_labels.keys())[0]
            )

            self.account_var = ctk.StringVar(value=active_label)
            ctk.CTkOptionMenu(
                self.header,
                values=list(account_labels.keys()),
                variable=self.account_var,
                width=160, height=36,
                fg_color="#2a2a3e",
                button_color=GOLD,
                button_hover_color="#a08050",
                text_color=BEIGE,
                command=self._on_account_switch
            ).pack(side="right", padx=10, pady=20)

    def _on_account_switch(self, selected_label):
        """
        Appelé quand l'utilisateur sélectionne un compte dans le dropdown.
        Change le compte actif et reconstruit le header avec l'UID et le
        serveur correspondants.
        """
        ltuid = self._account_labels.get(selected_label)
        if not ltuid:
            return

        self._switch_account(ltuid)
        self._build_header()

    def _add_account(self):
        """
        Ouvre Playwright pour connecter un nouveau compte HoYoLAB.
        Le nouveau compte est ajouté à la liste et devient le compte actif.
        """
        self.window.update()
        cookies = login_and_get_cookies()

        if cookies:
            self._save_account(cookies)
            self.active_cookies = cookies
            self.all_cookies    = self._load_all_cookies()
            self._build_header()

            # Récupérer le nickname en arrière-plan
            def fetch_nickname():
                try:
                    from src.hoyolab import get_hoyolab_nickname
                    result = get_hoyolab_nickname(cookies)
                    if result:
                        self._save_account(
                            cookies,
                            nickname=result["nickname"],
                            uid=result.get("uid")
                        )
                except Exception as e:
                    print(f"Impossible de récupérer le nickname : {e}")

            threading.Thread(target=fetch_nickname, daemon=True).start()

    # ── Chargement des données ────────────────────────────────────────────────

    def _on_load(self):
        """
        Lance le chargement des personnages et artefacts depuis l'API HoYoLAB.
        Tourne dans un thread séparé pour ne pas bloquer l'UI.
        Sauvegarde l'UID et le serveur choisi pour ce compte.
        """
        uid = self.uid_entry.get().strip()
        if not uid:
            return

        # Récupérer le serveur sélectionné dans le dropdown
        server = SERVERS.get(self.server_var.get(), "os_euro")

        # Construire les cookies pour l'appel API
        # On ajoute mi18nLang pour forcer le français dans les réponses
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
                # Récupérer tous les personnages
                avatars = get_all_characters(cookies, uid, server=server)
                ids     = [a["id"] for a in avatars]

                # Récupérer les détails (artefacts + property_map)
                details, property_map = get_character_details(cookies, uid, ids, server=server)
                self.property_map = property_map

                # Construire la liste des personnages
                self.characters = []
                for d in details:
                    self.characters.append({
                        "id":      d["base"]["id"],
                        "name":    d["base"]["name"],
                        "image":   d["base"]["image"],
                        "element": d["base"]["element"],
                        "level":   d["base"]["level"],
                        "relics":  d["relics"],
                    })

                # Sauvegarder l'UID et le serveur pour ce compte
                self._save_account(self.active_cookies, uid=uid, server=server)

                # Pré-télécharger toutes les icônes en parallèle
                # (évite le lag lors de la navigation entre les onglets)
                def prefetch(url):
                    try:
                        get_icon(url)
                    except Exception:
                        pass

                threads = [
                    threading.Thread(target=prefetch, args=(c["image"],), daemon=True)
                    for c in self.characters
                ]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                self.window.after(0, self._build_tabs)

            except Exception as e:
                error_msg = str(e)
                print(f"Erreur chargement : {error_msg}")

                # Cookies expirés → reproposer la connexion
                if "login" in error_msg.lower() or "please" in error_msg.lower():
                    self.window.after(0, self._build_login_page)
                else:
                    # Autre erreur (UID invalide, mauvais serveur...) → message
                    self.window.after(0, lambda: self._show_error(
                        f"Erreur : {error_msg}"))

            finally:
                # Toujours réactiver le bouton même en cas d'erreur
                self.window.after(0, lambda: self.load_btn.configure(
                    text="Charger", state="normal"))

        threading.Thread(target=load_data, daemon=True).start()

    def _show_error(self, message):
        """
        Affiche un message d'erreur temporaire sous le header.
        Disparaît automatiquement après 5 secondes.
        """
        if hasattr(self, "error_label"):
            self.error_label.destroy()

        self.error_label = ctk.CTkLabel(
            self.window,
            text=f"⚠ {message}",
            text_color="#ff6b6b",
            font=ctk.CTkFont(size=12)
        )
        self.error_label.pack(pady=5)
        self.window.after(5000, lambda: self.error_label.destroy()
                          if hasattr(self, "error_label") else None)

    # ── Onglets personnages ───────────────────────────────────────────────────

    def _build_tabs(self):
        """
        Construit la barre d'onglets scrollable avec les images des personnages
        et la zone de contenu principale.
        Détruit les anciens widgets si on recharge.
        """
        if hasattr(self, "tab_bar_frame"):
            self.tab_bar_frame.destroy()
        if hasattr(self, "content_frame"):
            self.content_frame.destroy()

        # Barre d'onglets scrollable horizontalement
        self.tab_bar_frame = ctk.CTkFrame(self.window, fg_color="#0d0d1a", height=120)
        self.tab_bar_frame.pack(fill="x", padx=10, pady=(5, 0))

        self.tab_scroll = ctk.CTkScrollableFrame(
            self.tab_bar_frame, orientation="horizontal",
            fg_color="#0d0d1a", height=100
        )
        self.tab_scroll.pack(fill="x", expand=True)

        # Zone de contenu (artefacts du personnage sélectionné)
        self.content_frame = ctk.CTkFrame(self.window, fg_color=DARK)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_buttons = []

        for i, character in enumerate(self.characters):
            btn_frame = ctk.CTkFrame(self.tab_scroll, fg_color="transparent")
            btn_frame.pack(side="left", padx=4)

            # Charger l'icône depuis le cache local
            try:
                pil_img = get_icon(character["image"])
                pil_img = pil_img.resize((64, 64))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(64, 64))
            except Exception:
                ctk_img = None

            # Bouton avec image au-dessus du nom du personnage
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

        # Afficher le premier personnage par défaut
        if self.characters:
            self._show_character(0)

    # ── Affichage des artefacts ───────────────────────────────────────────────

    def _show_character(self, idx):
        """
        Affiche les artefacts du personnage à l'index idx.
        Met en évidence l'onglet actif (fond doré, texte sombre).
        Affiche pour chaque artefact : slot, nom, mainstat, substats avec
        détail des rolls (qualité de chaque roll ex: [4, 3, 4]).
        """
        # Mettre à jour le style des boutons d'onglets
        for i, btn in enumerate(self.tab_buttons):
            btn.configure(
                fg_color=GOLD if i == idx else "transparent",
                text_color=DARK if i == idx else BEIGE
            )

        # Vider la zone de contenu
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        character = self.characters[idx]

        # Zone scrollable pour les 5 artefacts
        scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color=DARK)
        scroll.pack(fill="both", expand=True)

        for relic in character["relics"]:
            # Carte d'artefact
            card = ctk.CTkFrame(scroll, fg_color="#0d0d1a", corner_radius=8)
            card.pack(fill="x", padx=10, pady=5)

            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill="x", padx=10, pady=8)

            # Icône de l'artefact (depuis le cache local)
            try:
                pil_img = get_icon(relic["icon"])
                pil_img = pil_img.resize((64, 64))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(64, 64))
                ctk.CTkLabel(card_inner, image=ctk_img, text="").pack(
                    side="left", padx=(0, 10))
            except Exception:
                pass

            # Zone texte à droite de l'icône
            info = ctk.CTkFrame(card_inner, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)

            # Mainstat : "slot — nom artefact | nom stat : valeur"
            main      = relic.get("main_property") or {}
            main_type = str(main.get("property_type", "?"))
            main_name = self.property_map.get(main_type, {}).get("name", main_type)
            main_val  = main.get("value", "?")

            ctk.CTkLabel(
                info,
                text=f"{relic['pos_name']}  —  {relic['name']}  |  {main_name} : {main_val}",
                text_color=GOLD,
                font=ctk.CTkFont(size=13, weight="bold")
            ).pack(anchor="w")

            # Substats avec détail des rolls
            for sub in relic.get("sub_property_list", []):
                prop_type = sub.get("property_type", "?")
                stat_name = self.property_map.get(
                    str(prop_type), {}).get("name", str(prop_type))
                times     = sub.get("times", 0)

                # Convertir prop_type en int pour PROPERTY_TYPE_MAP (clés int)
                prop_type_int = int(prop_type) if str(prop_type).isdigit() else prop_type
                detail        = get_rolls_detail(prop_type_int, sub["value"], times)
                detail_str    = f" {detail}" if detail else ""

                ctk.CTkLabel(
                    info,
                    text=f"  • {stat_name} : {sub['value']}   (×{times} rolls{detail_str})",
                    text_color=BEIGE,
                    font=ctk.CTkFont(size=12)
                ).pack(anchor="w", pady=1)

            # Espaceur en bas de carte
            ctk.CTkLabel(card, text="", height=5).pack()

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        """Lance la boucle principale de l'interface graphique."""
        self.window.mainloop()