"""
login_page.py
=============
Page de connexion de Genshin Artifact Rater.
Style inspiré de l'interface officielle Genshin Impact :
- Fond crème/beige chaud
- Bordures et accents dorés
- Champs épurés sur fond blanc
- Bouton sombre avec texte doré

Utilisation depuis app.py :
    from src.login_page import LoginPage
    LoginPage(self.window, all_cookies=self.all_cookies, on_success=self._on_login_success)

Le callback on_success reçoit (cookies, uid, server) une fois la connexion établie.
"""

import customtkinter as ctk
import threading

# ── Palette de couleurs style Genshin ─────────────────────────────────────────
LOGIN_BG      = "#f0ebe0"   # Fond crème/beige chaud
LOGIN_CARD    = "#faf7f2"   # Fond de la carte, légèrement plus clair
LOGIN_GOLD    = "#c8a96e"   # Or Genshin (bordures, accents)
LOGIN_TEXT    = "#3d3226"   # Brun foncé (texte principal)
LOGIN_MUTED   = "#9b8e7e"   # Gris-brun (texte secondaire)
LOGIN_BTN     = "#2d2520"   # Fond bouton principal (sombre)
LOGIN_BTN_TXT = "#c8a96e"   # Texte doré sur bouton sombre
LOGIN_RED     = "#c0392b"   # Astérisque champs obligatoires

# ── Serveurs disponibles ──────────────────────────────────────────────────────
SERVER_LABELS = {
    "Europe":   "os_euro",
    "Asie":     "os_asia",
    "Amérique": "os_usa",
    "TW/HK/MO": "os_cht",
}


class LoginPage:
    """
    Page de connexion style Genshin Impact.

    Deux modes selon l'état des cookies :
    - Premier lancement (pas de comptes) → bouton HoYoLAB uniquement
    - Comptes existants → champs UID + serveur + bouton Connexion
                          + bouton secondaire pour ajouter un compte
    """

    def __init__(self, window, all_cookies, on_success):
        """
        window      : fenêtre CTk principale (App.window)
        all_cookies : dict complet des cookies (format multi-comptes)
        on_success  : callback appelé avec (cookies, uid, server) après connexion
        """
        self.window      = window
        self.all_cookies = all_cookies
        self.on_success  = on_success

        # Changer le fond de la fenêtre en beige pour la page de connexion
        self.window.configure(fg_color=LOGIN_BG)

        # Détruire les widgets existants
        for widget in self.window.winfo_children():
            widget.destroy()

        self._build()

    # ── Construction de l'UI ──────────────────────────────────────────────────

    def _build(self):
        """Construit toute la page de connexion."""

        # Conteneur centré dans la fenêtre
        outer = ctk.CTkFrame(self.window, fg_color=LOGIN_BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        # ── Ornement supérieur ────────────────────────────────────────────────
        ctk.CTkLabel(outer,
                     text="◈──────────────────────────────◈",
                     font=ctk.CTkFont(family="Georgia", size=13),
                     text_color=LOGIN_GOLD).pack(pady=(0, 8))

        # ── Titre ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(outer,
                     text="Genshin Artifact Rater",
                     font=ctk.CTkFont(family="Georgia", size=28, weight="bold"),
                     text_color=LOGIN_TEXT).pack(pady=(0, 4))

        ctk.CTkLabel(outer,
                     text="✦  Évaluateur d'artefacts  ✦",
                     font=ctk.CTkFont(family="Georgia", size=13),
                     text_color=LOGIN_GOLD).pack(pady=(0, 20))

        # ── Carte de connexion ────────────────────────────────────────────────
        card = ctk.CTkFrame(outer,
                            fg_color=LOGIN_CARD,
                            corner_radius=4,
                            border_width=1,
                            border_color=LOGIN_GOLD)
        card.pack(pady=0)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=35, pady=28)

        # Vérifier si des comptes existent déjà
        accounts = self.all_cookies.get("accounts", {})

        if accounts:
            self._build_returning(inner, accounts)
        else:
            self._build_first_time(inner)

        # ── Ornement inférieur ────────────────────────────────────────────────
        ctk.CTkLabel(outer,
                     text="◈──────────────────────────────◈",
                     font=ctk.CTkFont(family="Georgia", size=13),
                     text_color=LOGIN_GOLD).pack(pady=(12, 4))

        ctk.CTkLabel(outer,
                     text="Non affilié à HoYoverse  •  Données locales uniquement",
                     font=ctk.CTkFont(family="Georgia", size=10),
                     text_color=LOGIN_MUTED).pack()

    def _build_first_time(self, parent):
        """
        Mode premier lancement : pas de compte connu.
        Affiche uniquement le bouton de connexion HoYoLAB.
        """
        ctk.CTkLabel(parent,
                     text="Connectez-vous avec votre compte\nHoYoLAB pour accéder à tous\nvos personnages et artefacts.",
                     font=ctk.CTkFont(family="Georgia", size=13),
                     text_color=LOGIN_MUTED,
                     justify="center").pack(pady=(5, 24))

        self.connect_btn = ctk.CTkButton(
            parent,
            text="Se connecter avec HoYoLAB",
            width=370, height=52,
            fg_color=LOGIN_BTN,
            hover_color="#1a1510",
            text_color=LOGIN_BTN_TXT,
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold"),
            corner_radius=3,
            command=self._do_hoyolab_login
        )
        self.connect_btn.pack(pady=(0, 16))

        ctk.CTkLabel(parent,
                     text="Une fenêtre sécurisée s'ouvrira\npour vous connecter à votre compte.",
                     font=ctk.CTkFont(family="Georgia", size=11),
                     text_color=LOGIN_MUTED,
                     justify="center").pack()

    def _build_returning(self, parent, accounts):
        """
        Mode retour : des comptes existent déjà.
        Affiche UID + serveur pré-remplis + bouton Connexion.
        """
        # Récupérer les infos du compte actif
        active_id  = self.all_cookies.get("active", "")
        active_acc = accounts.get(active_id, {})
        saved_uid  = active_acc.get("uid", "")
        saved_srv  = active_acc.get("server", "os_euro")
        nickname   = active_acc.get("nickname", "")

        # Afficher le nickname si disponible
        if nickname:
            ctk.CTkLabel(parent,
                         text=f"✦  {nickname}",
                         font=ctk.CTkFont(family="Georgia", size=14),
                         text_color=LOGIN_GOLD).pack(pady=(0, 16))

        # ── Champ Serveur ─────────────────────────────────────────────────────
        ctk.CTkLabel(parent,
                     text="* Serveur",
                     width=370,
                     font=ctk.CTkFont(family="Georgia", size=12),
                     text_color=LOGIN_RED,
                     anchor="w").pack(fill="x", pady=(0, 5))

        default_srv = next(
            (lbl for lbl, val in SERVER_LABELS.items() if val == saved_srv), "Europe")
        self.server_var = ctk.StringVar(value=default_srv)

        ctk.CTkComboBox(parent,
                variable=self.server_var,
                values=list(SERVER_LABELS.keys()),
                width=370, height=42,
                fg_color="white",
                border_color=LOGIN_GOLD,
                border_width=1,
                button_color=LOGIN_GOLD,
                button_hover_color="#a08050",
                text_color=LOGIN_TEXT,
                dropdown_fg_color=LOGIN_CARD,
                dropdown_text_color=LOGIN_TEXT,
                dropdown_hover_color="#e8e0d0",
                font=ctk.CTkFont(family="Georgia", size=14),
                corner_radius=3,
                state="readonly").pack(fill="x", pady=(0, 16))

        # ── Champ UID ─────────────────────────────────────────────────────────
        ctk.CTkLabel(parent,
                     text="* UID Genshin",
                     width=370,
                     font=ctk.CTkFont(family="Georgia", size=12),
                     text_color=LOGIN_RED,
                     anchor="w").pack(fill="x", pady=(0, 5))

        self.uid_entry = ctk.CTkEntry(parent,
                                       placeholder_text="Votre UID Genshin",
                                       width=370, height=42,
                                       fg_color="white",
                                       border_color=LOGIN_GOLD,
                                       border_width=1,
                                       text_color=LOGIN_TEXT,
                                       font=ctk.CTkFont(family="Georgia", size=14),
                                       corner_radius=3)
        self.uid_entry.pack(fill="x", pady=(0, 20))

        # Pré-remplir l'UID sauvegardé
        if saved_uid:
            self.uid_entry.insert(0, saved_uid)

        # ── Bouton Connexion principal ─────────────────────────────────────────
        self.main_btn = ctk.CTkButton(
            parent,
            text="Se connecter",
            width=370, height=48,
            fg_color=LOGIN_BTN,
            hover_color="#1a1510",
            text_color=LOGIN_BTN_TXT,
            font=ctk.CTkFont(family="Georgia", size=16, weight="bold"),
            corner_radius=3,
            command=self._do_uid_login
        )
        self.main_btn.pack(fill="x", pady=(0, 14))

        # ── Séparateur ────────────────────────────────────────────────────────
        ctk.CTkLabel(parent,
                     text="── ou ──",
                     font=ctk.CTkFont(family="Georgia", size=11),
                     text_color=LOGIN_MUTED).pack(pady=(0, 12))

        # ── Bouton secondaire : ajouter un compte ─────────────────────────────
        ctk.CTkButton(parent,
                      text="+ Ajouter un compte HoYoLAB",
                      width=370, height=38,
                      fg_color="transparent",
                      hover_color="#e8e0d0",
                      text_color=LOGIN_GOLD,
                      border_width=1,
                      border_color=LOGIN_GOLD,
                      font=ctk.CTkFont(family="Georgia", size=13),
                      corner_radius=3,
                      command=self._do_hoyolab_login).pack(fill="x")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _do_uid_login(self):
        """
        Connexion avec UID existant.
        Appelle le callback on_success avec les cookies actifs + UID + serveur.
        """
        uid    = self.uid_entry.get().strip()
        server = SERVER_LABELS.get(self.server_var.get(), "os_euro")

        if not uid:
            # Mettre la bordure en rouge pour signaler le champ vide
            self.uid_entry.configure(border_color=LOGIN_RED)
            return

        # Récupérer les cookies du compte actif
        active_id = self.all_cookies.get("active", "")
        accounts  = self.all_cookies.get("accounts", {})
        cookies   = accounts.get(active_id, {})

        if not cookies:
            return

        # Appeler le callback
        self.on_success(cookies=cookies, uid=uid, server=server)

    def _do_hoyolab_login(self):
        """
        Connexion via Playwright (nouvelle session HoYoLAB).
        Bloque l'UI pendant que Playwright est ouvert — nécessaire sur Windows.
        Appelle le callback on_success avec les nouveaux cookies.
        """
        from src.auth import login_and_get_cookies

        # Désactiver le bouton et mettre à jour l'UI
        if hasattr(self, "connect_btn"):
            self.connect_btn.configure(text="Connexion en cours...", state="disabled")
        self.window.update()

        cookies = login_and_get_cookies()

        if cookies:
            # Connexion réussie → appeler le callback sans UID ni serveur
            # (l'utilisateur devra entrer son UID après)
            self.on_success(cookies=cookies, uid=None, server="os_euro")
        else:
            # Échec ou timeout → réactiver le bouton
            if hasattr(self, "connect_btn"):
                self.connect_btn.configure(
                    text="Se connecter avec HoYoLAB", state="normal")

    def destroy(self):
        """Détruit tous les widgets de la page de connexion."""
        for widget in self.window.winfo_children():
            widget.destroy()
        # Restaurer le fond sombre
        self.window.configure(fg_color="#1a1a2e")