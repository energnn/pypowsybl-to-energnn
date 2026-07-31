# Feuille de route

État des lieux et prochains chantiers envisagés pour ce package, dans l'ordre de priorité
proposé. Contexte : depuis la migration vers `energnn.converter` (PR #5), les ABC `Converter`
et `ElementsConverter` vivent dans energnn, et ce package ne fournit plus que la partie
PyPowSyBl — des convertisseurs d'éléments réduits à un getter pypowsybl + deux listes de
colonnes (ports et features).

## 1. Des configs explicites plutôt qu'un moteur d'options

Le chantier a d'abord été mené sous forme d'un convertisseur paramétré par options
(`topology_view`, grille de features solveur × rôle, dicts de modes `merge`/`connect` pour
satellites, infrastructure et extensions), résolues contre un registre déclaratif en une
spec par table. Design **abandonné après revue** : trop implicite — comprendre ce qu'une
combinaison d'options produit demandait d'exécuter de tête le moteur de résolution —,
difficile à modifier à la marge (retirer une colonne d'une seule table n'était pas
exprimable en options), et surtout **fermé par construction** : tout ce que le moteur
pouvait produire devait être énuméré d'avance dans le registre, et une table hors pypowsybl
(coûts, mesures, features calculées ailleurs) ne pouvait entrer qu'en modifiant la
librairie. Le détail vit dans l'historique de la branche `parametric-converter`.

Une première version « configs explicites » (un `TableConverter` générique + des dicts de
listes de colonnes) a ensuite été re-travaillée (2026-07-31) : le savoir métier vivait dans
des dicts de configuration, peu navigables pour le public visé (stagiaires/doctorants). Le
design retenu le déplace dans **une classe par type d'objet pypowsybl**, un module par
classe (`elements/lines.py`, `elements/generators.py`, ...), en assumant la verbosité :

- **Chaque classe porte ses défauts** — ports et features du problème AC, lisibles dans sa
  signature — et implémente la conversion en pandas explicite dans sa méthode
  `build_table`, l'unique point d'extension. La plomberie commune (split ports/features,
  validation des colonnes avec message explicite, isolation des ports pendants
  `isolate_dangling_ports` — `''` et NaN re-routés vers des adresses sentinelles
  déterministes) vit dans la base `PypowsyblElements`.
- **Chaque table jointe a son paramètre `<table>_features`**, symétrique de `features` :
  la liste des colonnes à ramener (`None` = pas jointe), préfixées du nom de la table dans
  le graphe (`ratio_tap_changer_tap`, `active_power_control_droop`, ... — pas de collision
  possible, `rho` existe des deux côtés). Concernés : régleurs et limites opérationnelles
  des branches (`selected_permanent_current_limits` : agrégation des limites permanentes
  sélectionnées de type CURRENT, une colonne par côté), extensions `activePowerControl`
  (Generators) et `standbyAutomaton` (StaticVarCompensators). Le réglage secondaire de
  tension n'est pas un satellite mais une structure à part entière : deux classes dédiées
  `SecondaryVoltageControlZones`/`Units` (pilotes multi-bus éclatés une hyper-arête par
  (zone, pilote), ids bus/breaker traduits en vue bus, adresse de zone partagée ;
  raccorder les units aux générateurs demande `Generators(ports=("id", ...))`).
- **Une config = un dict** `{classe: elements converter}`, assemblé par
  `PypowsyblConverter` (qui impose aussi `per_unit`). Override = copier le dict et
  remplacer ou ajouter des entrées. Les configs `ready_to_use`
  (`AC_LOAD_FLOW_INPUT`/`OUTPUT`, restrictions actives `DC_*` — invariant dc ⊆ ac testé)
  deviennent triviales : l'entrée AC est chaque classe avec ses défauts.
- **`TableConverter` reste l'échappatoire ouverte** : nom de getter pypowsybl ou callable
  recevant les kwargs de l'appel de conversion (`network=...` compris) — features
  dérivées, vue bus/breaker (démontrée dans les tests), sources exogènes raccordées au
  graphe par leurs ids pypowsybl.

**État** : implémenté (`elements/`, `converter.py`, `ready_to_use/`), à graphes produits
strictement identiques à la version précédente sur les configs ready-to-use. Restent la
vue node/breaker (pas de table globale dans pypowsybl, assemblage poste par poste à
re-namespacer) et le filtrage sur la composante synchrone principale, en chantiers futurs.

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
  (`isolate_dangling_ports`) pour éviter qu'un nœud fantôme `''` ne connecte entre eux
  tous les objets déconnectés.
- Un **`OutputWriter`** symétrique du convertisseur de sortie : même config (table,
  colonnes), direction inverse.

Sans ça, EnerGNN prédit des grandeurs qu'on ne peut pas rebrancher sur l'outil métier, ce qui
limite le package à l'entraînement.

## 3. Ready-to-use : suivre les projets, pas les multiplier

Ne pas pré-fabriquer des convertisseurs spéculatifs. Les candidats naturels vus des projets en
cours :

- **Contrôle de tension** : entrées avec données de régulation, sorties `target_v` / `target_q`.
- **Screening de contingences** : états N-1.
- **Topologie** : vue node/breaker (switches + busbar sections) pour l'optimisation de
  topologie.

La bonne mécanique : chaque projet écrit sa config explicite (un dict de `TableConverter`),
et on « promeut » dans `ready_to_use` celles qui ont fait leurs preuves.

## 4. Chantiers d'hygiène

Dans l'ordre :

- ~~**CI GitHub Actions**~~ : fait — black, flake8, mypy et pytest tournent sur chaque PR.
- ~~**Messages d'erreur**~~ : fait — `TableConverter` valide les colonnes à l'extraction
  (« Columns `['foo']` not found in `'get_lines'`; available: ... »).
- ~~**`per_unit`**~~ : fait — `PypowsyblConverter` le pose sur le réseau avant extraction.
- **Docs Sphinx** : le groupe de dépendances `docs` existe déjà dans `pyproject.toml`, mais
  `docs/` ne contient qu'un notebook de démo.
- **Release 0.2.0 sur PyPI** une fois energnn 0.4 publié (la dépendance pointe actuellement
  sur une branche git, voir `[tool.uv.sources]`).

## Ordre de bataille proposé

1. ~~Le socle de conversion d'abord~~ : fait (`TableConverter` + configs explicites, §1).
2. Le mapping id ↔ adresse et le chemin retour ensuite : c'est ce qui débloque les usages en
   boucle fermée.
3. ~~La CI en parallèle.~~ Fait.