# ha-pixoo-canvas

Intégration Home Assistant (custom component, compatible HACS) pour piloter un Divoom Pixoo 64 :
état authoritatif de l'écran via `Channel/GetAllConf`, configuration des pages directement
dans le config entry, et composants de rendu enrichis (icônes MDI, progress bar).

> ⚠️ Projet en cours de développement (Phase 3 terminée). Voir
> [État actuel](#état-actuel) ci-dessous avant d'installer.

## État actuel

- ✅ L'intégration est ajoutable depuis l'UI Home Assistant (IP manuelle, test de connexion).
- ✅ Un coordinator interroge le Pixoo toutes les 15 secondes et lit l'état authoritatif
  de l'écran (`LightSwitch`, `Brightness`, rotation, mirroir, page courante).
- ✅ Entités disponibles :
  - `switch.pixoo_screen_power` — allumage/extinction de l'écran, authoritatif (plus de flapping)
  - `light.pixoo_brightness` — luminosité uniquement, découplée du power (plus d'ambiguïté brightness/on-off)
  - 3 capteurs diagnostic : rotation, mirroir, ID de l'horloge/page courante
- ✅ Rendu de pages : service `pixoo_canvas.render_page` (composants `text`, `image`,
  `rectangle`, `templatable`), pages configurables dans les options de l'intégration
  (éditeur YAML brut). Le `rest_command` externe peut être remplacé progressivement.
- ❌ Pas encore : icônes MDI/progress bar enrichis (Phase 4), rotation automatique des
  pages (Phase 5), publication HACS (Phase 7).

## Installation

Pas encore publiée sur HACS (aucune release taguée). En attendant, installation manuelle :

1. Copier le dossier `custom_components/pixoo_canvas` dans `<config_dir>/custom_components/`.
2. Redémarrer Home Assistant.

## Configuration

Depuis l'UI : **Paramètres → Appareils et services → Ajouter une intégration → Pixoo Canvas**,
puis renseigner l'adresse IP du Pixoo sur le réseau local. Une connexion de test
(`Channel/GetAllConf`) est effectuée avant la création de l'entrée.

### Pages

Les pages se configurent depuis les options de l'intégration (**Configurer** sur la carte
Pixoo Canvas) sous forme de YAML brut, une liste de pages nommées :

```yaml
- name: Températures
  components:
    - type: rectangle
      position: [0, 0]
      size: [64, 64]
      color: black
    - type: text
      position: [2, 2]
      content: "{{ states('sensor.salon_temperature') }}°C"
      color: [255, 255, 255]
```

Puis, pour l'afficher :

```yaml
service: pixoo_canvas.render_page
data:
  device_id: <ton device Pixoo Canvas>
  page: Températures
```

`render_page` accepte aussi `components` (liste inline) à la place de `page`, pour un
affichage ponctuel sans passer par la config des pages.

## Licence

MIT — voir [LICENSE](LICENSE).
