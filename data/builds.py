"""
builds.py — Généré automatiquement par update_builds.py
Source : sephijin.fr (@sephijin)
Ne pas modifier manuellement, relancer update_builds.py à la place.
"""

BUILDS = {
    "Nefer": {
        # Dernière mise à jour : 2026-05-26
        "substats":    "TC/DC > ME RE%",
        "mainstat":    {"Sables du temps": ["Maîtrise"], "Coupe d'Eonothem": ["Maîtrise"], "Diadème de Logos": ["DGT Crit", "Taux Crit", "Maîtrise"]},
        "weights":     {"Taux Crit": 1.0, "DGT Crit": 1.0, "ATQ%": 0.0, "PV%": 0.0, "DEF%": 0.0, "Maîtrise": 0.8, "Recharge": 0.6},
        "image":       "https://sephijin.fr/wp-content/uploads/2025/11/nefer-catalyseur-dendro-guide-synthese-1.webp",
        "last_update": "2026-05-26",
    },
    "Lauma": {
        # Dernière mise à jour : 2026-05-26
        "substats":    "RE% DC ATQ% TC",
        "mainstat":    {"Sables du temps": ["Maîtrise", "Recharge"], "Coupe d'Eonothem": ["Maîtrise"], "Diadème de Logos": ["Maîtrise"]},
        "weights":     {"Taux Crit": 0.4, "DGT Crit": 0.8, "ATQ%": 0.6, "PV%": 0.0, "DEF%": 0.0, "Maîtrise": 0.0, "Recharge": 1.0},
        "image":       "https://sephijin.fr/wp-content/uploads/2025/09/lauma-catalyseur-dendro-guide-synthese.webp",
        "last_update": "2026-05-26",
    },
    "Furina": {
        # Dernière mise à jour : 2026-05-26
        "substats":    "RE% TC/DC PV%",
        "mainstat":    {"Sables du temps": ["Recharge"], "Coupe d'Eonothem": ["Bonus Hydro"], "Diadème de Logos": ["DGT Crit", "Taux Crit"]},
        "weights":     {"Taux Crit": 0.8, "DGT Crit": 0.8, "ATQ%": 0.0, "PV%": 0.6, "DEF%": 0.0, "Maîtrise": 0.0, "Recharge": 1.0},
        "image":       "https://sephijin.fr/wp-content/uploads/2025/03/furina-epee-hydro-guide-synthese-scaled.webp",
        "last_update": "2026-05-26",
    },
    "Mavuika": {
        # Dernière mise à jour : 2026-05-26
        "substats":    "DC/TC > ATQ% ME",
        "mainstat":    {"Sables du temps": ["ATQ%", "Maîtrise"], "Coupe d'Eonothem": ["Bonus Pyro"], "Diadème de Logos": ["DGT Crit", "Taux Crit"]},
        "weights":     {"Taux Crit": 1.0, "DGT Crit": 1.0, "ATQ%": 0.8, "PV%": 0.0, "DEF%": 0.0, "Maîtrise": 0.6, "Recharge": 0.0},
        "image":       "https://sephijin.fr/wp-content/uploads/2025/01/mavuika-claymore-pyro-guide-synthese.webp",
        "last_update": "2026-05-26",
    },
    "Sucrose": {
        # Dernière mise à jour : 2026-05-26
        "substats":    "ME RE%",
        "mainstat":    {"Sables du temps": ["Maîtrise"], "Coupe d'Eonothem": ["Maîtrise"], "Diadème de Logos": ["Maîtrise"]},
        "weights":     {"Taux Crit": 0.0, "DGT Crit": 0.0, "ATQ%": 0.0, "PV%": 0.0, "DEF%": 0.0, "Maîtrise": 1.0, "Recharge": 0.8},
        "image":       "https://sephijin.fr/wp-content/uploads/2023/07/sucrose-catalyseur-anemo-guide-synthese.webp",
        "last_update": "2026-05-26",
    },
    "Aino": {
        # Dernière mise à jour : 2026-05-26
        "substats":    "ME RE% TC (SI FAVO)",
        "mainstat":    {"Sables du temps": ["Maîtrise", "Recharge"], "Coupe d'Eonothem": ["Maîtrise"], "Diadème de Logos": ["Maîtrise", "Taux Crit"]},
        "weights":     {"Taux Crit": 0.6, "DGT Crit": 0.0, "ATQ%": 0.0, "PV%": 0.0, "DEF%": 0.0, "Maîtrise": 1.0, "Recharge": 0.8},
        "image":       "https://sephijin.fr/wp-content/uploads/2026/04/aino-claymore-hydro-guide-synthese.webp",
        "last_update": "2026-05-26",
    },
}

# Weights génériques par rôle — utilisés quand le personnage n'est pas
# référencé dans BUILDS (pas de page sur sephijin.fr ou pas encore parsé)
GENERIC_WEIGHTS = {
    "dps":     {"Taux Crit": 1.0, "DGT Crit": 1.0, "ATQ%": 0.6, "Maîtrise": 0.3},
    "support": {"Recharge":  1.0, "Taux Crit": 0.7, "DGT Crit": 0.7, "PV%": 0.5},
    "healer":  {"Recharge":  1.0, "PV%": 1.0,  "Taux Crit": 0.4, "DGT Crit": 0.4},
}


def get_build(character_name):
    """Retourne le build complet d'un personnage, ou None si non référencé."""
    return BUILDS.get(character_name)


def get_weights(character_name, role='dps'):
    """
    Retourne les weights d'un personnage pour le scoring.
    Si le personnage n'est pas dans BUILDS, retourne des weights génériques
    selon le rôle spécifié (dps, support, healer).
    """
    build = BUILDS.get(character_name)
    if build:
        return build["weights"]
    return GENERIC_WEIGHTS.get(role, GENERIC_WEIGHTS["dps"])