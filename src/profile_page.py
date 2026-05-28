"""
profile_page.py
===============
Page Profil de Genshin Artifact Rater.

Affiche les informations du compte et permet de charger les personnages.
Conçue pour évoluer — on pourra y ajouter l'exploration, les stats, etc.

Utilisation depuis app.py :
    from src.profile_page import ProfilePage
    ProfilePage(
        parent=self.content_area,   # ← zone de contenu, pas self.window
        active_cookies=self.active_cookies,
        on_load=self._on_load_characters
    )

Le callback on_load reçoit (uid, server) au clic sur Charger.
"""

import customtkinter as ctk

# ── Palette DA ────────────────────────────────────────────────────────────────
BG      = "#f0ebe0"
CARD    = "#faf7f2"
GOLD    = "#c8a96e"
GOLD2   = "#a08050"
TEXT    = "#3d3226"
MUTED   = "#9b8e7e"
BTN     = "#2d2520"
BTN_TXT = "#c8a96e"

SERVERS = {
    "EU":  "os_euro",
    "AS":  "os_asia",
    "USA": "os_usa",
    "CHT": "os_cht",
}


class ProfilePage:
    """
    Page profil : nickname, serveur, UID et bouton Charger.

    Extensions futures :
    - Niveau AR et monde
    - Avancement quête principale
    - % exploration par région
    - Statistiques générales
    """

    def __init__(self, parent, active_cookies, on_load):
        """
        parent          : zone de contenu (App.content_area)
        active_cookies  : dict des cookies du compte actif
        on_load         : callback(uid, server) au clic sur Charger
        """
        self.parent         = parent
        self.active_cookies = active_cookies or {}
        self.on_load        = on_load

        self._build()

    def _build(self):
        """Construit la page profil."""

        self.frame = ctk.CTkFrame(self.parent, fg_color=BG)
        self.frame.pack(fill="both", expand=True, padx=40, pady=30)

        # Titre
        ctk.CTkLabel(self.frame,
                     text="◈──────── Profil ────────◈",
                     font=ctk.CTkFont(family="Georgia", size=16),
                     text_color=GOLD).pack(pady=(0, 20))

        # Carte centrale
        card = ctk.CTkFrame(self.frame, fg_color=CARD, corner_radius=6,
                            border_width=1, border_color=GOLD)
        card.pack()

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=40, pady=28)

        # Nickname
        nickname = self.active_cookies.get("nickname", "")
        if nickname:
            ctk.CTkLabel(inner,
                         text=f"✦  {nickname}",
                         font=ctk.CTkFont(family="Georgia", size=20, weight="bold"),
                         text_color=GOLD).pack(pady=(0, 10))

        # UID affiché (non modifiable ici — se change dans la page de connexion)
        uid = self.active_cookies.get("uid", "")
        if uid:
            ctk.CTkLabel(inner,
                         text=f"UID : {uid}",
                         font=ctk.CTkFont(family="Georgia", size=13),
                         text_color=MUTED).pack(pady=(0, 5))

        # Serveur affiché
        saved_srv   = self.active_cookies.get("server", "os_euro")
        server_label = next((lbl for lbl, val in SERVERS.items()
                             if val == saved_srv), "EU")
        ctk.CTkLabel(inner,
                     text=f"Serveur : {server_label}",
                     font=ctk.CTkFont(family="Georgia", size=13),
                     text_color=MUTED).pack(pady=(0, 20))

        # Bouton Charger
        self.load_btn = ctk.CTkButton(inner,
                                       text="Charger mes personnages",
                                       width=280, height=48,
                                       fg_color=BTN,
                                       hover_color="#1a1510",
                                       text_color=BTN_TXT,
                                       font=ctk.CTkFont(family="Georgia",
                                                        size=15, weight="bold"),
                                       corner_radius=3,
                                       command=self._on_load_click)
        self.load_btn.pack()

        # Zone extensions futures (exploration, stats, etc.)
        # TODO : à enrichir au fur et à mesure

    def _on_load_click(self):
        """Appelle le callback on_load avec l'UID et le serveur sauvegardés."""
        uid    = self.active_cookies.get("uid", "").strip()
        server = self.active_cookies.get("server", "os_euro")

        if not uid:
            # Pas d'UID sauvegardé — demander à l'utilisateur
            self._show_uid_input()
            return

        self.set_loading(True)
        self.on_load(uid=uid, server=server)

    def _show_uid_input(self):
        """
        Affiche un champ UID si aucun n'est sauvegardé.
        Cas rare : première connexion sans UID entré.
        """
        if hasattr(self, "_uid_shown"):
            return
        self._uid_shown = True

        inner = self.load_btn.master

        ctk.CTkLabel(inner,
                     text="* UID Genshin requis",
                     font=ctk.CTkFont(family="Georgia", size=12),
                     text_color="#c0392b",
                     anchor="w").pack(fill="x", pady=(10, 4), before=self.load_btn)

        self.uid_entry = ctk.CTkEntry(inner,
                                       placeholder_text="Votre UID Genshin",
                                       width=280, height=42,
                                       fg_color="white",
                                       border_color=GOLD,
                                       border_width=1,
                                       text_color=TEXT,
                                       font=ctk.CTkFont(family="Georgia", size=14),
                                       corner_radius=3)
        self.uid_entry.pack(pady=(0, 10), before=self.load_btn)

        # Remplacer la commande du bouton
        self.load_btn.configure(command=self._on_load_with_uid_input)

    def _on_load_with_uid_input(self):
        """Appelé quand l'utilisateur a dû entrer son UID manuellement."""
        uid    = self.uid_entry.get().strip()
        server = self.active_cookies.get("server", "os_euro")
        if not uid:
            self.uid_entry.configure(border_color="#c0392b")
            return
        self.uid_entry.configure(border_color=GOLD)
        self.set_loading(True)
        self.on_load(uid=uid, server=server)

    def set_loading(self, loading):
        """Active ou désactive l'état de chargement du bouton."""
        if not self.load_btn.winfo_exists():
            return
        if loading:
            self.load_btn.configure(text="Chargement...", state="disabled")
        else:
            self.load_btn.configure(text="Charger mes personnages", state="normal")

    def destroy(self):
        """Détruit la page profil."""
        if hasattr(self, "frame") and self.frame.winfo_exists():
            self.frame.destroy()