# H27 — préflight Mac lecture seule de la livraison exacte des treize blobs source

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Commit revu PASS : `ca9e91481aa129d5bc8af19a54a0b13b71c14e1c`

## Autorisation et portée

La revue externe autorisait uniquement un préflight strictement lecture seule
de l'ODB source `/Users/amcarene/midi/.git`, avant toute implémentation ou
exécution du receiver. Aucun ACK, transport de payload, `hash-object -w`,
import cible, detach, registre, bundle, matérialisation, science ou locked test
n'était autorisé.

Les commandes Git du préflight ont supprimé toutes les variables héritées
préfixées `GIT_`, puis réintroduit uniquement `GIT_TERMINAL_PROMPT=0` et
`GIT_NO_LAZY_FETCH=1`. Les sélecteurs de dépôt étaient littéraux et toutes les
lectures Git utilisaient `--no-optional-locks` et `--no-replace-objects`.

## État source vérifié

```text
platform             Darwin
git                  2.39.5 (Apple Git-154)
checkout realpath    /Users/amcarene/midi
source ODB realpath  /Users/amcarene/midi/.git
objects realpath     /Users/amcarene/midi/.git/objects
refs realpath        /Users/amcarene/midi/.git/refs
HEAD                 eaed599a5a051685288f1f71b3cb057db64392c2
symbolic HEAD        refs/heads/codex/independent-note-neural-v2
worktree             clean
repository format    0
extensions.refStorage absent (rc=1, stdout/stderr vides)
.git/reftable        absent
objects/info/alternates absent
index.lock           absent
processus H27/import/hash-object pertinent absent
```

Checkout, `.git`, `objects` et `refs` sont des chemins réels non symboliques.

Snapshots lecture seule :

```text
regular refs sha256  8e2cf40b6bf97d34c00c0649b68b7dc3492a73c1a399d4820e6ec93e41d3d4fc
index size           96409
index sha256         3e4338ff315cd2327c174ec38e41100d6f3422a9d3ae9c10bc61185588571112
object file count    189
```

Root refs/pseudorefs présentes :

```text
FETCH_HEAD 125 105c1d1efde9c6c143c69328f01d72ae8f26901376a2f3447427a22f4cf8d14c
HEAD        49 4560fdfefea5d5bfa81ecda627156750dab6821bfff1004d57b4a2d86cae3911
ORIG_HEAD   41 1851ed6c21b503d665f04b8d962ef84ae99b2d2f7128abe20d4f76da27deb7ed
```

## Résultat des treize identités

Les treize blobs exacts du contrat sont tous absents de l'ODB source :

```text
7f5905f0d2b24eb96a6e1f1555dbe3993e85adbd absent
8cfdaba605115f43fffb66fc28161bd85e8cada9 absent
4520d69b04eec017f90a6a1c717519e6a303538d absent
0bba45c130c9f83ace74a91d92e48d53525740e7 absent
68cdc76688cee5364b54a8febc6b2d9a46e0994e absent
d1cdf1562a814cef271d606da331e96565fcc79a absent
d03385d842ca11631ba690d0a4bb70448c84480e absent
e574ddbcccb8bac791d9719fbee3e7fd5db8a047 absent
a514aa0270926dca1d8402ac84078a50754d2f17 absent
0f6a64b7477bde24968200a81d389b03a4a6ced0 absent
11fff0962fc0951a0bb06605e233d34756a2f4d9 absent
24a8c14fddd52eca148f961a31c39abaa4de018f absent
bda7e1fae7379996563e73d8bbcf1b2d7a871aa0 absent
```

Le receiver futur échouerait donc fermé avant son premier effet. Aucun ACK n'a
été posé et aucune écriture ODB n'a été tentée.

## Écart transitoire du premier relevé

La première commande de relevé a redirigé le stderr de la lecture
`extensions.refStorage` vers le fichier temporaire
`/tmp/h27_ref_storage_err.$$`, puis l'a supprimé. Sa sortie globale a ensuite
été tronquée côté outil et ne pouvait pas servir de preuve complète.

Cette création puis suppression transitoire n'a touché ni checkout, ni ODB,
ni refs, ni index, ni payload, et le contrôle final confirme qu'aucun fichier
`/tmp/h27_ref_storage_err.*` ne subsiste. Elle contrevient néanmoins à la
formulation littérale « aucun fichier Mac créé/modifié/supprimé » du préflight
et est donc archivée sans la masquer.

Un second relevé compact a été exécuté exclusivement avec des pipes mémoire
`subprocess.PIPE`, sans fichier temporaire. Il a produit l'état complet ci-dessus.
Le premier filtre processus a signalé deux services macOS `mdworker` par faux
positif lexical ; un filtre limité aux noms H27, receiver et `hash-object -w`
a confirmé zéro processus pertinent.

## STOP

État :
`H27_EXTERNAL_SOURCE_ODB_THIRTEEN_DELIVERY_READ_ONLY_PREFLIGHT_BLOCKED_ALL_THIRTEEN_ABSENT_WITH_TRANSIENT_TMP_DEVIATION_PENDING_EXTERNAL_REVIEW_NO_DELIVERY`.

Le préflight s'arrête ici. Aucun receiver n'est implémenté, aucun mécanisme de
livraison n'est exécuté et aucune autorisation mutante n'est consommée.
Prochaine action unique : revue externe de cette preuve et de l'écart `/tmp`
avant toute implémentation du receiver ou nouvelle commande Mac.
