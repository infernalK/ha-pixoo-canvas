# ha-pixoo-canvas

Intégration Home Assistant (custom component, compatible HACS) pour piloter un Divoom Pixoo 64 :
état authoritatif de l'écran via `Channel/GetAllConf`, configuration des pages directement
dans le config entry, et composants de rendu enrichis (icônes MDI, progress bar).

> ⚠️ Projet en cours de développement (Phase 1 terminée). Pas encore d'entités —
> voir [État actuel](#état-actuel) ci-dessous avant d'installer.

## État actuel

- ✅ L'intégration est ajoutable depuis l'UI Home Assistant (IP manuelle, test de connexion).
- ✅ Un coordinator interroge le Pixoo toutes les 15 secondes et lit l'état authoritatif
  de l'écran (`LightSwitch`, `Brightness`, rotation, mirroir, page courante).
- ❌ **Aucune entité n'est encore créée** (`switch`, `light`, `sensor` arrivent en Phase 2) :
  l'intégration se configure mais ne pilote rien dans HA pour l'instant.
- ❌ Pas encore de rendu de pages (Phase 3+).

## Installation

Pas encore publiée sur HACS (aucune release taguée). En attendant, installation manuelle :

1. Copier le dossier `custom_components/pixoo_canvas` dans `<config_dir>/custom_components/`.
2. Redémarrer Home Assistant.

## Configuration

Depuis l'UI : **Paramètres → Appareils et services → Ajouter une intégration → Pixoo Canvas**,
puis renseigner l'adresse IP du Pixoo sur le réseau local. Une connexion de test
(`Channel/GetAllConf`) est effectuée avant la création de l'entrée.

## Licence

MIT — voir [LICENSE](LICENSE).
