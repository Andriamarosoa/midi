# H23 — contrat pré-train du censoring harmonique multiscale

## Portée

H23 transforme le brainstorming sur la « dilution par pitch » en un protocole
falsifiable avant entraînement. Il ne contient aucune implémentation
scientifique et n'autorise aucun calcul, accès à des données réelles, modèle,
fit, calibration ou test verrouillé.

Le résultat H17 reste clos et sa population de `146` prises / `51` groupes
reste définitivement consommée. Elle ne peut pas être réutilisée par H23.

## Idée testée

La version retenue n'exécute pas des dizaines de transpositions. Elle calcule
une représentation spectrale causale partagée, puis applique des masques de
censoring relatifs à chaque hypothèse F0 :

```text
une fenêtre causale 4096
        ↓
une représentation spectrale/log-fréquence
        ↓
matrice pitch × niveau de censoring
        ↓
S_raw, S_norm, S_null, S_residual
```

Le MVP/live est limité à `4–6` cutoffs. Un éventuel teacher offline pourrait
utiliser `16–32` cutoffs, mais seulement après démonstration synthétique qu'il
contient une information absente du MVP. `[k90,k50,k10]` et les autres
statistiques sont des résumés secondaires, jamais le signal principal.

## Questions falsifiables

H23 demande d'abord :

1. reste-t-il une information structurelle après retrait de la géométrie
   pitch/cutoff et du gain global ?
2. cette information permet-elle de distinguer causalement une nouvelle source
   d'une ancienne résonance ?
3. une factorisation globale `K` contre `K+1`, autorisant le partage des
   partiels, explique-t-elle les mélanges sans imposer un propriétaire unique ?
4. le système sait-il répondre `AMBIGUOUS` lorsqu'aucune observation ne peut
   distinguer deux explications physiques ?

Les trois canaux suivants doivent rester séparés : hypothèse F0, prédiction
harmonique conditionnelle et observation spectrale indépendante. La tête
harmonique ne peut jamais confirmer seule le F0 qui la conditionne.

## Domaine et causalité

- audio : `44 100 Hz` ;
- hop : `256` échantillons ;
- fenêtre : `4096` échantillons ;
- lookahead ajouté : exactement `0` ;
- sortie MIDI physique : `40–76` ;
- observations analytiques : coordonnées `40–128` incluses, soit `89` points ;
- la coordonnée 128 n'est pas une note MIDI : elle couvre H20 de MIDI 76,
  situé à `127,863…` ;
- aucune observation virtuelle au-dessus de 76 ne peut émettre de MIDI.

Le graphe harmonique est orienté grave vers aigu. Une Do2 peut expliquer Do3
ou Do4 ; Do4 ne peut pas expliquer Do3 comme son harmonique. Les partiels
peuvent soutenir plusieurs hypothèses simultanément.

## Schéma anti-fuite

Toutes les features proviennent exclusivement de l'audio courant/passé dans
la fenêtre causale, des hypothèses de pitch et de l'état causal antérieur. Les
targets, références, labels, split, état post-décision et résultats H17 sont
interdits comme entrées. Une valeur manquante ou non supportée reçoit un masque
de validité ; elle ne devient jamais un négatif.

Le futur corpus synthétique devra conserver contrat, fixture, seed, paramètres
DSP, schéma de features, commit et les drapeaux :

```text
real_data_used=false
H17_population_used=false
locked_test_used=false
fit_performed=false
```

## P0 minimal — tuer rapidement l'idée si elle est mauvaise

### Analytique

`A01`, `A03–A07` vérifient la direction harmonique, la trivialité d'un indice
unique de disparition, l'impossibilité d'identifier deux waveforms identiques,
la séparation `K_pitch/K_source`, le domaine 40–127 et les cutoffs relatifs.

### DSP

`D01`, `D03–D05`, `D08` et `D11` vérifient la parité vectorisée, le null
géométrique, l'information au-delà du pitch et du gain, les bords de fenêtre
et l'insuffisance des seuls résumés.

### Fixtures

```text
S1C  Do2 conceptuelle + H2/H3/H4/H5 décroissants
S1P  analogue physiquement réalisable à partir de MIDI 40
S2   vraie Do4 et ses propres harmoniques, attaque à t0
S3   ancienne Do2 décroissante, rien de nouveau
S4   ancienne Do2 + nouvelle Do4 partageant H4/H1
S5   collision exacte sans indice indépendant
```

Chaque fixture produit baseline, six cutoffs, courbes brute, normalisée, null
et résiduelle. Les oracles catégoriels sont exacts : S1/S3 n'ont pas de birth,
S2/S4 exigent une nouvelle source, S5 doit produire `AMBIGUOUS`.

### Décisions P0

```text
CENSORING_NONTRIVIAL
SOURCE_BIRTH_SYNTHETICALLY_IDENTIFIABLE
NONIDENTIFIABLE_CASE_RESPECTED
```

Les deux premiers doivent valoir `yes`. Le troisième doit valoir `yes`, ce qui
implique `S5=AMBIGUOUS`. Toute dépendance au futur, fuite de label ou réussite
expliquée seulement par pitch/amplitude tue également l'idée.

## P1 complet — seulement si P0 passe

P1 ajoute :

- causalité, translation temporelle, âge de la résonance et retrigger ;
- phases, amplitudes, enveloppes, bruit, cents et inharmonicité ;
- octaves, quintes, accords, notes voisines et partiels partagés ;
- comparaison globale `K`/`K+1`, ordre candidat/graphe invariant ;
- anti-auto-confirmation et conservation des désaccords entre canaux ;
- bends, slides, vibrato, unisons physiques, harmoniques naturelles et
  résonance sympathique ;
- prior corde/frette uniquement souple avec `unknown/slack` ;
- silence, OOD synthétique, résidu inexpliqué et explication causale ;
- observation analytique 40–128 avec firewall MIDI 76.

Tous les tests sont identifiés dans le contrat JSON avec entrée, procédure,
oracle, règle PASS et inverse check. Le résolveur du schéma ajoute à chaque
entrée les métriques, la règle FAIL, les artefacts atomiques et le drawback
commun, sauf surcharge plus précise du test. Une entrée résolue incomplète est
invalide. Aucun seuil statistique arbitraire n'est inventé : les synthèses
demandent une égalité exacte, une catégorie exacte ou une direction
préenregistrée.

## P2 — viabilité live, seulement après P1

P2 vérifie déterminisme, parité batch/scalar, un seul encodeur spectral,
vectorisation des masques, mémoire bornée, absence de backlog durable,
décomposition de latence et lookahead nul. Le budget numérique de débit devra
être scellé avant son exécution et ne pourra pas être assoupli après résultat.

Le teacher `16–32` cutoffs est abandonné s'il ne démontre pas une information
synthétique précise absente de `4–6` cutoffs. Aucun student n'est entraîné dans
H23.

## Publication future

Chaque phase écrira d'abord sous `.staging`, vérifiera ses fichiers et leurs
SHA-256, puis effectuera un renommage atomique. Aucun rapport partiel ne sera
autoritatif. Le contrat exige les manifests, rapports JSON, WAV synthétiques,
features et plots diagnostiques listés dans le JSON H23.

## Risques restant impossibles à supprimer

Même un succès complet ne résout pas une superposition exactement identique,
un fondamental absent à explications multiples, le nombre de sources physiques
d'un unison indiscernable, une information non encore présente dans 4096
échantillons, ni le passage synthétique vers la vraie guitare. Il ne valide
pas davantage l'OOD réel ou la calibration.

## Verdict et prochaine action

Le seul statut positif futur est :

```text
AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL
```

et explicitement jamais :

```text
TRAIN_AUTHORIZED
```

La prochaine action est uniquement la revue externe du contrat H23. Aucune
implémentation ou exécution de P0 ne suit automatiquement ce commit.

## Validation structurelle locale

- parsing JSON réussi ;
- `72` IDs de tests, tous uniques ;
- neuf familles P0/P1/P2 présentes ;
- six fixtures `S1C`, `S1P`, `S2`, `S3`, `S4`, `S5` présentes ;
- tous les drapeaux d'exécution, données, fit, H17 et test verrouillé sont à
  `false` ;
- `git diff --check` réussi ;
- aucun fichier sous `src/`, `tests/`, `data/`, `artifacts/` ou `tmp/` modifié.
