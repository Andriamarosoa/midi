# H27 — contrat d'apport ODB-only des huit blobs exacts

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Autorisation amont : PASS de `0c3a90776c48f3edd5a05f98653e253084637d4d`

## Portée

Contrat déclaratif, external seal, test déterministe et documentation
uniquement. Aucun apport de blob, accès Mac, ACK, runner, detach, registre,
autorité, creator, bundle, materializer, science ou locked test.

## Identités

```text
contract blob  7f5905f0d2b24eb96a6e1f1555dbe3993e85adbd
contract size  8149
contract sha   8e4a00fdba0d7e56c0d77e66f141a914de5c29d08cff914ba2ff53ff7d39d420

seal blob      8cfdaba605115f43fffb66fc28161bd85e8cada9
seal size      6054
seal sha       745d80d1d163e67b68efb2dae1d4b337e068e4909d40718000848916eaff9573
```

Le contrat lie les huit payloads par chemin, blob SHA-1 Git, taille et SHA-256
brut. Les huit chemins et les huit IDs doivent être uniques.

La première revue externe du commit `3793e7d6...` rend `FAIL` uniquement parce
que l'interdiction de modifier les refs n'était pas accompagnée d'une preuve
avant/après. La correction courante ajoute cette capture et les deux
comparaisons byte-exactes dans le contrat, le seal, le test et la documentation,
sans ajouter d'implémentation ni d'effet Mac.

La seconde revue externe de `883a67ab...` confirme cette comparaison pour les
refs régulières mais rend `FAIL` parce que `for-each-ref` omet les root refs et
pseudorefs sans option dépendante de la version Git. La correction courante
conserve la commande portable des refs régulières et ajoute un scan stdlib
déterministe des fichiers racine Git aux noms majuscules, sans accès Mac.

La troisième revue externe de `dda47ec4...` confirme cette couverture avec le
backend `files`, mais rend `FAIL` car ce backend n'était pas lui-même imposé.
Le premier scellement utilisait `rev-parse --show-ref-format` et a reçu `PASS`
au commit `dffce1f9...`. Le préflight Mac a ensuite démontré qu'Apple Git
`2.39.5` renvoie littéralement l'option inconnue au lieu de `files`. La
micro-correction déclarative compatible 2.39.5 exige désormais conjointement :

```text
git --no-optional-locks --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  config --local --get core.repositoryFormatVersion

stdout exact: 0

git --no-optional-locks --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  config --local --get extensions.refStorage

returncode exact: 1
stdout/stderr exacts: vides
```

Le répertoire `.git/refs` doit en plus être réel, non-symlink, et `.git/reftable`
doit être absent. Cette preuve composite est répétée avant snapshot, juste
avant le premier effet futur et après les huit écritures. Tout repository
format étendu ou `extensions.refStorage`, ainsi que tout répertoire reftable,
échoue fermé. Le second blocage préflight, les treize objets absents de l'ODB
source, reste volontairement inchangé.

## Frontière future préenregistrée

Avant la première écriture future, l'exécuteur devra :

1. vérifier Darwin, l'ACK dédié, zéro argument, checkout/ODB réels ;
2. vérifier HEAD, symbolic HEAD, worktree propre, absence de lock/processus et
   capturer l'identité byte-exacte de l'index ainsi qu'un snapshot déterministe
   byte-exact des refs régulières triées par nom ainsi que de toutes les root
   refs/pseudorefs présentes dans `.git` ;
3. recevoir hors du checkout cible exactement huit payloads et tous les garder
   en mémoire, sans staging fichier ;
4. valider les huit triples d'identité et leur hash Git sans `-w` ;
5. revalider l'état initial, le même snapshot de refs et l'index, puis exiger
   les huit blobs absents ;
6. écrire une seule fois chaque blob dans l'ordre déclaré avec :

```text
git --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  hash-object -w --stdin
```

Chaque retour doit être l'ID attendu. Ensuite, les huit blobs, HEAD, symbolic
HEAD, snapshots byte-identiques des refs régulières et root refs/pseudorefs,
index byte-identique,
worktree, lock, ACK runner et downstream flags doivent être revalidés.

Le snapshot futur des refs régulières est défini exactement par :

```text
git --no-optional-locks --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  for-each-ref --sort=refname \
  --format=%(refname)%00%(objectname)%00%(objecttype)%00
```

En complément, l'exécuteur futur utilise `os.scandir` stdlib sur la racine ODB,
sélectionne tous les noms correspondant à `^[A-Z][A-Z0-9_]*$`, refuse symlinks
et entrées non régulières, trie les noms par octets UTF-8, puis conserve nom,
présence et octets bruts de chaque fichier. Cela couvre `HEAD` et toutes les
root refs/pseudorefs majuscules présentes, sans dépendre de
`--include-root-refs`. Les deux snapshots restent en mémoire ; taille et
SHA-256 sont également archivés. L'égalité exacte est requise avant et après
l'effet.

Fetch, pull, sync, update-ref, checkout, switch, detach, fallback worktree,
payload supplémentaire, retry, cleanup, réparation ou récupération automatique
sont interdits. Un import partiel futur serait un échec terminal consommé, sans
revendication de rollback.

## Validation locale

- `py_compile` : réussi ;
- tests ciblés contrat + importer stale : `10/10` réussis en `0,210 s` ;
- suite H27 complète : `524/524` réussis en `93,484 s` ;
- `git diff --check` : réussi avant commit.

## STOP

Le contrat corrigé reste dormant et non approuvé. Son changement d'identité
rend volontairement stale le binding de l'importer existant, qui reste lié aux
anciennes identités `42eebb25...` / `40020155...` et ne doit pas être exécuté.
Prochaine action unique : revue externe du contrat et du seal corrigés. Aucun
apport réel ni correction du runner/binding n'est autorisé par ce lot.
