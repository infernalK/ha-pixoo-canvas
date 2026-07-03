# Pixoo Canvas — Intégration Home Assistant pour Divoom Pixoo 64

Intégration Home Assistant (custom component, compatible HACS) pour piloter un Divoom
Pixoo 64 depuis Home Assistant : allumage/luminosité, et surtout un système de **pages**
personnalisées affichant tes capteurs, textes et images, avec rotation automatique entre
elles. Inspirée de [gickowtf/pixoo-homeassistant](https://github.com/gickowtf/pixoo-homeassistant).

> ⚠️ Pas encore publiée sur le store par défaut HACS (voir [Installation](#installation)
> pour l'installer quand même dès maintenant).

## Sommaire

- [Installation](#installation)
- [Configuration de base](#configuration-de-base)
- [Ce que tu obtiens](#ce-que-tu-obtiens)
- [Les pages](#les-pages)
  - [Page : Components (ton propre design)](#page--components-ton-propre-design)
  - [Page : Clock (horloge native)](#page--clock-horloge-native)
  - [Page : Channel (channel personnalisé Divoom)](#page--channel-channel-personnalisé-divoom)
  - [Page : Visualizer (visualiseur audio)](#page--visualizer-visualiseur-audio)
  - [Page : PV (solaire)](#page--pv-solaire)
  - [Page : Fuel (station-service)](#page--fuel-station-service)
- [Rotation automatique des pages](#rotation-automatique-des-pages)
- [Service : afficher une page à la demande](#service--afficher-une-page-à-la-demande)
- [Service : faire sonner le buzzer](#service--faire-sonner-le-buzzer)
- [Licence](#licence)

## Installation

**Via HACS** (dépôt personnalisé, en attendant la publication sur le store par défaut) :

1. Dans HACS → menu (⋮) → **Dépôts personnalisés**, ajoute
   `https://github.com/infernalK/ha-pixoo-canvas` en catégorie **Intégration**.
2. Installe "Pixoo Canvas" depuis HACS.
3. Redémarre Home Assistant.

**Manuellement**, si tu n'utilises pas HACS :

1. Copie le dossier `custom_components/pixoo_canvas` de ce dépôt dans le dossier
   `custom_components` de ta config Home Assistant.
2. Redémarre Home Assistant.

## Configuration de base

**Paramètres → Appareils et services → Ajouter une intégration → Pixoo Canvas.**

Si un Pixoo est détecté sur ton réseau, choisis-le dans la liste (ou "Enter IP
manually" sinon). Une fois ajoutée, clique sur **Configurer** sur la carte Pixoo Canvas
pour régler :

| Réglage | Description |
| --- | --- |
| Adresse IP | Modifiable après coup si ton Pixoo change d'IP. |
| Durée d'affichage par défaut | Combien de temps chaque page reste à l'écran pendant la rotation automatique, sauf si elle précise sa propre `duration` (voir [Rotation automatique](#rotation-automatique-des-pages)). |
| Pages (YAML) | La liste de tes pages — voir [Les pages](#les-pages) ci-dessous. |

Chaque sauvegarde teste la connexion à l'appareil avant d'appliquer les changements.

## Ce que tu obtiens

Une fois l'intégration configurée, tu as accès à :

- `switch.pixoo_screen_power` — allumer/éteindre l'écran.
- `light.pixoo_brightness` — régler la luminosité.
- `switch.pixoo_page_rotation` — activer/désactiver le défilement automatique des pages.
- `select.pixoo_screen_orientation` — orientation physique de l'écran (0°/90°/180°/270°),
  à régler selon le montage de ton cadre.
- 3 capteurs de diagnostic (rotation, effet miroir, ID de l'horloge affichée) — utiles
  pour du dépannage, pas pour un usage quotidien.

## Les pages

Une **page**, c'est un bloc YAML avec au minimum un `name`. Le champ `page_type`
détermine comment elle s'affiche — s'il est absent, c'est `components` (ton propre
design, voir ci-dessous). Colle tes pages dans le champ **Pages (YAML)** des options,
sous forme de liste :

```yaml
- name: Ma première page
  page_type: components   # optionnel, c'est le défaut
  components:
    - type: text
      position: [2, 2]
      content: "Bonjour !"
```

**Champs communs à toutes les pages**, quel que soit leur `page_type` :

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `name` | Oui | | Nom de la page (utilisé pour l'appeler via le service `render_page`). |
| `page_type` | Non | `components` | `components`, `clock`, `channel`, `visualizer`, `pv`, `fuel`. |
| `enabled` | Non | activée | `true`/`false` ou template `{{ }}` — pages désactivées sautées par la rotation. |
| `duration` | Non | (le réglage global) | Secondes d'affichage avant de passer à la page suivante, en rotation. |
| `scan_interval` | Non | | Secondes entre rafraîchissements pendant que la page est affichée (utile pour des valeurs qui changent souvent). |

```yaml
- name: SPA
  enabled: "{{ states('input_boolean.spa_actif') }}"
  duration: 20
  scan_interval: 10
  page_type: components
  components: [...]
```

Si tu débutes, commence par une page `components` : c'est la plus flexible, et les
autres types (`clock`, `channel`, `visualizer`, `pv`, `fuel`) s'utilisent exactement de
la même façon une fois que tu as compris le principe.

### Page : Components (ton propre design)

Le Pixoo devient ta toile : tu empiles des **composants** (texte, image, rectangle...) à
des positions précises sur un écran de 64×64 pixels. `(0, 0)` est le coin en haut à
gauche, `(63, 63)` le coin en bas à droite.

```yaml
- name: Températures
  page_type: components
  components:
    - type: rectangle
      position: [0, 0]
      size: [64, 64]
      color: black
    - type: text
      position: [2, 2]
      content: "{{ states('sensor.salon_temperature') }}°C"
      color: white
```

#### Composant : `text`

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `position` | Oui | | `[x, y]` |
| `content` | Oui | | Texte, avec support des templates `{{ }}` et des retours à la ligne. |
| `font` | Non | `pico_8` | Voir [Polices](#polices) ci-dessous. |
| `color` | Non | `white` | `[R, G, B]` ou nom de couleur — voir [Couleurs](#couleurs). |
| `align` | Non | `left` | `left`, `center`, `right`. |

#### Composant : `image`

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `position` | Oui | | `[x, y]` |
| `image_url` ou `image_path` | Oui (une des deux) | | URL (ou template `{{ }}`) ou chemin local, ex. `/config/www/logo.png`. |

#### Composant : `rectangle`

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `position` | Oui | | `[x, y]` |
| `size` | Oui | | `[largeur, hauteur]` |
| `color` | Non | `white` | `[R, G, B]` ou nom de couleur. |
| `filled` | Non | `true` | `true` (rempli) ou `false` (contour seul). |

#### Composant : `icon`

Icône [Material Design Icons](https://pictogrammers.com/library/mdi/) (avec ou sans
préfixe `mdi:`), coloriée et redimensionnée — aucun appel réseau, tout est embarqué dans
l'intégration.

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `position` | Oui | | `[x, y]` |
| `icon` | Oui | | Nom MDI, ex. `mdi:thermometer` ou juste `thermometer`. |
| `size` | Non | `16` | Taille en pixels. |
| `color` | Non | `white` | `[R, G, B]` ou nom de couleur. |
| `value` + `color_thresholds` | Non | | Colore l'icône selon une valeur — voir ci-dessous. |

#### Composant : `progress_bar`

Barre de progression horizontale ou verticale.

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `position` | Oui | | `[x, y]` |
| `size` | Oui | | `[largeur, hauteur]` |
| `orientation` | Non | `horizontal` | `horizontal`, `vertical` |
| `transition` | Non | `hard` | `hard` (bord net) ou `smooth` (dégradé au bord) |
| `min` / `max` | Non | `0` / `100` | Bornes de la valeur. |
| `value` | Oui | | Valeur actuelle, brute ou template. |
| `background_color` | Non | gris foncé | `[R, G, B]` ou nom de couleur. |
| `color` + `color_thresholds` | Non | vert | Couleur de la barre — voir ci-dessous. |

**`color_thresholds`** (commun à `icon` et `progress_bar`) : une liste croissante de
paliers `{value, color}`. La couleur retenue est celle du palier le plus élevé encore
inférieur ou égal à `value` :

```yaml
- type: progress_bar
  position: [2, 50]
  size: [60, 6]
  value: "{{ states('sensor.spa_filtration_pct') }}"
  color_thresholds:
    - value: 0
      color: red
    - value: 50
      color: orange
    - value: 90
      color: green
```

#### Composant : `scroll_text`

Texte défilant, animé nativement par l'écran (pas par nous) — utile pour un message plus
long que l'écran.

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `position` | Oui | | `[x, y]` |
| `content` | Oui | | Texte, avec support des templates. |
| `color` | Non | `white` | `[R, G, B]` ou nom de couleur. |
| `direction` | Non | `left` | `left`, `right` |
| `width` | Non | `64` | Largeur de la zone de défilement en pixels. |
| `speed` | Non | `100` | Millisecondes par pas — plus petit = plus rapide. |
| `align` | Non | `left` | `left`, `center`, `right` |
| `text_id` | Non | | Identifiant du slot (0-19), pour superposer plusieurs textes défilants. |

#### Composant : `templatable`

Pour les cas avancés : un template Jinja qui génère lui-même une liste de composants
(utile pour des grilles répétitives). Réservé à qui est déjà à l'aise avec les templates
Home Assistant.

```yaml
- type: templatable
  template: >-
    {% set output = namespace(list=[]) %}
    {% for i in range(5) %}
      {% set output.list = output.list + [{"type": "rectangle", "position": [i * 10, 0], "size": [8, 8], "color": "red"}] %}
    {% endfor %}
    {{ output.list }}
```

#### Polices

Le composant `text` accepte un champ `font` optionnel :

| `font` | Type | Hauteur native | Largeur (pour "Temperatures") |
| --- | --- | --- | --- |
| `pico_8` (défaut) | bitmap pixel natif | 5px | 47px |
| `gicko` | bitmap pixel natif, plus large | 6px | 83px |
| `press_start_2p` | TrueType (`font_size`, défaut 6) | 7px | 72px |
| `silkscreen` | TrueType (`font_size`, défaut 6) | 4px | 55px |
| `silkscreen_bold` | TrueType (`font_size`, défaut 6) | 4px | 61px |

`pico_8` et `gicko` sont de vraies polices bitmap (portées depuis
[gickowtf/pixoo-homeassistant](https://github.com/gickowtf/pixoo-homeassistant), licence
MIT) : chaque glyphe est une grille de pixels fixe, comme sur un vrai écran LED — c'est
ce qui reste le plus lisible sur l'écran physique. Pour ces deux polices, `font_size` est
un facteur d'échelle entier (`font_size: 2` double chaque pixel, défaut `1`) plutôt
qu'une taille de police classique. `gicko` n'a pas de glyphes minuscules dans la police
d'origine : une minuscule est automatiquement affichée avec le glyphe majuscule
correspondant (`pico_8` a bien les minuscules).

Aperçu (rendu réel, zoomé x10 pour la lisibilité) :

| `pico_8` | `gicko` |
| --- | --- |
| ![pico_8](docs/img/fonts/pico_8.png) | ![gicko](docs/img/fonts/gicko.png) |

| `press_start_2p` | `silkscreen` | `silkscreen_bold` |
| --- | --- | --- |
| ![press_start_2p](docs/img/fonts/press_start_2p.png) | ![silkscreen](docs/img/fonts/silkscreen.png) | ![silkscreen_bold](docs/img/fonts/silkscreen_bold.png) |

#### Couleurs

Partout où une couleur est attendue, tu peux utiliser :
- Une liste `[R, G, B]`, ex. `[255, 0, 0]`.
- Un nom de couleur CSS, ex. `red`, `orange`, `deepskyblue`.
- Un code hexadécimal, ex. `"#FF0000"`.
- Un template `{{ }}` qui produit l'un des trois ci-dessus.

### Page : Clock (horloge native)

Bascule l'écran sur une des horloges intégrées au Pixoo (celles que tu choisirais dans
l'app Divoom) — aucun composant à dessiner, l'appareil gère tout lui-même.

| Champ | Obligatoire | Valeurs |
| --- | :---: | --- |
| `id` | Oui | ID de l'horloge (entier ou template). Voir la [liste des horloges](https://github.com/gickowtf/pixoo-homeassistant/blob/main/READMES/CLOCKS.md), ou active le logging debug de l'intégration et choisis l'horloge dans l'app Divoom : l'ID apparaît dans les logs (`CurClockId`). |

```yaml
- name: Horloge
  page_type: clock
  id: 182
```

### Page : Channel (channel personnalisé Divoom)

Bascule sur un des 3 "channels personnalisés" que tu configures dans l'app Divoom
elle-même (le rythme de défilement des images du channel se règle dans l'app, pas ici).

| Champ | Obligatoire | Valeurs |
| --- | :---: | --- |
| `id` | Oui | `0`, `1` ou `2` (les 3 channels personnalisés de l'app Divoom). |

```yaml
- name: Channel photos
  page_type: channel
  id: 0
```

### Page : Visualizer (visualiseur audio)

Bascule sur un des visualiseurs audio intégrés au Pixoo.

| Champ | Obligatoire | Valeurs |
| --- | :---: | --- |
| `id` | Oui | Index du visualiseur, tel qu'affiché dans l'app Divoom (à partir de 0). |

```yaml
- name: Visualiseur
  page_type: visualizer
  id: 2
```

### Page : PV (solaire)

Page prête à l'emploi pour un système solaire/batterie — l'icône batterie et la barre
de charge changent de couleur automatiquement (rouge → orange → vert) selon le niveau.

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `power` | Non | | Puissance actuelle (affichée en W), brute ou template. |
| `storage` | Non | | Niveau de batterie en % (0-100), colore l'icône et la barre. |
| `discharge` | Non | | Puissance de décharge (affichée en W) — n'apparaît que si renseigné. |
| `time` | Non | heure courante | Heure affichée en haut à droite. |

```yaml
- name: Solaire
  page_type: pv
  power: "{{ states('sensor.solar_power') }}"
  storage: "{{ states('sensor.battery_level') }}"
  discharge: "{{ states('sensor.battery_discharge') }}"
```

### Page : Fuel (station-service)

Page prête à l'emploi pour afficher jusqu'à 3 prix de carburant.

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `title` | Non | | Titre en haut de la page, ex. nom de la station. |
| `name1`/`price1`, `name2`/`price2`, `name3`/`price3` | Non | | Chaque paire est optionnelle : une ligne ne s'affiche que si `name` ou `price` est renseigné. |
| `status` | Non | | Ligne libre en bas de la page, ex. ouvert/fermé. |

```yaml
- name: Station Total
  page_type: fuel
  title: Total
  name1: Diesel
  price1: "{{ states('sensor.prix_diesel') }}"
  name2: SP95
  price2: "{{ states('sensor.prix_sp95') }}"
  status: "{{ 'Ouvert' if is_state('binary_sensor.station_ouverte', 'on') else 'Fermé' }}"
```

## Rotation automatique des pages

Active `switch.pixoo_page_rotation` pour faire défiler automatiquement toutes les pages
activées (celles dont `enabled` n'est pas `false`), dans l'ordre où elles apparaissent
dans ta config, chacune pendant sa `duration` (ou la durée par défaut réglée dans les
options si elle n'en précise pas). Cette rotation reprend automatiquement au redémarrage
de Home Assistant si elle était active avant l'arrêt.

## Service : afficher une page à la demande

Le service `pixoo_canvas.render_page` affiche une page immédiatement, sans attendre son
tour dans la rotation :

```yaml
service: pixoo_canvas.render_page
data:
  device_id: <ton appareil Pixoo Canvas>
  page: Températures
```

Tu peux aussi lui passer une page directement en ligne (sans nommer de page
existante), pour un affichage ponctuel — pratique pour une notification. Sans
`page_type`, une liste de `components` est attendue (le défaut) :

```yaml
service: pixoo_canvas.render_page
data:
  device_id: <ton appareil Pixoo Canvas>
  components:
    - type: rectangle
      position: [0, 0]
      size: [64, 64]
      color: black
    - type: text
      position: [2, 20]
      content: "Livraison arrivée !"
      color: yellow
```

Les autres `page_type` (`clock`, `channel`, `visualizer`, `pv`, `fuel`) marchent aussi
en ligne, en indiquant `page_type` et les champs de ce type (voir le tableau plus haut) :

```yaml
service: pixoo_canvas.render_page
data:
  device_id: <ton appareil Pixoo Canvas>
  page_type: clock
  id: 182
```

## Service : faire sonner le buzzer

Le service `pixoo_canvas.play_buzzer` fait sonner le buzzer intégré au Pixoo — pratique
pour une alerte sonore en plus d'une notification visuelle. ⚠️ À utiliser avec modération :
un usage répété/rapide pourrait fatiguer le matériel.

```yaml
service: pixoo_canvas.play_buzzer
data:
  device_id: <ton appareil Pixoo Canvas>
  active_time_ms: 500   # optionnel, défaut 500 — durée du buzzer par cycle
  off_time_ms: 500      # optionnel, défaut 500 — silence entre chaque cycle
  total_time_ms: 3000   # optionnel, défaut 3000 — durée totale de l'alerte
```

## Licence

MIT — voir [LICENSE](LICENSE).
