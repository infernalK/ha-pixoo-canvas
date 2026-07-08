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
  - [Page : Sound meter (sonomètre)](#page--sound-meter-sonomètre)
  - [Page : PV (solaire)](#page--pv-solaire)
  - [Page : Fuel (station-service)](#page--fuel-station-service)
- [Rotation automatique des pages](#rotation-automatique-des-pages)
- [Service : afficher une page à la demande](#service--afficher-une-page-à-la-demande)
- [Service : faire sonner le buzzer](#service--faire-sonner-le-buzzer)
- [Service : redémarrer l'appareil](#service--redémarrer-lappareil)
- [Service : minuteur (start_timer / stop_timer)](#service--minuteur-start_timer--stop_timer)
- [Service : chronomètre (start_stopwatch / pause_stopwatch / stop_stopwatch / reset_stopwatch)](#service--chronomètre-start_stopwatch--pause_stopwatch--stop_stopwatch--reset_stopwatch)
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
- `switch.pixoo_mirror_mode` — miroir horizontal de l'écran.
- `select.pixoo_screen_orientation` — orientation physique de l'écran (0°/90°/180°/270°),
  à régler selon le montage de ton cadre.
- `button.pixoo_reboot` — redémarre l'appareil en un tap (équivalent du service
  `pixoo_canvas.reboot_device`, voir plus bas). Un bouton plutôt qu'un switch : un
  redémarrage n'a pas d'état on/off persistant à refléter.
- `switch.pixoo_channel_faces` / `channel_cloud` / `channel_visualizer` / `channel_custom`
  — un switch par channel de haut niveau de l'appareil (l'horloge, le flux Cloud Divoom,
  le visualiseur audio, ou tes channels personnalisés), à la manière de boutons radio :
  activer l'un désactive implicitement les 3 autres. Éteindre celui qui est déjà actif ne
  fait rien — il n'y a pas d'état "aucun channel". Comme `start_timer`/`start_stopwatch`,
  activer un channel met `switch.pixoo_page_rotation` en pause si elle tournait ; l'éteindre
  la relance, seulement si c'est ce switch qui l'avait mise en pause.
  > ⚠️ Ces switches ne reflètent que le dernier channel activé *via ce switch* — pas
  > forcément ce qui est réellement affiché à l'instant T (utilise
  > `sensor.pixoo_active_channel` pour ça).
- `sensor.pixoo_active_channel` — le channel réellement actif sur l'appareil en ce moment
  (Faces/Cloud/Visualizer/Custom), à jour même si le changement vient d'ailleurs que Home
  Assistant (app Divoom, télécommande).
- 2 autres capteurs de diagnostic (indicateur de rotation, ID de l'horloge affichée) —
  utiles pour du dépannage, pas pour un usage quotidien.
- `sensor.pixoo_device_id` — un capteur diagnostic dont l'état est le `device_id`
  Home Assistant de cet appareil, celui attendu par tous les services `pixoo_canvas.*`
  (`render_page`, `play_buzzer`, `reboot_device`, `start_timer`, `stop_timer`). Pratique
  pour construire un raccourci iOS/Android sans devoir aller le chercher dans l'URL de
  Paramètres → Appareils.

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
| `page_type` | Non | `components` | `components`, `clock`, `channel`, `visualizer`, `sound_meter`, `pv`, `fuel`. |
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
autres types (`clock`, `channel`, `visualizer`, `sound_meter`, `pv`, `fuel`) s'utilisent
exactement de la même façon une fois que tu as compris le principe.

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

Par défaut, le texte est dessiné une fois dans le buffer de l'image (statique). Avec
`scroll: true`, il défile à la place, animé nativement par l'écran (pas par nous) —
utile pour un message plus long que l'écran.

⚠️ **En mode `scroll: true`, `font`/`font_size` (nos polices bitmap) sont ignorés.** Le
texte n'est alors plus dessiné par l'intégration : il est envoyé tel quel au firmware du
Pixoo (`Draw/SendHttpText`), qui l'anime et le rend lui-même avec une de ses polices
natives (`divoom_font`, 0-7 — voir l'aperçu ci-dessous). Nos polices bitmap ne peuvent
pas s'appliquer sur ce chemin : c'est le device qui dessine les pixels, pas nous.

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `position` | Oui | | `[x, y]` |
| `content` | Oui | | Texte, avec support des templates `{{ }}` et des retours à la ligne. |
| `color` | Non | `white` | `[R, G, B]` ou nom de couleur — voir [Couleurs](#couleurs). |
| `align` | Non | `left` | `left`, `center`, `right`. |
| `font` | Non | `pico_8` | Police bitmap — voir [Polices](#polices) ci-dessous. Ignoré si `scroll: true`. |
| `font_size` | Non | `1` | Échelle entière de la police bitmap. Ignoré si `scroll: true`. |
| `scroll` | Non | `false` | `true` pour un défilement natif (matériel) plutôt qu'un dessin statique. |

Champs suivants, utilisés uniquement quand `scroll: true` :

| Champ | Obligatoire | Défaut | Valeurs |
| --- | :---: | :---: | --- |
| `scroll_direction` | Non | `left` | `left`, `right` |
| `scroll_speed` | Non | `100` | Millisecondes par pas — plus petit = plus rapide. |
| `text_width` | Non | `64` | Largeur de la zone de défilement en pixels. |
| `divoom_font` | Non | `0` | Police native du Pixoo (0-7), utilisée par le firmware pour le rendu défilant. |
| `text_id` | Non | | Identifiant du slot (0-19), pour superposer plusieurs textes défilants. |

**Aperçu des polices natives (`divoom_font`)**, confirmé sur device réel (Pixoo 64) :

| `divoom_font` | Taille (L×H, px) | Style observé |
| --- | :---: | --- |
| `0` | 10×7 | Traits fins, majuscules/minuscules distinctes — la plus sobre. |
| `1` | 11×10 | Grande et grasse, la plus haute. |
| `2` | 8×7 | La plus compacte/condensée. |
| `3` | 10×10 | Même largeur que `0` mais nettement plus haute. |
| `4` | 11×8 | Grande et grasse, un peu moins haute que `1`. |
| `5` | 13×9 | La plus large, blocky. |
| `6` | 13×8 | Aussi large que `5`, style penché/dynamique. |
| `7` | 11×8 | Grande, droite, nette, sans empattement — très lisible. |

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

| `font` | Hauteur native | Largeur (pour "Temperatures") |
| --- | --- | --- |
| `pico_8` (défaut) | 5px | 47px |
| `gicko` | 6px, plus large | 80px |
| `matrix_chunky_6` | 6px | 49px |
| `matrix_chunky_8` | 8px | 49px |

Ce sont de vraies polices bitmap (portées depuis
[gickowtf/pixoo-homeassistant](https://github.com/gickowtf/pixoo-homeassistant) et
[trip5/Matrix-Fonts](https://github.com/trip5/Matrix-Fonts), licence MIT) : chaque glyphe
est une grille de pixels fixe, comme sur un vrai écran LED — c'est ce qui reste lisible
sur l'écran physique (des polices TrueType ont été essayées et retirées, illisibles une
fois réduites à cette taille). `font_size` est un facteur d'échelle entier (`font_size: 2`
double chaque pixel, défaut `1`) plutôt qu'une taille de police classique.

`gicko` n'a pas de glyphes minuscules dans la police d'origine : une minuscule est
automatiquement affichée avec le glyphe majuscule correspondant. `pico_8`,
`matrix_chunky_6` et `matrix_chunky_8` ont bien de vraies minuscules ; ces deux derniers
ont aussi de vraies descendantes (g/y/p qui dépassent sous la ligne de base) et les
accents français (à â é è ê ë î ï ô ù û ü ç œ et majuscules), en plus des guillemets
français « » et du signe degré.

Aperçu (rendu réel, zoomé x10 pour la lisibilité) :

| `pico_8` | `gicko` |
| --- | --- |
| ![pico_8](docs/img/fonts/pico_8.png) | ![gicko](docs/img/fonts/gicko.png) |

| `matrix_chunky_6` | `matrix_chunky_8` |
| --- | --- |
| ![matrix_chunky_6](docs/img/fonts/matrix_chunky_6.png) | ![matrix_chunky_8](docs/img/fonts/matrix_chunky_8.png) |

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

### Page : Sound meter (sonomètre)

Bascule sur l'outil sonomètre intégré au Pixoo (mesure de niveau sonore en dB, écran
plein). Pas de champ `id` : il n'y en a qu'un seul.

```yaml
- name: Sonomètre
  page_type: sound_meter
```

> ⚠️ Comme le [minuteur](#service--minuteur-start_timer--stop_timer) et le
> [chronomètre](#service--chronomètre-start_stopwatch--pause_stopwatch--stop_stopwatch--reset_stopwatch),
> cet outil prend tout l'écran. Pas besoin de l'arrêter manuellement avant de passer à
> une autre page : n'importe quel changement de page (rotation ou service `render_page`)
> l'arrête automatiquement.

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

Les autres `page_type` (`clock`, `channel`, `visualizer`, `sound_meter`, `pv`, `fuel`)
marchent aussi en ligne, en indiquant `page_type` et les champs de ce type (voir le
tableau plus haut) :

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

## Service : redémarrer l'appareil

Le service `pixoo_canvas.reboot_device` redémarre le Pixoo — utile
dans une automation de récupération (ex. appareil qui ne répond plus), pas comme action
de routine. L'écran s'éteint quelques instants ; la rotation, si elle était active,
reprend d'elle-même une fois l'appareil de nouveau en ligne. Pour un déclenchement manuel
depuis un tableau de bord ou un raccourci, `button.pixoo_reboot` fait la même chose sans
passer par un appel de service.

```yaml
service: pixoo_canvas.reboot_device
data:
  device_id: <ton appareil Pixoo Canvas>
```

## Service : minuteur (start_timer / stop_timer)

Les services `pixoo_canvas.start_timer` et `pixoo_canvas.stop_timer` pilotent l'outil
minuteur intégré au Pixoo — il prend tout l'écran jusqu'à l'arrêt ou le passage à une
autre page/service. Si `switch.pixoo_page_rotation` est actif, `start_timer` le met
automatiquement en pause (sans changer ta préférence on/off) pour que le minuteur ne soit
pas écrasé au tour suivant ; `stop_timer` relance la rotation seulement si c'est
`start_timer` qui l'avait mise en pause. `stop_timer` marche même sans `start_timer`
préalable (pratique pour un Raccourci "au cas où") et laisse toujours l'écran propre,
sans le cadre du minuteur qui traîne.

```yaml
service: pixoo_canvas.start_timer
data:
  device_id: <ton appareil Pixoo Canvas>
  minutes: 5   # optionnel, défaut 0 — minutes/secondes ne peuvent pas être toutes les deux à 0
  seconds: 30  # optionnel, défaut 0
```

```yaml
service: pixoo_canvas.stop_timer
data:
  device_id: <ton appareil Pixoo Canvas>
```

> ⚠️ Confirmé sur device réel (et dans l'app Divoom elle-même) : arrêter un minuteur en
> cours remet toujours le compte à rebours à zéro. Contrairement au chronomètre, il
> n'existe donc pas de vraie pause pour le minuteur — impossible de le figer en cours de
> route puis de reprendre le compte à rebours là où il en était.

**Pour un raccourci iOS** : pas besoin de rien de spécial côté intégration — l'app
Home Assistant Companion expose nativement n'importe quel service HA comme étape
"Effectuer une action" ("Perform action") dans l'app Raccourcis. Crée un raccourci avec
cette étape, choisis `pixoo_canvas.start_timer` (ou `stop_timer`), renseigne `device_id`
(et `minutes`/`seconds` pour le démarrage), et ajoute-le à l'écran d'accueil ou pilote-le
via Siri. Pour le `device_id` : regarde l'état de `sensor.pixoo_device_id` (copie-le
depuis Paramètres → Appareils et services → Entités, ou l'historique de l'entité) plutôt
que de le chercher dans l'URL de la page de l'appareil.

## Service : chronomètre (start_stopwatch / pause_stopwatch / stop_stopwatch / reset_stopwatch)

Les services `pixoo_canvas.start_stopwatch`, `pixoo_canvas.pause_stopwatch`,
`pixoo_canvas.stop_stopwatch` et `pixoo_canvas.reset_stopwatch` pilotent l'outil
chronomètre intégré au Pixoo, en tout point similaire au minuteur (voir ci-dessus) : il
prend tout l'écran jusqu'à l'arrêt ou le passage à une autre page/service. Aucun champ
requis à part `device_id` — le chronomètre compte simplement depuis zéro.

`pause_stopwatch` et `stop_stopwatch` arrêtent tous les deux le décompte, mais avec une
différence importante : **`stop_stopwatch`** relance `switch.pixoo_page_rotation` (si
`start_stopwatch` l'avait mise en pause) et laisse l'écran propre — c'est le bon choix
quand tu as fini d'utiliser le chronomètre, y compris appelé directement sans
`start_stopwatch` préalable (pratique pour un Raccourci "au cas où"). **`pause_stopwatch`**
ne fait ni l'un ni l'autre : la rotation reste en pause et le chronomètre reste affiché,
temps écoulé figé à l'écran — utilise-le quand tu comptes reprendre avec `start_stopwatch`
sous peu.

```yaml
service: pixoo_canvas.start_stopwatch
data:
  device_id: <ton appareil Pixoo Canvas>
```

```yaml
service: pixoo_canvas.pause_stopwatch
data:
  device_id: <ton appareil Pixoo Canvas>
```

```yaml
service: pixoo_canvas.reset_stopwatch
data:
  device_id: <ton appareil Pixoo Canvas>
```

```yaml
service: pixoo_canvas.stop_stopwatch
data:
  device_id: <ton appareil Pixoo Canvas>
```

## Licence

MIT — voir [LICENSE](LICENSE).
