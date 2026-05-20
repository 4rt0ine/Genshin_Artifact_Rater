# Builds recommandés par personnage
# weights : importance de chaque substat pour le scoring (0.0 à 1.0)
# mainstat : mainstats recommandées par slot

BUILDS = {
    "Furina": {
        "sets": ["Troupe Dorée (4pc)", "2 Troupe Dorée / 2 PV%"],
        "mainstat": {
            "Sables du temps":    ["PV%", "Recharge"],
            "Coupe d'Eonothem":   ["Bonus Hydro", "PV%"],
            "Diadème de Logos":   ["Taux Crit", "DGT Crit"],
        },
        "weights": {
            "Recharge":   1.0,
            "Taux Crit":  1.0,
            "DGT Crit":   1.0,
            "PV%":        0.8,
        },
    },
    "Nahida": {
        "sets": ["Souvenirs de Serenitea (4pc)", "2 Maîtrise / 2 Maîtrise"],
        "mainstat": {
            "Sables du temps":    ["Maîtrise"],
            "Coupe d'Eonothem":   ["Maîtrise", "Bonus Dendro"],
            "Diadème de Logos":   ["Maîtrise", "Taux Crit", "DGT Crit"],
        },
        "weights": {
            "Maîtrise":   1.0,
            "Taux Crit":  0.5,
            "DGT Crit":   0.5,
            "Recharge":   0.3,
        },
    },
    "Neuvillette": {
        "sets": ["Maréchaussée Fantôme (4pc)"],
        "mainstat": {
            "Sables du temps":    ["PV%"],
            "Coupe d'Eonothem":   ["Bonus Hydro"],
            "Diadème de Logos":   ["Taux Crit", "DGT Crit"],
        },
        "weights": {
            "Taux Crit":  1.0,
            "DGT Crit":   1.0,
            "PV%":        0.8,
            "Recharge":   0.3,
        },
    },
}


def get_weights(character_name):
    """Retourne les weights d'un personnage, ou des weights génériques."""
    if character_name in BUILDS:
        return BUILDS[character_name]["weights"]
    # Weights génériques DPS si le perso n'est pas dans la liste
    return {
        "Taux Crit": 1.0,
        "DGT Crit":  1.0,
        "ATQ%":      0.5,
        "Recharge":  0.3,
    }