# H26 — contrat dormant d'autorité de matérialisation

## Correction de liaison de la preuve d'exécution runtime

La correction est autorisée uniquement sous le token :

```text
AUTHORIZED_TO_CORRECT_H26_DORMANT_POPULATION_MATERIALIZATION_AUTHORITY_RUNTIME_EXECUTION_PROOF_BINDING_ONLY
```

Son parent exact est :

```text
b1b13048efeb73b468cb7fbb0f1ccff4c00ff0d0
```

Elle ferme un défaut purement contractuel : le SHA d'un runtime record qualifié
ne suffit pas, à lui seul, à prouver que ce record provient de l'unique
invocation autorisée et consommée. Une future autorité de matérialisation doit
désormais lier et faire valider toute la chaîne :

```text
runtime execution authority
→ unique consumed claim
→ observer-entry evidence
→ terminal receipt
→ exact QUALIFIED runtime record
```

La pile de validation dormante approuvée est scellée par :

```text
execution authority contract             e0e070b8b75e85fb8ef78c7d6950a13f2c69ceae
execution authority contract blob        5ab6ff43980c0dc0f32308d3f8cee14a90351ec7
execution authority contract raw SHA     c7f6da697d74f710b957ab7ad32bef0fc184bb4f16ffaef16d2e2e1abafc63f9
runtime qualification contract           89cc0659de3afb5194afcf8e7ea9ac6c300e1f92
runtime qualification contract blob      c3a021872dfd3a99b6977fdef1302d5edc755fea
runtime qualification contract raw SHA   eec08691f12f673f86ed3839379865cbe6087e974a6745b1a4ef6cecea839736
runtime qualifier                         25a08630d6ad99d5e3432a277b99b9603990458a
runtime qualifier blob                    ef24d9ebdc4ae834b3b872175fb7e098330a68bf
authority/claim/evidence validators       10d3ee0525790279bce299492d89cec4002ab931
authority/claim/evidence validators blob  1c1777ad7c4493e66674d1daf63508778874df04
terminal receipt validator                09ef74cd537392d76eab1ed09082bf04e0214f16
terminal receipt validator blob           9721a41eca9e3f2bfa1ef8150ff39bf34ccf5fce
review closure                            b1b13048efeb73b468cb7fbb0f1ccff4c00ff0d0
review closure report blob                f26262b28e9d00e5d5c270461dd72c04e16bbaf9
```

Les champs futurs obligatoires incluent maintenant les identités et SHA bruts
exacts de l'authority, du claim consommé et de la preuve d'entrée observer,
ainsi que le SHA brut du receipt, son statut terminal et le SHA du record.
Le receipt doit imposer :

```text
terminal_status = H26_MATERIALIZATION_RUNTIME_QUALIFIED
runtime_record_exists = true
observer_entered = true
observer_invocation_count = 1
claim_consumed = true
retry_allowed = false
receipt.runtime_record_raw_sha256 = qualified_runtime_record_sha256
```

Un statut disqualified ou inconclusive-consumed, un échec pré-observer, un
receipt sans record, un record sans receipt, un receipt sans le claim exact ou
un simple SHA de record ne peuvent jamais permettre l'émission d'une autorité
de matérialisation.

Cette correction ne crée aucun des objets cités. Toutes les valeurs courantes
restent `null` et toutes les frontières opérationnelles restent `false`.

## Portée

Le contrat initial avait été autorisé sous le token historique :

```text
AUTHORIZED_TO_DEFINE_AND_COMMIT_H26_DORMANT_POPULATION_MATERIALIZATION_AUTHORITY_CONTRACT_ONLY
```

Il ajoutait un contrat déclaratif décrivant les conditions d'une éventuelle
future autorité de matérialisation. Il n'implémentait, n'émettait et ne consommait
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

Après la première revue externe, les contraintes de l'authority future fixent
structurellement `authority_schema_version=1`, les trois SHA scientifiques,
le blob exact du materializer, `single_use=true`, `retry_allowed=false`, le
namespace et schéma de population ainsi que `execution_authorized=true` pour
une authority effective future. Ce dernier champ n'active rien aujourd'hui :
`current_execution_authorized` et les onze frontières restent `false`.

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

Le SHA de l'authority n'est pas auto-référentiel. L'authority future ne doit
jamais contenir son propre SHA. Un artefact externe séparé
`H26_EXTERNAL_AUTHORITY_SEAL_V1` devra lier le SHA brut de l'authority, le SHA
brut de ce contrat et le commit approuvé qui contient ce contrat. Le seal ne
contient pas non plus son propre SHA ; celui-ci pourra seulement être calculé
extérieurement après sa création. Aucun fixed-point ou convention implicite
n'est admis, et aucun seal n'est créé ici.

Le SHA runtime futur n'a aucune valeur présente : il devra être exactement
celui du record lié par le receipt terminal de la chaîne complète validée,
avec statut `H26_MATERIALIZATION_RUNTIME_QUALIFIED`, sans placeholder,
wildcard ou fallback. Le record seul reste explicitement insuffisant. La
destination future devra être absolue, non vide,
unique, liée avant le claim et immuable après celui-ci ; destination et staging
devront être absents avant invocation, sans suffixe de repli automatique.

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

La correction a été contrôlée uniquement par la bibliothèque standard et Git :

```text
parent exact                         b1b13048efeb73b468cb7fbb0f1ccff4c00ff0d0
JSON strict                          OK, clés dupliquées et non-finis refusés
SHA scientifiques historiques        3/3 inchangés
blobs d'implémentation historiques   5/5 inchangés
objets commit/blob de la pile        9/9 présents avec le type Git attendu
frontières d'autorisation            11/11 false
champs runtime courants              tous null
fichiers modifiés                    exactement 3
git diff --check                     OK
```

Aucun test H26 n'a été lancé et aucun module H26 n'a été importé.

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
