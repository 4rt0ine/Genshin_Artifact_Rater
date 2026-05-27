# Genshin Artifact Rater

Une application desktop Python qui évalue la qualité de tes artefacts Genshin Impact en les comparant à l'artefact théorique parfait, en récupérant **tous** tes personnages via l'API HoYoLAB.

## Fonctionnalités

- Connexion automatique via une fenêtre HoYoLAB intégrée (Playwright) — pas de copier-coller de cookies
- Récupération de **tous** tes personnages et leurs artefacts (pas seulement la vitrine des 12)
- Affichage des artefacts avec icônes, mainstats nommées et substats détaillées
- Détail des rolls pour chaque substat (ex: `[4, 3, 4]` = qualité de chaque roll)
- Mise à jour automatique des builds recommandés depuis [sephijin.fr](https://sephijin.fr) via OCR
- Cache local des icônes et des builds pour un chargement rapide
- Interface graphique desktop thème doré/sombre inspirée de Genshin Impact

## Prérequis

- Python 3.10+
- Un compte HoYoLAB

## Installation

```bash
git clone https://github.com/ton-pseudo/genshin-artifact-rater
cd genshin-artifact-rater
pip install -r requirements.txt
playwright install chromium
python main.py
```

## Utilisation

### Premier lancement

1. Lance l'application avec `python main.py`
2. Clique sur **Se connecter avec HoYoLAB** — une fenêtre Chromium s'ouvre
3. Connecte-toi sur HoYoLAB normalement dans cette fenêtre
4. La fenêtre se ferme automatiquement une fois la connexion détectée
5. Entre ton **UID Genshin** dans le champ et clique sur **Charger**
6. Navigue entre tes personnages via la barre d'onglets scrollable
7. Consulte les artefacts de chaque personnage avec le détail des rolls

### Lancements suivants

Les cookies sont sauvegardés automatiquement — tu arrives directement sur l'écran principal avec ton UID pré-rempli. Clique simplement sur **Charger**.

### Changer de compte

Clique sur **Changer de compte** dans le header — les cookies sont supprimés et la page de connexion réapparaît.

## Structure du projet

```
genshin-artifact-rater/
├── src/
│   ├── main.py              # Point d'entrée
│   ├── app.py               # Interface graphique CustomTkinter
│   ├── hoyolab.py           # Appels API HoYoLAB
│   ├── scoring.py           # Logique de notation des artefacts
│   └── auth.py              # Authentification via Playwright
├── data/
│   ├── builds.py            # Builds générés automatiquement (ne pas modifier)
│   ├── builds_cache.json    # Cache des builds et hashs d'images (gitignore)
│   └── cookies.json         # Cookies de session (gitignore)
├── assets/                  # Cache local des icônes HoYoLAB (gitignore)
├── tests/
│   ├── test_auth.py         # Test de la connexion HoYoLAB
│   ├── test_hoyolab.py      # Test des appels API
│   └── test_ocr.py          # Test de la reconnaissance OCR
├── update_builds.py         # Mise à jour automatique des builds
├── requirements.txt
├── .gitignore
└── README.md
```

## Système de notation

Chaque substat est notée selon la **qualité de ses rolls** — chaque roll peut tomber sur l'une des 4 valeurs possibles (rang 1 à 4, du minimum au maximum). Le score final d'un artefact est calculé en comparant les rolls obtenus au maximum théorique possible, pondéré par l'importance de chaque substat pour le personnage concerné.

Les weights (pondérations) sont extraits automatiquement depuis les guides de [sephijin.fr](https://sephijin.fr) via reconnaissance optique (OCR). Ils sont mis à jour automatiquement si l'image du guide change.

## Mise à jour des builds

Les builds sont récupérés automatiquement depuis sephijin.fr au chargement. Pour forcer une mise à jour manuelle :

```bash
python update_builds.py
```

Le script vérifie si les images des guides ont changé (via hash MD5) et ne relance l'OCR que si nécessaire.

## Technologies

- [Python](https://python.org)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — interface graphique
- [Playwright](https://playwright.dev/python/) — authentification HoYoLAB
- [API HoYoLAB](https://www.hoyolab.com) — données joueur
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — reconnaissance des builds
- [Pillow](https://python-pillow.org) — affichage des icônes
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) — scraping sephijin.fr

## Crédits

Images des builds : [sephijin.fr](https://sephijin.fr) (@sephijin)