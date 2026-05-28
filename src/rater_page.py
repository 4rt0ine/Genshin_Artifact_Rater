"""
rater_page.py
=============
Page "Rater un artefact" de Genshin Artifact Rater.
Permet d'évaluer manuellement n'importe quel artefact pour n'importe quel
personnage du jeu, même ceux que l'utilisateur ne possède pas encore.

Flux :
    1. L'utilisateur sélectionne un personnage (liste complète du jeu)
    2. Il choisit le slot de l'artefact (Fleur, Plume, Sables, Coupe, Diadème)
    3. Il entre jusqu'à 4 substats avec leur valeur et nombre de rolls
    4. Le score est calculé en temps réel selon les weights du build
    5. Le détail des rolls est affiché pour chaque substat

Ce module est conçu pour être instancié depuis app.py via _open_rater_page().
"""

import customtkinter as ctk
from .hoyolab import get_all_game_characters, get_icon
from .scoring import score_artifact, get_rolls_detail, PROPERTY_TYPE_MAP

# ── Constantes visuelles (identiques à app.py) ────────────────────────────────
GOLD  = "#c8a96e"
BEIGE = "#f0e6d3"
DARK  = "#1a1a2e"
DARK2 = "#0d0d1a"

# ── Slots d'artefacts disponibles ────────────────────────────────────────────
SLOTS = [
    "Fleur de la vie",
    "Plume de la mort",
    "Sables du temps",
    "Coupe d'Eonothem",
    "Diadème de Logos",
]

# ── Substats disponibles ──────────────────────────────────────────────────────
# Correspond aux clés de SUBSTAT_ROLLS dans scoring.py
SUBSTATS = [
    "Taux Crit",
    "DGT Crit",
    "ATQ%",
    "PV%",
    "DEF%",
    "Maîtrise",
    "Recharge",
    "ATQ",
    "PV",
    "DEF",
]

# Nombre maximum de substats sur un artefact 5★
MAX_SUBSTATS = 4


class RaterPage(ctk.CTkToplevel):
    """
    Fenêtre popup pour rater un artefact manuellement.
    Hérite de CTkToplevel pour s'afficher au-dessus de la fenêtre principale.
    """

    def __init__(self, parent, cookies=None):
        """
        parent  : fenêtre parente (App.window)
        cookies : cookies HoYoLAB pour récupérer la liste des persos du wiki
        """
        super().__init__(parent)

        self.title("Rater un artefact")
        self.geometry("700x650")
        self.configure(fg_color=DARK)
        self.resizable(False, False)

        # Garder la fenêtre au-dessus de la principale
        self.transient(parent)
        self.grab_set()

        self.cookies = cookies

        # Liste de tous les persos du jeu (chargée en arrière-plan)
        self.all_characters = []
        self.filtered_characters = []

        # Widgets des substats (liste de dicts {stat, value, times})
        self.substat_rows = []

        self._build_ui()
        self._load_characters()

    # ── Construction de l'UI ──────────────────────────────────────────────────

    def _build_ui(self):
        """Construit tous les éléments de l'interface."""

        # ── Titre ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(self,
                     text="✦ Rater un artefact ✦",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=GOLD).pack(pady=(20, 5))

        ctk.CTkLabel(self,
                     text="Évalue n'importe quel artefact pour n'importe quel personnage",
                     font=ctk.CTkFont(size=12),
                     text_color="#888888").pack(pady=(0, 15))

        # ── Section personnage + slot ─────────────────────────────────────────
        config_frame = ctk.CTkFrame(self, fg_color=DARK2, corner_radius=8)
        config_frame.pack(fill="x", padx=20, pady=(0, 10))

        inner = ctk.CTkFrame(config_frame, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=12)

        # Recherche de personnage
        ctk.CTkLabel(inner, text="Personnage :",
                     text_color=BEIGE,
                     font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        self.search_entry = ctk.CTkEntry(inner,
                                         textvariable=self.search_var,
                                         placeholder_text="Rechercher...",
                                         width=180, height=34,
                                         fg_color="#2a2a3e",
                                         border_color=GOLD,
                                         text_color=BEIGE)
        self.search_entry.grid(row=0, column=1, padx=(0, 8))

        # Dropdown personnage
        self.character_var = ctk.StringVar(value="Sélectionner...")
        self.character_menu = ctk.CTkOptionMenu(inner,
                                                 variable=self.character_var,
                                                 values=["Chargement..."],
                                                 width=180, height=34,
                                                 fg_color="#2a2a3e",
                                                 button_color=GOLD,
                                                 button_hover_color="#a08050",
                                                 text_color=BEIGE,
                                                 command=self._on_character_change)
        self.character_menu.grid(row=0, column=2, padx=(0, 20))

        # Slot de l'artefact
        ctk.CTkLabel(inner, text="Slot :",
                     text_color=BEIGE,
                     font=ctk.CTkFont(size=13)).grid(row=0, column=3, sticky="w", padx=(0, 10))

        self.slot_var = ctk.StringVar(value=SLOTS[0])
        ctk.CTkOptionMenu(inner,
                          variable=self.slot_var,
                          values=SLOTS,
                          width=180, height=34,
                          fg_color="#2a2a3e",
                          button_color=GOLD,
                          button_hover_color="#a08050",
                          text_color=BEIGE).grid(row=0, column=4)

        # ── Section substats ──────────────────────────────────────────────────
        substats_label_frame = ctk.CTkFrame(self, fg_color="transparent")
        substats_label_frame.pack(fill="x", padx=20, pady=(5, 0))

        ctk.CTkLabel(substats_label_frame, text="Substats",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=GOLD).pack(side="left")

        ctk.CTkLabel(substats_label_frame,
                     text="Stat",
                     font=ctk.CTkFont(size=11),
                     text_color="#888888",
                     width=180).pack(side="left", padx=(60, 0))

        ctk.CTkLabel(substats_label_frame,
                     text="Valeur",
                     font=ctk.CTkFont(size=11),
                     text_color="#888888",
                     width=90).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(substats_label_frame,
                     text="Rolls",
                     font=ctk.CTkFont(size=11),
                     text_color="#888888",
                     width=60).pack(side="left", padx=(10, 0))

        # Conteneur des lignes de substats
        self.substats_frame = ctk.CTkFrame(self, fg_color=DARK2, corner_radius=8)
        self.substats_frame.pack(fill="x", padx=20, pady=(5, 0))

        # Ajouter 4 lignes de substats par défaut
        for _ in range(MAX_SUBSTATS):
            self._add_substat_row()

        # ── Bouton calculer ───────────────────────────────────────────────────
        ctk.CTkButton(self,
                      text="Calculer le score",
                      width=200, height=40,
                      fg_color=GOLD, text_color=DARK,
                      hover_color="#a08050",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._calculate_score).pack(pady=15)

        # ── Zone de résultat ──────────────────────────────────────────────────
        self.result_frame = ctk.CTkFrame(self, fg_color=DARK2, corner_radius=8)
        self.result_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.score_label = ctk.CTkLabel(self.result_frame,
                                         text="Entrez les substats et cliquez sur Calculer",
                                         font=ctk.CTkFont(size=13),
                                         text_color="#888888")
        self.score_label.pack(pady=15)

    def _add_substat_row(self):
        """
        Ajoute une ligne de saisie pour une substat.
        Chaque ligne contient : dropdown stat, champ valeur, champ rolls.
        """
        row_frame = ctk.CTkFrame(self.substats_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=10, pady=5)

        # Index de la ligne pour le label
        idx = len(self.substat_rows) + 1
        ctk.CTkLabel(row_frame, text=f"{idx}.",
                     text_color=BEIGE,
                     font=ctk.CTkFont(size=13),
                     width=20).pack(side="left", padx=(5, 5))

        # Dropdown de la stat
        stat_var = ctk.StringVar(value=SUBSTATS[0])
        stat_menu = ctk.CTkOptionMenu(row_frame,
                                       variable=stat_var,
                                       values=SUBSTATS,
                                       width=180, height=32,
                                       fg_color="#2a2a3e",
                                       button_color="#3a3a5e",
                                       button_hover_color=GOLD,
                                       text_color=BEIGE)
        stat_menu.pack(side="left", padx=(0, 8))

        # Champ valeur (ex: "9.7%" ou "311")
        value_var = ctk.StringVar()
        value_entry = ctk.CTkEntry(row_frame,
                                    textvariable=value_var,
                                    placeholder_text="Valeur",
                                    width=90, height=32,
                                    fg_color="#2a2a3e",
                                    border_color="#3a3a5e",
                                    text_color=BEIGE)
        value_entry.pack(side="left", padx=(0, 8))

        # Champ nombre de rolls (1 à 9)
        times_var = ctk.StringVar(value="1")
        times_entry = ctk.CTkEntry(row_frame,
                                    textvariable=times_var,
                                    placeholder_text="Rolls",
                                    width=60, height=32,
                                    fg_color="#2a2a3e",
                                    border_color="#3a3a5e",
                                    text_color=BEIGE)
        times_entry.pack(side="left", padx=(0, 8))

        # Label détail des rolls (affiché après calcul)
        detail_label = ctk.CTkLabel(row_frame,
                                     text="",
                                     font=ctk.CTkFont(size=11),
                                     text_color=GOLD)
        detail_label.pack(side="left")

        self.substat_rows.append({
            "stat":   stat_var,
            "value":  value_var,
            "times":  times_var,
            "detail": detail_label,
        })

    # ── Chargement des personnages ────────────────────────────────────────────

    def _load_characters(self):
        """
        Charge la liste de tous les persos du jeu depuis le wiki HoYoLAB.
        Tourne dans un thread séparé pour ne pas bloquer l'UI.
        """
        import threading

        def fetch():
            try:
                self.all_characters = get_all_game_characters(cookies=self.cookies)
                names = [c["name"] for c in self.all_characters]
                self.filtered_characters = names
                # Mettre à jour le dropdown dans le thread principal
                self.after(0, lambda: self.character_menu.configure(values=names))
                self.after(0, lambda: self.character_var.set(names[0] if names else ""))
            except Exception as e:
                print(f"Erreur chargement persos wiki : {e}")
                self.after(0, lambda: self.character_menu.configure(
                    values=["Erreur de chargement"]))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_search_change(self, *args):
        """
        Filtre la liste des personnages selon la recherche en temps réel.
        Met à jour le dropdown avec les noms correspondants.
        """
        query = self.search_var.get().lower()
        all_names = [c["name"] for c in self.all_characters]

        if not query:
            filtered = all_names
        else:
            filtered = [n for n in all_names if query in n.lower()]

        self.filtered_characters = filtered

        if filtered:
            self.character_menu.configure(values=filtered)
            self.character_var.set(filtered[0])
        else:
            self.character_menu.configure(values=["Aucun résultat"])
            self.character_var.set("Aucun résultat")

    def _on_character_change(self, selected):
        """
        Appelé quand l'utilisateur sélectionne un personnage.
        Pourrait être utilisé pour afficher le build recommandé.
        """
        pass  # Extension future : afficher les weights du build

    # ── Calcul du score ───────────────────────────────────────────────────────

    def _calculate_score(self):
        """
        Calcule le score de l'artefact saisi et affiche le résultat.
        Construit un dict compatible avec score_artifact() depuis scoring.py.
        """
        character_name = self.character_var.get()

        # Récupérer les weights du build depuis builds.py
        try:
            from data.builds import get_weights
            weights = get_weights(character_name)
        except Exception:
            # Fallback sur des weights génériques DPS
            weights = {
                "Taux Crit": 1.0,
                "DGT Crit":  1.0,
                "ATQ%":      0.6,
                "Maîtrise":  0.3,
            }

        # Construire la liste des substats depuis les champs de saisie
        # On utilise le nom de stat directement (pas de property_type)
        sub_property_list = []
        for row in self.substat_rows:
            stat_name = row["stat"].get()
            value_str = row["value"].get().strip()
            times_str = row["times"].get().strip()

            # Ignorer les lignes vides
            if not value_str:
                row["detail"].configure(text="")
                continue

            try:
                times = int(times_str) if times_str else 1
                times = max(1, min(times, 9))  # Clamp entre 1 et 9
            except ValueError:
                times = 1

            sub_property_list.append({
                "stat_name": stat_name,  # On utilisera le nom directement
                "value":     value_str,
                "times":     times,
            })

            # Calculer et afficher le détail des rolls
            # On mappe le nom de stat vers le property_type pour get_rolls_detail
            prop_type = self._stat_name_to_prop_type(stat_name)
            if prop_type is not None:
                detail = get_rolls_detail(prop_type, value_str, times)
                detail_str = f"→ {detail}" if detail else ""
            else:
                detail_str = ""
            row["detail"].configure(text=detail_str)

        if not sub_property_list:
            self._show_result(None, "Aucune substat saisie")
            return

        # Calculer le score
        # On adapte le format pour score_artifact qui attend property_type
        # On crée un artefact "virtuel" avec les noms de stats
        score = self._compute_score(sub_property_list, weights)
        self._show_result(score, character_name)

    def _stat_name_to_prop_type(self, stat_name):
        """
        Convertit un nom de stat (ex: "Taux Crit") en property_type (ex: 20).
        Inverse de PROPERTY_TYPE_MAP dans scoring.py.
        """
        # PROPERTY_TYPE_MAP : {int → str}, on l'inverse
        inverse = {v: k for k, v in PROPERTY_TYPE_MAP.items()}
        return inverse.get(stat_name)

    def _compute_score(self, substats, weights):
        """
        Calcule le score de l'artefact sur 100.
        On utilise directement les noms de stats au lieu des property_type.

        substats : liste de {"stat_name", "value", "times"}
        weights  : dict {nom_stat: poids}
        """
        from src.scoring import SUBSTAT_ROLLS, PRIORITY_WEIGHTS

        score = 0.0

        for sub in substats:
            stat_name = sub["stat_name"]
            value_str = sub["value"]
            times     = sub["times"]

            if stat_name not in weights or stat_name not in SUBSTAT_ROLLS:
                continue

            # Nettoyer la valeur
            try:
                value = float(value_str.replace("%", "").replace(",", "."))
            except ValueError:
                continue

            poids      = weights[stat_name]
            nb_rolls   = max(times, 1)
            value_per_roll = value / nb_rolls

            # Trouver le rang moyen des rolls
            rolls = SUBSTAT_ROLLS[stat_name]
            closest = min(rolls, key=lambda r: abs(r - value_per_roll))
            rank = rolls.index(closest) + 1

            score += (rank / 4) * poids * (nb_rolls / 9)

        # Score max théorique
        sorted_weights = sorted(weights.values(), reverse=True)
        if len(sorted_weights) >= 2:
            score_max = sorted_weights[0] * (5 / 9) + sorted_weights[1] * (4 / 9)
        elif len(sorted_weights) == 1:
            score_max = sorted_weights[0]
        else:
            return 0.0

        if score_max == 0:
            return 0.0

        return round((score / score_max) * 100, 1)

    def _show_result(self, score, character_name):
        """
        Affiche le score dans la zone de résultat avec une couleur adaptée :
        - Rouge   < 40%
        - Orange  40-70%
        - Vert    > 70%
        """
        # Vider la zone de résultat
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        if score is None:
            ctk.CTkLabel(self.result_frame,
                         text=character_name,
                         font=ctk.CTkFont(size=13),
                         text_color="#888888").pack(pady=15)
            return

        # Couleur selon le score
        if score >= 70:
            color = "#4ade80"   # Vert
            quality = "Excellent"
        elif score >= 40:
            color = "#fb923c"   # Orange
            quality = "Correct"
        else:
            color = "#f87171"   # Rouge
            quality = "Médiocre"

        # Score principal
        ctk.CTkLabel(self.result_frame,
                     text=f"Score pour {character_name}",
                     font=ctk.CTkFont(size=12),
                     text_color=BEIGE).pack(pady=(12, 2))

        ctk.CTkLabel(self.result_frame,
                     text=f"{score} %  —  {quality}",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=color).pack(pady=(0, 5))

        # Barre de progression
        progress = ctk.CTkProgressBar(self.result_frame,
                                       width=400, height=14,
                                       corner_radius=7,
                                       fg_color="#2a2a3e",
                                       progress_color=color)
        progress.set(score / 100)
        progress.pack(pady=(0, 12))