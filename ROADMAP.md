# Feuille de route

État des lieux et prochains chantiers envisagés pour ce package, dans l'ordre de priorité
proposé. Contexte : depuis la migration vers `energnn.converter` (PR #5), les ABC `Converter`
et `ElementsConverter` vivent dans energnn, et ce package ne fournit plus que la partie
PyPowSyBl — des convertisseurs d'éléments réduits à un getter pypowsybl + deux listes de
colonnes (ports et features).

## 1. Une conversion « recouvrante » paramétrée par options

Plutôt que de demander à l'utilisateur d'écrire une spec élément par élément, partir d'une
**config recouvrante** — une spec maximale qui couvre la quasi-totalité des usages — modulée
par quelques options orthogonales :

```python
converter = PypowsyblConverter(
    topology_view="bus_branch",    # "bus_branch" | "bus_breaker"
    features=("ac_pf_input",),     # grille solveur × rôle : "ac_pf_input" | "ac_pf_output" | "dc_pf_input" | "dc_pf_output"
    per_unit=True,
    regulation=True,               # ports de régulation distante (regulated_bus_id, ...)
    satellites={"ratio_tap_changers": "merge", "operational_limits": "connect"},
    infrastructure={"voltage_levels": "merge", "substations": "connect"},
    ports=True,                    # False : retirer les adresses (orthogonal aux features)
    main_component_only=True,
    extensions={"activePowerControl": "merge", "slackTerminal": "connect"},
)
```

Les options se rangent en deux groupes — la **structure** (quelles classes d'hyper-arêtes,
comment elles se connectent : `topology_view`, `regulation`, `satellites`, `infrastructure`,
`ports`) et les **features** (quels groupes de colonnes, une seule option) — et chacune
s'adosse à un mécanisme précis de l'API pypowsybl :

- **`features`** : les résultats d'un load flow ne sont pas des tables à part mais des
  colonnes d'état des mêmes getters (`p`, `q`, `i`, `p1`…`i2`, `v_mag`), à NaN tant
  qu'aucun calcul n'a tourné. L'option liste les groupes de colonnes à projeter, sur une
  grille solveur × rôle : `"ac_pf_input"` (les données du problème AC — impédances,
  limites, consignes) et `"ac_pf_output"` (l'état qu'il résout), plus leurs pendants DC
  `"dc_pf_input"`/`"dc_pf_output"` restreints au volet actif (l'AC recouvre le DC :
  `dc_* ⊆ ac_*`, invariant testé, d'où l'interdiction de mélanger les deux solveurs). Les
  groupes input/output d'un même solveur sont **cumulables** : l'entrée typique d'un GNN
  porte le problème *et* l'état issu d'un premier load flow
  (`("ac_pf_input", "ac_pf_output")`), une cible d'entraînement seulement l'état
  (`("ac_pf_output",)`). Les actuels `ACLoadFlowInput/OutputConverter` deviennent deux
  combinaisons. `ports=False` est un choix orthogonal, pas une composante de la cible :
  retirer les adresses seulement quand elles sont redondantes (lignes alignées avec un
  graphe d'entrée extrait du même réseau).
- **`topology_view`** : chaque élément porte ses adresses dans toutes les vues à la fois
  (`bus_id`, `bus_breaker_bus_id`) ; l'option choisit la colonne de port et la table de
  nœuds. `"bus_branch"` = `get_buses`, la vue du calcul ; `"bus_breaker"` =
  `get_bus_breaker_view_buses` + switches, la vue où les couplages redeviennent visibles.
  La vue node/breaker (busbar sections, internal connections, celle de l'optimisation de
  topologie du §3) n'a pas de table globale — seulement `get_node_breaker_topology(vl_id)`
  poste par poste, avec des nœuds entiers locaux à re-namespacer : un chantier à part,
  retiré des valeurs supportées en attendant. La dualité `dc_nodes`/`dc_buses` des réseaux
  DC maillés reproduit la même distinction — l'option s'applique aux deux couches (les
  `voltage_source_converters` pontant les deux : ports `bus*_id` côté AC, `dc_node*_id`
  côté DC).
- **`per_unit`** : attribut du `Network`, pas des getters — le convertisseur le positionne
  lui-même, ce qui règle le point d'hygiène « per_unit oublié = graphe silencieusement
  faux » du §4.
- **`regulation`** : ports de régulation distante (`regulated_bus_id` des
  générateurs/SVC/VSC — du contrôle de tension —, `regulating_bus_id` des régleurs, un
  contrôle de flux ou de courant pour les déphaseurs) — une arête vers un bus
  potentiellement lointain, indispensable au contrôle de tension (§3). Le réglage de
  fréquence (droop, facteurs de participation) ne porte pas de port : il arrivera en
  features via `extensions`.
- **`satellites`** : pypowsybl range beaucoup d'informations dans des tables rattachées à
  un élément parent par son id — régleurs et déphaseurs (`get_ratio/phase_tap_changers`,
  une ligne par régleur : `tap`, plage, consigne) et leurs prises (`_steps`, une ligne par
  prise), limites opérationnelles, courbes de capabilité, sections de shunts, génération
  des dangling lines. Le dict choisit table par table entre deux représentations :
  `"merge"` — agréger dans les features du parent, sans perte quand le satellite est
  1-pour-1 (le régleur dans son transfo), impossible sinon (il faudrait élire la limite
  permanente, le step courant, ...) ; `"connect"` — une classe d'hyper-arêtes à part
  entière, port vers le parent, la cardinalité variable étant native pour le GNN —
  indispensable dès que le satellite est l'objet d'intérêt (seuils temporaires du screening
  N-1, steps d'un réglage de prises). Table absente du dict = non extraite.
- **`infrastructure`** : les étages de localité — `voltage_levels` (nominal_v, limites de
  tension), `substations` (pays, TSO) et `areas` (zones de réglage,
  `interchange_target`) — choisis un par un avec le même vocabulaire que `satellites` :
  `"merge"` recopie les features de l'étage vers le bas, sur les bus porteurs de tension de
  la vue choisie (jointure via `voltage_level_id`, en chaîne bus → voltage level →
  substation pour les substations) ; `"connect"` en fait des classes d'hyper-arêtes,
  substations et areas se rattachant alors au graphe à travers les voltage_levels, qui
  doivent être connectés eux aussi. Les areas ne sont pas mergeables (un voltage level peut
  appartenir à plusieurs areas). Étage absent du dict = jeté.
- **`main_component_only`** : filtrer sur la composante synchrone principale — les îlots
  non résolus par le load flow polluent l'apprentissage (même logique de nettoyage pour
  les éléments `fictitious` de certains imports).
- **`extensions`** : les tables de `get_extensions(...)` sont des satellites au fetch près
  (indexées par l'id du porteur, une ligne par élément équipé) — donc la troisième option
  en dict de modes `merge`/`connect`, sur un registre curé qui déclare le split
  ports/features (les colonnes id ne deviennent jamais des features). Premier lot :
  `activePowerControl` (droop et facteurs de participation, mergé dans generators *et*
  batteries), `hvdcAngleDroopActivePowerControl`, `referencePriorities`,
  `voltageRegulation` (tension des batteries), `standbyAutomaton`,
  `coordinatedReactiveControl`, plus deux connect-only : `slackTerminal` (le bus slack d'un
  AC-PF, rempli par `write_slack_bus=True` — un surrogate doit le voir) et
  `secondaryVoltageControl` (relationnel : zones avec bus pilote et target_v, units
  générateur → zone, liées par l'adresse de zone). Attention aux espaces d'ids : le bus
  slack est un id de la vue bus, le bus pilote un id bus/breaker — chaque port bus déclare
  sa vue et est omis dans l'autre. Points ouverts : pilotes multi-bus (bus_ids séparés par
  virgules, non splittés) et merge du réglage secondaire vers les générateurs (chaîne
  unit → zone, faisable via le mécanisme `via` si besoin).

Le jeu est recouvrant au sens où les projets du §3 sont des combinaisons : contrôle de
tension = `regulation=True` + cibles `target_v`/`target_q` ; screening N-1 =
`features=("ac_pf_input", "ac_pf_output")` + `satellites={"operational_limits": "connect"}` ;
topologie = la vue node/breaker, à réintroduire dans `topology_view`.

Sous le capot, chaque combinaison se **résout en une spec explicite** (table → getter +
colonnes de ports + colonnes de features), qui reste le format pivot :

- **Sérialisable** : un dict de chaînes → dump YAML/JSON trivial, à versionner, hasher et
  stocker à côté des datasets dans
  [energnn-feature-store](https://github.com/energnn/energnn-feature-store) — datasets
  reproductibles et comparables. C'est l'argument décisif.
- **Amendable** avant instanciation (ajouter/retirer une colonne, une table), et
  **tolérante** : toutes les sources ne remplissent pas tout (pas de node/breaker en UCTE,
  pas d'extensions en Matpower) — table absente ou vide → classe d'éléments vide, et la
  validation à la construction (§4) dit explicitement ce qui manque.
- Les `ready_to_use` deviennent des **combinaisons d'options nommées**, et les ~30
  sous-classes de `elements.py` de simples alias — voire disparaissent à terme.

À garder en tête sans en faire des options : les **variantes** (boucler sur
`set_working_variant` pour générer états N-1 et tirages Monte-Carlo sans recharger le
réseau) et les **frontières CGMES** (dangling lines `paired`/`tie_line_id`, grandeurs
`boundary_*` — le traitement des frontières doit être fixé par la spec, pas par le format
d'import).

La sous-classe garde sa place pour ce que ni options ni spec n'expriment : features
dérivées, agrégats calculés, sources de données exogènes. C'est une minorité des usages, et
le mécanisme existe déjà.

**État** : implémenté dans le sous-package `parametric/`, découpé selon le flux de données —
`spec.py` (le pivot), `registry.py` (le déclaratif, dont `_TABLES`), `resolve.py` (options →
spec), `converter.py` (spec → graphe), dépendances strictement descendantes —
`topology_view` (bus_branch/bus_breaker), `features` (grille `{ac,dc}_pf_{input,output}`,
input/output cumulables par solveur), `per_unit` imposé, `regulation`, `satellites` et
`infrastructure` en dicts de modes `merge`/`connect` (jointures en chaîne comprises pour le
merge des substations),
`ports=False` pour les cibles, `extensions` (8 extensions curées, dont
`secondaryVoltageControl` multi-tables via `getter_args`), spec sérialisable
(`to_dict`/`from_spec`, amendable) et validation des colonnes avec message explicite (§4).
Restent la vue node/breaker (retirée des valeurs supportées) et `main_component_only`
(`NotImplementedError` explicite en attendant).

## 2. Le chemin retour : Graph → réseau

Le manque le plus structurant pour les usages réels (contrôle de tension notamment) : le
package sait extraire, mais pas **réinjecter les prédictions dans le réseau**
(`update_generators`, `update_shunt_compensators`, ...). Deux prérequis :

- **Garder la correspondance `adresse entière ↔ id pypowsybl`** : aujourd'hui `_str_to_int`
  (côté energnn) la construit puis la jette. Il faudrait que le `Converter` amont l'expose ou
  la retourne en option — petit chantier côté energnn, mais c'est ce package qui en a besoin.
  Chantier cousin : des **ports optionnels** dans la structure H2MG (adresse -1 + masque)
  pour les points de connexion inexistants (`bus_id` vide d'un élément déconnecté, ...).
  En attendant, ce package re-route chaque port vide vers une adresse sentinelle isolée
  (`_isolate_dangling_ports`) pour éviter qu'un nœud fantôme `''` ne connecte entre eux
  tous les objets déconnectés.
- Un **`OutputWriter`** symétrique du convertisseur de sortie : même spec (table, colonnes),
  direction inverse.

Sans ça, EnerGNN prédit des grandeurs qu'on ne peut pas rebrancher sur l'outil métier, ce qui
limite le package à l'entraînement.

## 3. Ready-to-use : suivre les projets, pas les multiplier

Ne pas pré-fabriquer des convertisseurs spéculatifs. Les candidats naturels vus des projets en
cours :

- **Contrôle de tension** : entrées avec données de régulation, sorties `target_v` / `target_q`.
- **Screening de contingences** : états N-1.
- **Topologie** : vue node/breaker (switches + busbar sections) pour l'optimisation de
  topologie.

La bonne mécanique : chaque projet définit sa spec via la classe paramétrable, et on
« promeut » dans `ready_to_use` celles qui ont fait leurs preuves.

## 4. Chantiers d'hygiène

Dans l'ordre :

- **CI GitHub Actions** (pytest + black + flake8) : les PR n'ont aujourd'hui que le check DCO,
  les 28 tests ne tournent que localement.
- **Messages d'erreur** : une colonne inconnue produit un `KeyError` pandas cryptique au fond
  de pypowsybl. Une validation à la construction — « `foo` n'existe pas dans `get_lines`,
  colonnes disponibles : ... » — coûterait peu et changerait la vie.
- **`per_unit`** : les tests le positionnent à la main ; un oubli produit des graphes
  silencieusement faux. Le convertisseur devrait l'imposer, ou au moins le vérifier.
- **Docs Sphinx** : le groupe de dépendances `docs` existe déjà dans `pyproject.toml`, mais
  `docs/` ne contient qu'un notebook de démo.
- **Release 0.2.0 sur PyPI** une fois energnn 0.4 publié (la dépendance pointe actuellement
  sur une branche git, voir `[tool.uv.sources]`).

## Ordre de bataille proposé

1. La classe paramétrable d'abord : petite, elle simplifie tout le reste.
2. Le mapping id ↔ adresse et le chemin retour ensuite : c'est ce qui débloque les usages en
   boucle fermée.
3. La CI en parallèle.