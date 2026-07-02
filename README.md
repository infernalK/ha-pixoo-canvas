# ha-pixoo-canvas

Intégration Home Assistant (custom component, compatible HACS) pour piloter un Divoom Pixoo 64 :
état authoritatif de l'écran via `Channel/GetAllConf`, configuration des pages directement
dans le config entry, et composants de rendu enrichis (icônes MDI, progress bar).

> ⚠️ Projet en cours de développement (Phase 5 terminée). Voir
> [État actuel](#état-actuel) ci-dessous avant d'installer.

## État actuel

- ✅ L'intégration est ajoutable depuis l'UI Home Assistant, avec détection automatique du
  Pixoo sur le réseau local (via le service de découverte cloud de Divoom, comme les autres
  intégrations Pixoo) — repli sur saisie manuelle de l'IP si rien n'est trouvé ou en cas d'échec.
- ✅ Un coordinator interroge le Pixoo (toutes les 15 secondes par défaut, configurable) et lit
  l'état authoritatif de l'écran (`LightSwitch`, `Brightness`, rotation, mirroir, page courante).
- ✅ IP et intervalle d'interrogation modifiables après coup depuis les options de l'intégration
  (rechargement automatique à la sauvegarde).
- ✅ Entités disponibles :
  - `switch.pixoo_screen_power` — allumage/extinction de l'écran, authoritatif (plus de flapping)
  - `light.pixoo_brightness` — luminosité uniquement, découplée du power (plus d'ambiguïté brightness/on-off)
  - `switch.pixoo_page_rotation` — active/désactive la rotation automatique des pages, état
    restauré après redémarrage
  - `select.pixoo_screen_orientation` — orientation physique de l'écran (0°/90°/180°/270°),
    à régler selon le montage de ton cadre — authoritatif via `GyrateAngle`
  - 3 capteurs diagnostic : indicateur de rotation (signification exacte non confirmée, probablement
    liée à la rotation auto de la galerie), mirroir, ID de l'horloge/page courante
- ✅ Rendu de pages : service `pixoo_canvas.render_page` (composants `text`, `image`,
  `rectangle`, `icon`, `progress_bar`, `templatable`), pages configurables dans les options
  de l'intégration (éditeur YAML brut). Le `rest_command` externe peut être remplacé
  progressivement.
- ✅ Rotation automatique des pages : chaque page peut définir `duration` (durée d'affichage),
  `scan_interval` (rafraîchissement pendant l'affichage) et `enabled` (condition Jinja) —
  voir [Rotation automatique](#rotation-automatique) ci-dessous.
- ✅ Interface traduite (FR/EN) pour la configuration et les entités.
- ❌ Pas encore : publication HACS (Phase 7).

## Installation

Pas encore publiée sur HACS (aucune release taguée). En attendant, installation manuelle :

1. Copier le dossier `custom_components/pixoo_canvas` dans `<config_dir>/custom_components/`.
2. Redémarrer Home Assistant.

## Configuration

Depuis l'UI : **Paramètres → Appareils et services → Ajouter une intégration → Pixoo Canvas**.
Si un ou plusieurs Pixoo sont détectés sur le réseau (via l'API de découverte de Divoom), une
liste à choisir apparaît, avec une option "Enter IP manually" ; sinon le formulaire de saisie
manuelle de l'IP s'affiche directement. Une connexion de test (`Channel/GetAllConf`) est
effectuée avant la création de l'entrée, que l'IP vienne de la détection ou d'une saisie
manuelle.

Ensuite, tout se règle depuis un seul écran d'options (**Configurer** sur la carte Pixoo
Canvas) : adresse IP de l'appareil (modifiable après coup, utile si le Pixoo change d'IP),
intervalle d'interrogation de l'état authoritatif de l'écran, et pages. Chaque sauvegarde
teste la connexion à l'IP indiquée avant d'appliquer les changements ; si l'adresse ou
l'intervalle change, l'intégration se recharge automatiquement pour en tenir compte.

### Pages

Les pages se configurent dans la même fenêtre d'options, sous forme de YAML brut, une liste
de pages nommées :

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

Les composants `icon` (icône MDI, avec couleur conditionnelle) et `progress_bar`
(barre horizontale/verticale) évitent la gymnastique Jinja pour ces cas fréquents :

```yaml
- name: SPA
  components:
    - type: rectangle
      position: [0, 0]
      size: [64, 64]
      color: black
    - type: icon
      icon: mdi:thermometer
      position: [2, 2]
      size: 16
      value: "{{ states('sensor.spa_temperature') }}"
      color_thresholds:
        - value: 0
          color: blue
        - value: 30
          color: green
        - value: 38
          color: red
    - type: text
      position: [20, 6]
      content: "{{ states('sensor.spa_temperature') }}°C"
      color: [255, 255, 255]
    - type: progress_bar
      position: [2, 50]
      size: [60, 6]
      orientation: horizontal
      transition: smooth
      min: 0
      max: 100
      value: "{{ states('sensor.spa_filtration_pct') }}"
      background_color: [40, 40, 40]
      color_thresholds:
        - value: 0
          color: red
        - value: 50
          color: orange
        - value: 90
          color: green
```

`icon` résout un nom [Material Design Icons](https://pictogrammers.com/library/mdi/) (avec ou
sans préfixe `mdi:`) en glyphe de la police MDI embarquée dans l'intégration (aucun appel
réseau, aucune dépendance système — juste Pillow), coloré et dessiné à la taille demandée
(`size`, en pixels). `color_thresholds` (commun à `icon` et `progress_bar`) prend une liste
ascendante `{value, color}` : la couleur retenue est celle du seuil le plus élevé encore
inférieur ou égal à `value`.

#### Polices

Le composant `text` accepte un champ `font` optionnel (par défaut `pico_8`) :

| `font` | Type | Hauteur native | Largeur (pour "Temperatures") |
| --- | --- | --- | --- |
| `pico_8` (défaut) | bitmap pixel natif | 5px | 47px |
| `gicko` | bitmap pixel natif, plus large | 6px | 83px |
| `press_start_2p` | TrueType (`font_size`, défaut 6) | 7px | 72px |
| `silkscreen` | TrueType (`font_size`, défaut 6) | 4px | 55px |
| `silkscreen_bold` | TrueType (`font_size`, défaut 6) | 4px | 61px |

`pico_8` et `gicko` sont de vraies polices bitmap (chaque glyphe est une grille de pixels
fixe, comme sur un vrai écran LED) portées depuis
[gickowtf/pixoo-homeassistant](https://github.com/gickowtf/pixoo-homeassistant) (licence MIT,
voir `render/fonts/bitmap/`) — l'intégration qui a inspiré ce projet et dont tes pages
utilisaient déjà `font: pico_8` à l'origine. `pico_8` est maintenant le défaut : c'est la seule
police qui reste à la fois compacte (~47px pour un titre de 12 caractères, contre 72px pour
`press_start_2p`) **et** assez haute (5px) pour rester lisible sur l'écran physique — contrairement
à `silkscreen`, plus étroite mais trop fine (4px) pour bien se voir derrière la diffusion des LED.

Pour les polices bitmap, `font_size` n'est pas une taille de point mais un **facteur d'échelle
entier** (`font_size: 2` double chaque pixel du glyphe, défaut `1`). Pour les polices
TrueType (`press_start_2p`, `silkscreen`, `silkscreen_bold`), `font_size` reste une taille de
police classique (défaut `6`).

##### Page de test des polices

Colle ça comme page (ou en `components` inline pour un test ponctuel via `render_page`) pour
comparer les 6 combinaisons sur ton écran réel avec le texte qui posait problème :

```yaml
- name: Test polices
  components:
    - type: rectangle
      position: [0, 0]
      size: [64, 64]
      color: black
    - type: text          # ligne 1 : défaut (pico_8, échelle 1)
      position: [0, 0]
      content: Temperatures
      font: pico_8
      color: white
    - type: text          # ligne 2 : gicko, échelle 1 (plus large, déborde ici)
      position: [0, 8]
      content: Temperatures
      font: gicko
      color: yellow
    - type: text          # ligne 3 : press_start_2p réduit (l'option de repli suggérée avant)
      position: [0, 16]
      content: Temperatures
      font: press_start_2p
      font_size: 5
      color: cyan
    - type: text          # ligne 4 : press_start_2p taille par défaut (déborde volontairement, pour comparaison)
      position: [0, 24]
      content: Temperatures
      font: press_start_2p
      font_size: 6
      color: orange
    - type: text          # ligne 5 : silkscreen agrandie pour compenser sa finesse
      position: [0, 34]
      content: Temperatures
      font: silkscreen
      font_size: 8
      color: lime
    - type: text          # ligne 6 : silkscreen_bold agrandie
      position: [0, 44]
      content: Temperatures
      font: silkscreen_bold
      font_size: 8
      color: magenta
```

Ordre des lignes de haut en bas : **pico_8** (blanc) · **gicko** (jaune) · **press_start_2p@5**
(cyan) · **press_start_2p@6** (orange, déborde volontairement) · **silkscreen@8** (vert) ·
**silkscreen_bold@8** (magenta). Regarde laquelle est la plus lisible *sur l'écran*, pas sur une
capture d'écran — dis-moi ton verdict et j'ajuste le défaut si `pico_8` ne te convainc pas non
plus.

Puis, pour l'afficher :

```yaml
service: pixoo_canvas.render_page
data:
  device_id: <ton device Pixoo Canvas>
  page: Températures
```

`render_page` accepte aussi `components` (liste inline) à la place de `page`, pour un
affichage ponctuel sans passer par la config des pages.

### Rotation automatique

Active `switch.pixoo_page_rotation` pour faire défiler automatiquement toutes les pages
activées de la config. Chaque page accepte trois champs optionnels :

```yaml
- name: SPA
  duration: 20          # secondes d'affichage avant de passer à la page suivante (défaut : 15)
  scan_interval: 10      # secondes entre rafraîchissements pendant que la page est affichée
  enabled: "{{ not is_state('sensor.spa_temperature_eau', 'unavailable') }}"  # condition Jinja, défaut : toujours activée
  components:
    - ...
```

- `duration` : combien de temps cette page reste à l'écran avant de passer à la suivante.
- `scan_interval` : si présent, la page est repoussée (mêmes composants, valeurs Jinja
  re-évaluées) à cet intervalle pendant qu'elle est affichée — utile pour les pages avec des
  valeurs qui changent souvent (température, minuteries...). Sans ce champ, la page n'est
  rendue qu'une fois à son tour.
- `enabled` : template Jinja évalué au début de chaque tour de rotation ; une page qui rend
  `false` est simplement sautée. Un appel à `render_page` avec `page: <nom>` continue de
  fonctionner sur une page désactivée par rotation.

La rotation reprend automatiquement au redémarrage de Home Assistant si elle était active
avant l'arrêt. Un appel manuel à `pixoo_canvas.render_page` pendant que la rotation tourne
affiche la page demandée jusqu'au prochain tick de rotation, qui la remplacera.

## Licence

MIT — voir [LICENSE](LICENSE).
