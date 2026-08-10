# H8 — préparation scellée de la cohorte age-1 persistence

## Statut

```text
provisional_resolution_age1_persistence_h8_preparation_sealed
```

Cette étape est exclusivement une préparation de provenance et de paramètres.
Elle n'implémente ni extracteur de cible, ni extracteur de signal, et n'exécute
aucun calcul scientifique.

## Prérequis H7

- commit : `e3e2be144282ecf0079ba22831abfb6439b16ac3` ;
- contrat H7 SHA-256 :
  `2b03305444506430fc0458430730fd4f4bc04ca50b21b1fe321b9985ceaae296`.

Le SHA brut a été vérifié avant la sélection H8.

## Sélection déterministe

La seule source de partition est le plan Policy A persistant :

```text
plan SHA-256 : a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4
partition    : dev
population   : toutes les prises éligibles après exclusion entière des groupes interdits
```

Il n'y a ni plafond, ni équilibrage, ni sous-échantillonnage, ni sélection
manuelle. Les groupes présents dans la cohorte V2 déjà consommée et dans le
test verrouillé sont interdits. La sélection obtenue est :

```text
Policy A dev avant exclusion : 102 prises
exclusion locked-test        :   1 prise / 1 groupe
exclusion cohorte V2         :   0 prise / 0 groupe
cohorte H8                   : 101 prises / 31 groupes
```

Répartition des 101 prises :

```text
GAPS                         27
Guitar-TECHS direct input     7
Guitar-TECHS mic amp          7
GuitarSet                    60
```

Les groupes par corpus valent respectivement `23`, `7`, `7` et `1`. Comme les
deux vues Guitar-TECHS d'une même capture partagent une clé de fuite, ces
comptes par corpus ne sont pas additionnables pour obtenir les `31` groupes
uniques. L'artefact explicite `9` relations multi-enregistrements partageant
une même clé de fuite.

Les intersections finales avec les groupes V2 et test verrouillé valent toutes
deux zéro. La seule prise `dev` retirée est
`gaps_poly_mix|Sc1wc|054_Sc1wc|gaps_mixed_downmix`, parce que son groupe
`gaps:player:sanja_plohl` apparaît dans le test verrouillé.

## Preuve d'actifs

Les 101 fichiers audio et les 101 fichiers de labels ont été lus comme octets
bruts, sans décodage ni parsing. Leur taille et leur SHA-256 ont été comparés au
registre Policy A historique :

```text
registre SHA-256 : 12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507
audio vérifiés   : 101/101
labels vérifiés  : 101/101
```

Le manifeste train/validation reste
`b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7`.
Le manifeste combiné, utilisé uniquement pour lire les identités de groupes du
split test, reste
`8334d66356cbea5d607da71d740fafaec37db6c0249694446da6d1b0a8f7fafa`.
Aucun audio ni label du test verrouillé n'a été ouvert.

L'artefact canonique est :

```text
configs/provisional_resolution_age1_persistence_h8_selected_cohort.json
112013 octets
SHA-256 4dd76bd13c33ccb3946bfdbcf6f575d4550fb0c5588095e23da3b6e3f84bce1f
```

Le contrat de préparation canonique fait `1892` octets et a le SHA-256
`9bbe2b5558b6b5764415619260a6aba1e3daf1d3c22ce185f3b00a336f8e1639`.

Chaque entrée contient l'identité stable, corpus, groupe de fuite, partition,
identités de chemins/membres, tailles et SHA-256 audio/labels, ainsi que les
identités du manifeste et du plan sources. Les chemins sont portables et
relatifs à la racine de données ; aucun chemin ne s'échappe de cette racine.

## Paramètres H8 figés mais non exécutés

```text
bootstrap group-safe          10000 réplicats
seed                          0x2b033054 = 721629268
réplicats valides minimum     9500
observations age=1 minimum    200
unité de rééchantillonnage    leakage_group_key
IC                            percentile bilatéral 95 % [2,5 ; 97,5]
```

Une réplication mono-classe ou avec AUC non finie sera invalide. Aucun minimum
de classe supplémentaire n'est ajouté au contrat H7.

## Interdictions conservées

Cette étape n'a importé ni TensorFlow ni modèle, n'a effectué aucune inférence,
aucun replay du décodeur, aucun décodage audio, aucun parsing de labels, aucune
extraction de cible/S0/S1/D1, aucun calcul d'AUC et aucun bootstrap. Elle
n'autorise toujours ni fit, calibration, validation, export, live ou test
verrouillé.

L'étape suivante requiert une revue externe avant toute implémentation H9 ou
exécution scientifique.
