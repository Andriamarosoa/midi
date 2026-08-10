# H24 — materializer de population dormant

Date : `2026-08-10`

## Autorisation

La revue externe a approuvé le contrat de matérialisation au commit
`2cf2be8e95a73f0648eda4b692c41deefce0418f` et a autorisé uniquement :

```text
AUTHORIZED_TO_IMPLEMENT_H24_DORMANT_MATERIALIZER_CLAIM_AND_ATOMIC_PUBLISHER_ONLY
```

Cette étape implémente la mécanique future, mais ne crée ni seal d'activation,
ni capability active, ni marker, ni waveform, ni population.

## Surface ajoutée

Le module dormant est :

```text
src/polyphonic/harmonic_censoring_h24_population_materializer.py
```

Il lie le contrat approuvé au SHA-256 :

```text
b48aa4f417a9857983c79809efe24137d6b82ad0984d20e906286477f05a14ca
```

Il contient :

- un validateur fermé pour un futur seal d'activation séparé ;
- une capability process-local avec exactement les 18 champs contractuels ;
- un registre d'identité par `id` + weakref, distinct de l'égalité objet ;
- le preflight sans import NumPy : hashes, blobs, HEAD, worktree, runtime,
  175 recettes et 175 seeds ;
- la primitive durable `O_CREAT|O_EXCL|O_WRONLY`, mode `0600`, fsync fichier
  et parent ;
- la trace exacte des sources, trajectoires, bruit et six OOD ;
- l'encodage `<f8`, les triples spec/target/waveform, l'index JSONL et le reçu ;
- relecture et rehash des 525 fichiers avant publication ;
- publication atomique staging → population et terminal atomique ;
- terminal négatif post-claim sans verdict scientifique.

## Séparation commit d'implémentation / activation

Le seal futur nommera le commit du materializer déjà relu et son blob source.
Un commit d'activation distinct pourra ensuite ajouter le seal. Son SHA sera
lié hors du JSON par la variable d'environnement :

```text
H24_POPULATION_MATERIALIZATION_AUTHORIZATION_COMMIT
```

Le checkout devra être exactement ce commit d'activation et les octets du seal
devront être ceux de ce commit. Cette séparation évite toute auto-référence Git
impossible où un fichier tenterait de contenir le SHA du commit qui le contient.

La capability conserve `implementation_commit` pour le commit materializer
revu. Le commit d'activation reste dans l'état privé attesté et est revérifié
immédiatement avant le futur `O_EXCL`.

## Dormance effective

Le module n'importe ni NumPy, ni TensorFlow, ni loader de données, ni évaluateur
scientifique. La factory échoue d'abord faute de seal/commit d'activation.

Le corps complet de synthèse/publication est privé et accepte un objet NumPy
uniquement après une capability durablement claimed. L'entrée publique reste
un garde dormant : même si le contrôle de claim était satisfait, elle refuse
le bridge runtime NumPy. Une future activation devra donc être revue et ajouter
explicitement ce bridge; rien ne l'active ici.

Le test du claim remplace l'écriture durable par un mock. Il vérifie les octets
du marker, mais aucun marker réel n'est créé. Les tests de dtype, shape,
finitude, byte count et rehash utilisent seulement des objets factices ou des
octets temporaires; aucune waveform scientifique n'est allouée.

## Tests adversariaux

Les tests couvrent notamment :

- absence d'import NumPy/TensorFlow et absence de CLI ;
- factory refusée avant plan lorsque l'activation manque ;
- NumPy déjà présent dans `sys.modules` refusé avant claim ;
- seal avec champ supplémentaire ou mauvais hash refusé ;
- construction, mutation, copie, deepcopy, pickle et clone `object.__new__`
  de capability refusés ;
- marker exact à 21 champs, produit seulement depuis les 18 autorités ;
- `FileExistsError` du futur `O_EXCL` sans enregistrement de claim ;
- publisher public refusé avant staging et sans appel NumPy ;
- mauvais dtype, shape, nonfini ou longueur d'octets refusé ;
- hash de fichier rouvert incorrect refusé ;
- présence statique de toutes les primitives numériques et atomiques scellées ;
- absence de sélection de chemins ou de population par l'appelant.

## Validation administrative

```text
158 tests H24/H23/H20 réussis en 2,130 s
py_compile réussi
git diff --check réussi
aucun seal d'activation créé
aucune capability active émise
aucun claim/marker réel créé
aucun import NumPy par le materializer
aucune waveform synthétisée
aucune population publiée
aucun P0/P1/P2, real data, H17, locked-test ou training
```

La prochaine action est uniquement la revue externe de cette implémentation
dormante. Toute activation, tout seal opérationnel et toute tentative one-shot
restent interdits.
