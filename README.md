# ha-pixoo-canvas

Intégration Home Assistant (custom component, compatible HACS) pour piloter un Divoom Pixoo 64 :
état authoritatif de l'écran via `Channel/GetAllConf`, configuration des pages directement
dans le config entry, et composants de rendu enrichis (icônes MDI, progress bar).

> ⚠️ Projet en cours de développement (Phase 5 terminée). Voir
> [État actuel](#état-actuel) ci-dessous avant d'installer.

## État actuel

- ✅ L'intégration est ajoutable depuis l'UI Home Assistant (IP manuelle, test de connexion).
- ✅ Un coordinator interroge le Pixoo toutes les 15 secondes et lit l'état authoritatif
  de l'écran (`LightSwitch`, `Brightness`, rotation, mirroir, page courante).
- ✅ Entités disponibles :
  - `switch.pixoo_screen_power` — allumage/extinction de l'écran, authoritatif (plus de flapping)
  - `light.pixoo_brightness` — luminosité uniquement, découplée du power (plus d'ambiguïté brightness/on-off)
  - `switch.pixoo_page_rotation` — active/désactive la rotation automatique des pages, état
    restauré après redémarrage
  - 3 capteurs diagnostic : rotation écran, mirroir, ID de l'horloge/page courante
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

Le composant `text` accepte un champ `font` optionnel (par défaut `press_start_2p`) :

| `font` | Style | Hauteur à `font_size: 6` | Largeur (pour "Fete du jour") |
| --- | --- | --- | --- |
| `press_start_2p` (défaut) | bloc large, style arcade | 7px | 72px |
| `silkscreen` | fine, compacte | 4px | 52px |
| `silkscreen_bold` | comme `silkscreen`, en gras | 4px | 56px |

`press_start_2p` reste le défaut : sur l'écran LED physique, c'est la **hauteur** du glyphe qui
détermine la lisibilité (le flou de diffusion des LED rend une police fine illisible), pas
juste la largeur. `silkscreen` est plus étroite mais nettement moins lisible sur l'écran réel
à taille égale — à réserver aux cas où tu as vraiment besoin de caser plus de caractères et où
tu acceptes ce compromis (idéalement avec une `font_size` plus grande pour compenser la
hauteur, ex. `font_size: 10`).

**Le vrai problème que tu as vu** (texte coupé) vient du fait qu'à `font_size: 6` (le défaut),
`press_start_2p` déborde de l'écran 64px dès qu'un titre dépasse ~10 caractères. Sur tes 7
pages, ça concerne concrètement les titres **Alerte météo**, **Fête du jour**,
**Températures**, **Poubelles !** et **~ PISCINE ~** (pas seulement "Fête du jour"). Le fix
n'est pas de changer de police mais de réduire `font_size` sur ces titres précis :

```yaml
- type: text
  position: [0, 0]
  content: "Temperatures"
  font_size: 5   # au lieu du défaut (6) qui déborde pour ce titre précis
  color: yellow
```

À `font_size: 5`, ces 5 titres tiennent tous dans les 64px (max 60px de large), avec une perte
de lisibilité minime par rapport à la taille 6.

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
