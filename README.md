# Genshin Artifact Rater

Une application desktop Python qui évalue la qualité de tes artefacts Genshin Impact en les comparant à l'artefact théorique parfait, en récupérant **tous** tes personnages via l'API HoYoLAB.

## Fonctionnalités

- Connexion via les cookies HoYoLAB (accès à tous tes personnages, pas seulement la vitrine)
- Récupération automatique de tous tes personnages et leurs artefacts
- Notation ultra-détaillée : score par substat, qualité de chaque roll, comparaison avec le maximum théorique
- Interface graphique desktop inspirée de l'UI de Genshin Impact (thème doré/sombre)
- Cache local des icônes pour un chargement rapide
- Builds recommandés par personnage

## Prérequis

- Python 3.10+
- Un compte HoYoLAB connecté sur ton navigateur

## Installation

```bash
git clone https://github.com/ton-pseudo/genshin-artifact-rater
cd genshin-artifact-rater
pip install -r requirements.txt
python main.py
```

## Récupérer tes cookies HoYoLAB

1. Connecte-toi sur [hoyolab.com](https://hoyolab.com)
2. Ouvre les outils développeur (F12)
3. Va dans **Application** → **Cookies** → `https://www.hoyolab.com`
4. Copie les valeurs de `ltuid_v2` et `ltoken_v2`
5. Entre-les dans l'application au premier lancement

> ⚠️ Ne partage jamais tes cookies — ils donnent accès à ton compte.

## Structure du projet

```
genshin-artifact-rater/
├── main.py              # Point d'entrée
├── app.py               # Interface graphique CustomTkinter
├── hoyolab.py           # Appels API HoYoLAB
├── scoring.py           # Logique de notation des artefacts
├── data/
│   └── builds.py        # Builds recommandés et poids par personnage
├── assets/              # Cache local des icônes
├── requirements.txt
└── README.md
```

## Utilisation

1. Lance l'application avec `python main.py`
2. Entre ton `ltuid_v2` et `ltoken_v2` au premier lancement (sauvegardés automatiquement)
3. Entre ton UID Genshin et clique sur **Charger**
4. Navigue entre tes personnages via les onglets
5. Consulte le score détaillé de chaque artefact

## Système de notation

Chaque artefact est noté de **0 à 100 %** selon :

- La qualité de chaque roll (rang 1 à 4) rapportée au maximum possible
- La quantité de rolls investis dans les substats utiles (sur 9 rolls au total)
- Le poids de chaque substat pour le personnage sélectionné

## Technologies

- [Python](https://python.org)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — interface graphique
- [API HoYoLAB](https://www.hoyolab.com) — données joueur
- [Pillow](https://python-pillow.org) — affichage des icônes

## Roadmap

- [x] Connexion via cookies HoYoLAB
- [x] Récupération de tous les personnages
- [x] Affichage des artefacts avec icônes
- [ ] Scoring complet avec détail des rolls
- [ ] Builds recommandés par personnage
- [ ] Indicateur de potentiel (+0)
- [ ] Packaging en `.exe` avec PyInstaller