# ha-pixoo-canvas

Intégration Home Assistant (custom component, compatible HACS) pour piloter un Divoom Pixoo 64 :
état authoritatif de l'écran via `Channel/GetAllConf`, configuration des pages directement
dans le config entry, et composants de rendu enrichis (icônes MDI, progress bar).

> ⚠️ Projet en cours de développement (Phase 2 terminée). Pas encore de rendu de pages —
> voir [État actuel](#état-actuel) ci-dessous avant d'installer.

## État actuel

- ✅ L'intégration est ajoutable depuis l'UI Home Assistant (IP manuelle, test de connexion).
- ✅ Un coordinator interroge le Pixoo toutes les 15 secondes et lit l'état authoritatif
  de l'écran (`LightSwitch`, `Brightness`, rotation, mirroir, page courante).
- ✅ Entités disponibles :
  - `switch.pixoo_screen_power` — allumage/extinction de l'écran, authoritatif (plus de flapping)
  - `light.pixoo_brightness` — luminosité uniquement, découplée du power (plus d'ambiguïté brightness/on-off)
  - 3 capteurs diagnostic : rotation, mirroir, ID de l'horloge/page courante
- ❌ Pas encore de rendu de pages (`pixoo_canvas.render_page`, Phase 3+) : le `rest_command`
  actuel reste nécessaire pour l'affichage de contenu, cette intégration ne gère pour
  l'instant que l'état de l'écran (power/brightness).

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
