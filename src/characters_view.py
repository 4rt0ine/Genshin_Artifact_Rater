"""
characters_view.py
==================
Affichage des personnages et de leurs artefacts.

Gère :
    - La barre d'onglets scrollable avec icônes carrées + noms
    - Scroll horizontal : glisser-déposer (scan_mark/dragto) + Shift+molette
    - Les 5 slots d'artefacts toujours affichés (vides si non équipés)
    - Icônes placeholder générées avec Pillow pour les slots vides
    - Portrait du personnage en arrière-plan avec dégradé élémentaire
    - Cartes compactes qui remplissent uniformément l'espace vertical
"""

import threading
import os
from PIL import Image, ImageDraw, ImageFont
import customtkinter as ctk
from src.hoyolab import get_icon
from src.scoring import get_rolls_detail

# ── Palette DA ────────────────────────────────────────────────────────────────
BG    = "#f0ebe0"
CARD  = "#faf7f2"
CARD2 = "#f0e8d8"
GOLD  = "#c8a96e"
TEXT  = "#3d3226"
MUTED = "#9b8e7e"

# ── Couleurs élémentaires Genshin ─────────────────────────────────────────────
ELEMENT_COLORS = {
    "Anemo":   (78,  203, 158),
    "Hydro":   (28,  114, 253),
    "Pyro":    (239, 123,  48),
    "Electro": (176, 111, 228),
    "Cryo":    (152, 217, 224),
    "Geo":     (207, 163,  42),
    "Dendro":  (123, 180,  45),
}
BG_RGB = (240, 235, 224)

# ── Slots d'artefacts ─────────────────────────────────────────────────────────
# pos → (nom_fr, lettre_placeholder)
SLOTS = {
    1: ("Fleur de la vie",    "F"),
    2: ("Plume de la mort",   "P"),
    3: ("Sables du temps",    "S"),
    4: ("Coupe d'Eonothem",   "C"),
    5: ("Diadème de Logos",   "D"),
}


class CharactersView:
    """Vue principale des personnages et artefacts."""

    def __init__(self, parent, characters, property_map):
        self.parent             = parent
        self.characters         = characters
        self.property_map       = property_map
        self.tab_buttons        = []
        self._active_idx        = 0
        self._placeholder_icons = {}

        self._build()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self):
        """Construit la barre d'onglets et la zone d'artefacts."""

        # ── Barre d'onglets ───────────────────────────────────────────────────
        tab_bar = ctk.CTkFrame(self.parent, fg_color=CARD2,
                               height=130, corner_radius=0)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)

        ctk.CTkFrame(tab_bar, fg_color=GOLD, height=1,
                     corner_radius=0).pack(fill="x", side="bottom")

        self.tab_scroll = ctk.CTkScrollableFrame(
            tab_bar, orientation="horizontal",
            fg_color=CARD2, height=115)
        self.tab_scroll.pack(fill="x", expand=True, padx=5, pady=5)

        # ── Scroll horizontal ─────────────────────────────────────────────────
        canvas = self.tab_scroll._parent_canvas

        # Glisser-déposer avec scan_mark/scan_dragto — méthode native Tkinter,
        # plus fluide que calculer le delta manuellement
        canvas.bind("<ButtonPress-1>", lambda e: canvas.scan_mark(e.x, e.y))
        canvas.bind("<B1-Motion>",     lambda e: canvas.scan_dragto(e.x, e.y, gain=5))

        # Molette normale → scroll horizontal (utile quand la souris est sur l'onglet)
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.xview_scroll(int(-e.delta / 10), "units"))

        # Shift+molette → scroll horizontal uniquement si la souris est
        # dans la zone de la barre d'onglets (y < 190px depuis le haut de la fenêtre)
        # 60px (header) + 130px (tab_bar) = 190px
        def on_shift_scroll(e):
            root = self.parent.winfo_toplevel()
            y    = root.winfo_pointery() - root.winfo_rooty()
            if y <= 190:
                canvas.xview_scroll(int(-e.delta / 10), "units")

        self.parent.winfo_toplevel().bind(
            "<Shift-MouseWheel>", on_shift_scroll, add="+"
        )

        # Linux/Mac
        canvas.bind("<Button-4>", lambda e: canvas.xview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e: canvas.xview_scroll(1,  "units"))

        # ── Zone d'artefacts ──────────────────────────────────────────────────
        self.artifacts_frame = ctk.CTkFrame(self.parent, fg_color=BG,
                                             corner_radius=0)
        self.artifacts_frame.pack(fill="both", expand=True)

        # ── Onglets ───────────────────────────────────────────────────────────
        for i, character in enumerate(self.characters):
            self._build_tab(i, character)

        if self.characters:
            self.show_character(0)

        threading.Thread(target=self._update_tab_icons, daemon=True).start()

    def _build_tab(self, idx, character):
        """Onglet cliquable avec icône carrée + nom avec wraplength."""
        frame = ctk.CTkFrame(self.tab_scroll, fg_color="transparent",
                              cursor="hand2", corner_radius=4)
        frame.pack(side="left", padx=4, pady=3)

        ctk_img   = self._load_icon_cached(character["icon"], size=64)
        img_label = ctk.CTkLabel(frame, image=ctk_img, text="",
                                  fg_color="transparent", cursor="hand2",
                                  width=64, height=64)
        img_label.pack(pady=(4, 2))

        name_label = ctk.CTkLabel(frame,
                                   text=character["name"],
                                   font=ctk.CTkFont(family="Georgia", size=13),
                                   text_color=TEXT,
                                   fg_color="transparent",
                                   wraplength=80,
                                   justify="center",
                                   cursor="hand2")
        name_label.pack(pady=(0, 4))

        for widget in [frame, img_label, name_label]:
            widget.bind("<Button-1>",
                        lambda e, i=idx: self._on_tab_click(i))
            widget.bind("<Enter>",
                        lambda e, f=frame, i=idx: self._on_tab_enter(f, i))
            widget.bind("<Leave>",
                        lambda e, f=frame, i=idx: self._on_tab_leave(f, i))

        self.tab_buttons.append((frame, img_label, name_label))

    # ── Gestion des onglets ───────────────────────────────────────────────────

    def _on_tab_click(self, idx):
        self.show_character(idx)

    def _on_tab_enter(self, frame, idx):
        if idx != self._active_idx:
            frame.configure(fg_color="#e8e0d0")

    def _on_tab_leave(self, frame, idx):
        if idx != self._active_idx:
            frame.configure(fg_color="transparent")

    def show_character(self, idx):
        """Affiche les 5 slots d'artefacts du personnage sélectionné."""
        self._active_idx = idx

        for i, (frame, img_lbl, name_lbl) in enumerate(self.tab_buttons):
            if i == idx:
                frame.configure(fg_color=GOLD)
                name_lbl.configure(text_color="white")
            else:
                frame.configure(fg_color="transparent")
                name_lbl.configure(text_color=TEXT)

        for widget in self.artifacts_frame.winfo_children():
            widget.destroy()

        character = self.characters[idx]

        # Conteneur principal
        container = ctk.CTkFrame(self.artifacts_frame, fg_color=BG, corner_radius=0)
        container.pack(fill="both", expand=True)

        # Zone des cartes d'artefacts
        # padx à droite laisse de la place au portrait sans que les cartes débordent
        relics_frame = ctk.CTkFrame(container, fg_color="transparent", corner_radius=0)
        relics_frame.pack(fill="both", expand=True, padx=15, pady=8)
        
        # Canvas pour le portrait en arrière-plan (premier plan temporaire)
        self.canvas = ctk.CTkCanvas(container, highlightthickness=0, bg=BG)
        self.canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        # self.canvas._canvas.tkraise()

        # Dict pos → relic pour accès rapide
        relic_by_pos = {r["pos"]: r for r in character["relics"]}

        # 5 slots dans l'ordre, expand=True pour remplir uniformément
        for pos, (slot_name, letter) in SLOTS.items():
            relic = relic_by_pos.get(pos)
            self._build_relic_card(relics_frame, relic, pos, slot_name, letter)

        # Portrait en arrière-plan
        element = character.get("element", "")
        threading.Thread(
            target=self._load_portrait_background,
            args=(character["image"], element),
            daemon=True
        ).start()

    # ── Icônes placeholder ────────────────────────────────────────────────────

    def _make_placeholder_icon(self, pos, size=48):
        """
        Génère une icône placeholder Pillow pour un slot vide.
        Fond beige, cercle doré, lettre ASCII centrée.
        Mis en cache pour éviter la régénération à chaque changement d'onglet.
        """
        if pos in self._placeholder_icons:
            return self._placeholder_icons[pos]

        letter = SLOTS[pos][1]

        img  = Image.new("RGB", (size, size), BG_RGB)
        draw = ImageDraw.Draw(img)

        margin = 4
        draw.ellipse([margin, margin, size - margin, size - margin],
                     outline=(200, 169, 110), width=2,
                     fill=(250, 247, 242))

        font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), letter, font=font)
        tw   = bbox[2] - bbox[0]
        th   = bbox[3] - bbox[1]
        draw.text(((size - tw) // 2, (size - th) // 2),
                  letter, fill=(200, 169, 110), font=font)

        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        self._placeholder_icons[pos] = ctk_img
        return ctk_img

    # ── Gestion des icônes ────────────────────────────────────────────────────

    def _load_icon_cached(self, url, size=64):
        """Charge une icône depuis le cache local si disponible."""
        try:
            filename   = url.split("/")[-1]
            cache_path = f"assets/{filename}"
            if os.path.exists(cache_path):
                pil_img = Image.open(cache_path).resize((size, size), Image.LANCZOS)
                return ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                    size=(size, size))
        except Exception:
            pass
        return None

    def _update_tab_icons(self):
        """Télécharge et met à jour les icônes des onglets en arrière-plan."""
        for i, character in enumerate(self.characters):
            try:
                pil_img = get_icon(character["icon"]).resize((64, 64), Image.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                       size=(64, 64))
                if i < len(self.tab_buttons):
                    _, img_lbl, _ = self.tab_buttons[i]
                    self.parent.after(
                        0, lambda lbl=img_lbl, img=ctk_img: lbl.configure(
                            image=img, width=64, height=64))
            except Exception:
                pass

    # ── Portrait en arrière-plan ──────────────────────────────────────────────

    def _load_portrait_background(self, image_url, element):
        """
        Charge le portrait, applique le dégradé élémentaire
        et l'affiche sur le canvas à droite en arrière-plan.
        """
        try:
            pil_img = get_icon(image_url).convert("RGBA")

            self.parent.update_idletasks()
            zone_h = self.artifacts_frame.winfo_height()
            zone_w = self.artifacts_frame.winfo_width()

            if zone_h < 10 or zone_w < 10:
                return

            w, h    = pil_img.size
            ratio   = zone_h / h
            new_w   = int(w * ratio)
            new_h   = zone_h
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

            # Masque de fondu horizontal
            mask      = Image.new("L", (new_w, new_h), 0)
            draw_mask = ImageDraw.Draw(mask)
            fade_w    = int(new_w * 0.5)
            for x in range(new_w):
                alpha = int((x / fade_w) * 220) if x < fade_w else 220
                draw_mask.line([(x, 0), (x, new_h)], fill=min(alpha, 220))
            pil_img.putalpha(mask)

            # Dégradé élémentaire
            elem_color  = ELEMENT_COLORS.get(element, (200, 180, 150))
            bg          = Image.new("RGBA", (new_w, new_h), BG_RGB + (255,))
            color_layer = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
            color_draw  = ImageDraw.Draw(color_layer)
            for x in range(new_w):
                t     = x / new_w
                r     = int(BG_RGB[0] * (1 - t) + elem_color[0] * t)
                g     = int(BG_RGB[1] * (1 - t) + elem_color[1] * t)
                b     = int(BG_RGB[2] * (1 - t) + elem_color[2] * t)
                color_draw.line([(x, 0), (x, new_h)], fill=(r, g, b, int(t * 80)))

            result  = Image.alpha_composite(bg, color_layer)
            result  = Image.alpha_composite(result, pil_img)
            result  = result.convert("RGB")
            x_pos   = zone_w - new_w
            ctk_img = ctk.CTkImage(light_image=result, dark_image=result,
                                    size=(new_w, new_h))

            def place_on_canvas(img=ctk_img, x=x_pos):
                try:
                    if hasattr(self, "canvas") and self.canvas.winfo_exists():
                        lbl = ctk.CTkLabel(self.canvas, image=img, text="",
                                           fg_color="transparent")
                        lbl.place(x=x, y=0)
                        self._portrait_label = lbl
                        self._portrait_img   = img
                except Exception:
                    pass

            self.parent.after(0, place_on_canvas)

        except Exception as e:
            print(f"Portrait background erreur : {e}")

    # ── Cartes d'artefacts ────────────────────────────────────────────────────

    def _build_relic_card(self, parent, relic, pos, slot_name, letter):
        """
        Carte compacte pour un slot d'artefact.
        Vide → placeholder + "Aucun artefact équipé"
        Équipé → icône + mainstat + substats sur 2 colonnes
        expand=True pour répartir uniformément les 5 cartes.
        """
        is_empty = relic is None

        card = ctk.CTkFrame(parent,
                            fg_color="transparent",
                            corner_radius=6,
                            border_width=1,
                            border_color=GOLD if not is_empty else "#d4c4a0")
        card.pack(fill="both", expand=True, pady=3)

        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="x", padx=10, pady=8)

        # Icône
        if is_empty:
            ctk_img = self._make_placeholder_icon(pos, size=48)
        else:
            ctk_img = None
            try:
                pil_img = get_icon(relic["icon"]).resize((48, 48), Image.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                       size=(48, 48))
            except Exception:
                ctk_img = self._make_placeholder_icon(pos, size=48)

        ctk.CTkLabel(card_inner, image=ctk_img, text="",
                     fg_color="transparent").pack(side="left", padx=(0, 10))

        info = ctk.CTkFrame(card_inner, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)

        if is_empty:
            ctk.CTkLabel(info, text=slot_name,
                         text_color=GOLD, fg_color="transparent",
                         font=ctk.CTkFont(family="Georgia", size=14, weight="bold"),
                         anchor="w").pack(fill="x")
            ctk.CTkFrame(info, fg_color="#d4c4a0", height=1,
                         corner_radius=0).pack(fill="x", pady=(2, 4))
            ctk.CTkLabel(info, text="Aucun artefact équipé",
                         text_color="#b0a090", fg_color="transparent",
                         font=ctk.CTkFont(family="Georgia", size=13),
                         anchor="w").pack(fill="x")
        else:
            # Mainstat
            main      = relic.get("main_property") or {}
            main_type = str(main.get("property_type", "?"))
            main_name = self.property_map.get(main_type, {}).get("name", main_type)
            main_val  = main.get("value", "?")

            ctk.CTkLabel(info,
                         text=f"{relic['pos_name']}  —  {relic['name']}  |  {main_name} : {main_val}",
                         text_color=GOLD, fg_color="transparent",
                         font=ctk.CTkFont(family="Georgia", size=15, weight="bold"),
                         anchor="w").pack(fill="x")

            ctk.CTkFrame(info, fg_color=GOLD, height=1,
                         corner_radius=0).pack(fill="x", pady=(2, 3))

            # Substats sur 2 colonnes
            subs = relic.get("sub_property_list", [])
            if subs:
                sub_frame = ctk.CTkFrame(info, fg_color="transparent")
                sub_frame.pack(fill="x")

                col1 = ctk.CTkFrame(sub_frame, fg_color="transparent")
                col1.pack(side="left", fill="x", expand=True)
                col2 = ctk.CTkFrame(sub_frame, fg_color="transparent")
                col2.pack(side="left", fill="x", expand=True)

                for j, sub in enumerate(subs):
                    prop_type     = sub.get("property_type", "?")
                    stat_name     = self.property_map.get(
                        str(prop_type), {}).get("name", str(prop_type))
                    times         = sub.get("times", 0)
                    prop_type_int = int(prop_type) if str(prop_type).isdigit() else prop_type
                    detail        = get_rolls_detail(prop_type_int, sub["value"], times)
                    detail_str    = f" {detail}" if detail else ""

                    col = col1 if j % 2 == 0 else col2
                    ctk.CTkLabel(col,
                                 text=f"• {stat_name} : {sub['value']}{detail_str}",
                                 text_color=MUTED, fg_color="transparent",
                                 font=ctk.CTkFont(family="Georgia", size=13, weight="bold"),
                                 anchor="w").pack(fill="x", pady=1)