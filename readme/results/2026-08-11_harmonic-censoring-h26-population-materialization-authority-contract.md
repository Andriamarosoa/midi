# H26 — contrat dormant d'autorité de matérialisation

## Portée

Cette étape est autorisée uniquement sous le token :

```text
AUTHORIZED_TO_DEFINE_AND_COMMIT_H26_DORMANT_POPULATION_MATERIALIZATION_AUTHORITY_CONTRACT_ONLY
```

Elle ajoute un contrat déclaratif qui décrit les conditions d'une éventuelle
future autorité de matérialisation. Elle n'implémente, n'émet et ne consomme
aucune autorité, capability ou claim.

Le parent direct attendu est le commit de clôture documentaire approuvé :

```text
0044675695f25a6127c648e99bcd4126c50b9727
```

## Liaisons scellées

Le contrat lie les trois fichiers scientifiques existants par leur chemin et
SHA-256 brut :

```text
scientific preregistration  8ecbb1da33e67e78bb76a2b0364d0d5c1697414a711418a030aafb000943b583
fixture specifications      c8e66f7f9d200451559bf538af5b6dd0b0e7131e042588b6f13ec8655804fc28
test manifest               f64b55a4b5dc21da0e2dc4bf9deb712073af59f3d67fd6e3d7d019ce8037e073
```

Il lie également au commit revu `60b8d90b…` les cinq blobs Git de la pile :

```text
contract.py       bf454505ed6ccc7c9de059d8619fe0025fc07558
materializer.py   2991c69db8a8816d0261c1fb6bb4e339e9408c11
engine.py         729a989766fc05c9e5149877b3c3b9a68e141fcd
recomputer.py     2e7fc04c6e12234f39d7722ad156019511c5d63e
dormant tests     1bf43c4cea572d37ca0dc1a54513661710b95b04
```

Ces valeurs ont été recalculées localement sans importer ou exécuter le
materializer.

## Contrat futur, sans objet présent

Le JSON spécifie de façon fail-closed :

- les 40 identités baseline ordonnées et la dérivation cartésienne exacte des
  futurs records P2 depuis le manifest et les grilles scellés ;
- le schéma v2 de l'index, les types `<f8`/`u8`, les SHA obligatoires et les
  règles d'alternate des collisions A01-A06 ;
- une publication future uniquement par renommage atomique final, sans rendre
  un staging partiel consommable ;
- la liaison obligatoire d'une future authority au SHA brut de ce contrat, à
  son commit revu, au runtime qualifié, aux trois SHA scientifiques, aux blobs
  d'implémentation et à une destination absolue absente ;
- la consommation du claim avant l'unique invocation et l'interdiction de tout
  retry après consommation, succès ou échec ;
- les receipts futurs et les deux seuls statuts terminaux admissibles.

Aucun objet conforme au schéma futur n'est créé : pas d'`authority_id`, de
destination, de date d'émission, d'issuer, de signature, de seal, de secret ou
de variable d'environnement.

## Frontière actuelle

Les onze booléens de `authorization_boundary` sont explicitement `false` :

```text
authority issuer / authority             false / false
capability issuer / capability           false / false
materialization claim / authorization    false / false
materialization executed                 false
population / population index            false / false
p2 records                               false
scientific execution authorized          false
```

La qualification runtime reste un prérequis futur séparément autorisé et
revu. Aucun Python/NumPy scientifique, BLAS ou secondary runtime n'est lancé et
aucun runtime record n'est créé dans cette étape.

## Validation autorisée

Seuls des contrôles statiques et standard-library sont permis : parsing JSON
strict, refus des clés dupliquées et valeurs non finies, recalcul des trois
SHA-256 bruts, vérification Git des cinq blobs et deux commits, contrôle des
booléens à `false`, absence de valeurs réelles d'authority/claim/destination,
`git diff --check` et diff limité aux trois fichiers déclaratifs autorisés.

Les 29 tests H26 ne sont pas relancés. Aucun module de matérialisation n'est
importé ou exécuté.

## Interdictions maintenues

Cette étape n'autorise ni issuer, capability, authority, claim, seal,
destination réelle, matérialisation, waveform, index, record P2, population,
P0/P1/P2, secondary runtime, qualification scientifique, donnée réelle,
modèle, entraînement, calibration ou locked-test.

Même une future approbation de ce contrat ne constituerait pas une autorisation
de matérialisation. Une nouvelle portée séparée serait obligatoire.
