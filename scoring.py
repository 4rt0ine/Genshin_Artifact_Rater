from itertools import combinations_with_replacement

# Valeurs possibles par roll pour chaque substat (artefacts 5★)
SUBSTAT_ROLLS = {
    "PV":       [209.13, 239.00, 268.88, 298.75],
    "ATQ":      [13.62,  15.56,  17.51,  19.45],
    "DEF":      [16.20,  18.52,  20.83,  23.15],
    "PV%":      [4.08,   4.66,   5.25,   5.83],
    "ATQ%":     [4.08,   4.66,   5.25,   5.83],
    "DEF%":     [5.10,   5.83,   6.56,   7.29],
    "Maîtrise": [16.32,  18.65,  20.98,  23.31],
    "Recharge": [4.53,   5.18,   5.83,   6.48],
    "Taux Crit":[2.72,   3.11,   3.50,   3.89],
    "DGT Crit": [5.44,   6.22,   6.99,   7.77],
}

# Correspondance property_type → nom de substat pour le scoring
PROPERTY_TYPE_MAP = {
    2:  "PV",
    3:  "PV%",
    5:  "ATQ",
    6:  "ATQ%",
    8:  "DEF",
    9:  "DEF%",
    20: "Taux Crit",
    22: "DGT Crit",
    23: "Recharge",
    28: "Maîtrise",
}

def get_rolls_detail(property_type, value_str, nb_rolls):
    """
    Retourne le détail des rangs de chaque roll ex : [4, 3, 4]
    """
    stat_name = PROPERTY_TYPE_MAP.get(property_type)
    if not stat_name or nb_rolls == 0:
        return None
    
    value = float(str(value_str).replace("%", ""))
    possible_values = SUBSTAT_ROLLS[stat_name]
    
    for combo in combinations_with_replacement(possible_values, nb_rolls):
        if abs(sum(combo) - value) < 0.15:
            return [possible_values.index(v) + 1 for v in combo]
    
    return None


def get_roll_quality(stat_name, value_str, nb_rolls):
    """
    Pour le scoring : retourne le rang moyen des rolls (1 à 4).
    """
    if not stat_name not in SUBSTAT_ROLLS:
        return 1
    value = float(str(value_str).replace("%", ""))
    value_per_roll = value/nb_rolls
    rolls = SUBSTAT_ROLLS[stat_name]
    # On cherche le rang le plus proche
    closest = min(rolls, key=lambda r: abs(r - value_per_roll))
    return rolls.index(closest) + 1


def score_artifact(artifact, weights):
    """
    Note un artefact de 0 à 100 selon les weights du personnage.
    artifact : dict avec "sub_property_list" (depuis HoYoLAB)
    weights : dict { nom_stat: poids } ex: {"DGT Crit": 1.0, "Taux Crit": 1.0}
    """
    score = 0

    for substat in artifact.get("sub_property_list", []):
        prop_type = substat["property_type"]
        times = substat.get("times", 1)  # nombre de rolls
        
        stat_name = PROPERTY_TYPE_MAP.get(prop_type)
        if not stat_name or stat_name not in weights:
            continue

        # Valeur numérique (on retire le % si présent)
        raw_value = str(substat["value"]).replace("%", "")
        try:
            value = float(raw_value)
        except ValueError:
            continue

        poids = weights[stat_name]
        nb_rolls = max(times, 1)

        # Qualité moyenne des rolls
        roll_quality = get_roll_quality(stat_name, value / nb_rolls) if nb_rolls > 0 else 1
        
        score += (roll_quality / 4) * poids * (nb_rolls / 9)

    # Score max théorique : 9 rolls tous au rang 4 sur les 2 meilleures stats
    sorted_weights = sorted(weights.values(), reverse=True)
    if len(sorted_weights) >= 2:
        score_max = sorted_weights[0] * (5/9) + sorted_weights[1] * (4/9)
    elif len(sorted_weights) == 1:
        score_max = sorted_weights[0]
    else:
        return 0

    if score_max == 0:
        return 0

    return round((score / score_max) * 100, 1)