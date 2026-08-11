# H26 — contrat dormant authority, claim et receipt de qualification runtime

## Portée

Cette étape applique uniquement le token fermé :

```text
AUTHORIZED_TO_DEFINE_AND_COMMIT_H26_DORMANT_RUNTIME_QUALIFICATION_EXECUTION_AUTHORITY_CLAIM_AND_RECEIPT_CONTRACT_ONLY
```

Le parent direct attendu est
`25a08630d6ad99d5e3432a277b99b9603990458a`. Le changement est exclusivement
déclaratif : nouveau contrat JSON, présent rapport et résumé global. Aucun code,
test, observer, NumPy, BLAS, `otool`, runtime ou actif scientifique n'est
exécuté.

## Bindings figés

Le contrat lie exactement :

```text
contrat qualification runtime commit  89cc0659de3afb5194afcf8e7ea9ac6c300e1f92
contrat qualification runtime blob    c3a021872dfd3a99b6977fdef1302d5edc755fea
contrat qualification runtime SHA256  eec08691f12f673f86ed3839379865cbe6087e974a6745b1a4ef6cecea839736
qualificateur dormant commit           25a08630d6ad99d5e3432a277b99b9603990458a
qualificateur dormant blob             ef24d9ebdc4ae834b3b872175fb7e098330a68bf
contrat authority matérialisation      236a84b4eb928b102bc1548fb2b32d1bffda2e63
blob authority matérialisation         dd5bcbff325e74f74e7bde4d425a11ac84aa264d
rôle runtime                            H26_PRIMARY_MATERIALIZATION_RUNTIME
```

## Octets canoniques et identités dérivées

Authority, claim, entry-evidence et receipt utilisent une représentation
unique : UTF-8 sans BOM, clés JSON dupliquées interdites, aucun float/NaN/
Infinity, clés triées lexicographiquement, aucun espace hors chaînes,
séparateurs `,` et `:`, `ensure_ascii=true`, puis exactement un LF terminal.
Tout CR/CRLF est interdit. Le SHA brut est toujours le SHA-256 lowercase de ces
octets exacts. Un JSON sémantiquement équivalent mais non canonique est refusé,
jamais normalisé silencieusement en objet opérationnel.

L'échappement des chaînes est également unique. Guillemets et backslashes
emploient respectivement les deux octets `5c 22` et `5c 5c`. Backspace, tab,
LF, form-feed et CR utilisent obligatoirement les short escapes `b/t/n/f/r`;
les autres contrôles U+0000..U+001F utilisent `\u00xx` en hex lowercase. Le
solidus `/` et tout ASCII imprimable hors guillemet/backslash restent littéraux :
`\/` et `\u0041` sont donc refusés quand `/` et `A` sont les formes canoniques.

U+0080..U+FFFF hors surrogates utilise exactement `\u` suivi de quatre hex
lowercase. U+10000..U+10FFFF utilise l'unique paire UTF-16, high surrogate puis
low surrogate, chacun sous cette forme. Un surrogate isolé est interdit. Le tri
des clés porte toujours sur les chaînes logiques non échappées, par code point.
Une orthographe d'échappement entrante non canonique est refusée, jamais
réécrite.

L'`authority_id` futur reste produit par un issuer séparément autorisé, mais il
devra être une chaîne ASCII non vide, sans whitespace initial/final et immuable.
Seul le SHA de ses octets authority canoniques peut dériver le claim.

Le `claim_id` est figé par :

```text
digest = SHA256(
  ASCII("H26_RUNTIME_QUALIFICATION_CLAIM_ID_V1") || 0x00 ||
  UTF8(authority_id) || 0x00 || ASCII(authority_raw_sha256)
)
claim_id = "h26-runtime-claim-v1-" + lowercase_hex(digest)
claim_slot_identity = claim_id
```

L'`observer_entry_evidence_id` est figé par :

```text
digest = SHA256(
  ASCII("H26_RUNTIME_QUALIFICATION_OBSERVER_ENTRY_ID_V1") || 0x00 ||
  UTF8(authority_id) || 0x00 || ASCII(authority_raw_sha256) || 0x00 ||
  UTF8(claim_id) || 0x00 || ASCII(claim_raw_sha256)
)
observer_entry_evidence_id = "h26-runtime-entry-v1-" + lowercase_hex(digest)
entry_slot_identity = observer_entry_evidence_id
```

Aucun UUID, random, choix caller ou algorithme alternatif n'est permis. Les
racines filesystem réelles des deux slots restent `null` et nécessiteront une
autorisation future. Claim, evidence et receipt ont chacun pour SHA externe le
SHA-256 de leurs propres octets canoniques et ne contiennent jamais ce SHA.

## Chaîne future distincte

Le contrat définit quatre artefacts distincts et ordonnés :

```text
future runtime qualification authority
        ↓
single-use qualification claim consommé
        ↓
exactement un observe_primary_runtime
        ├── runtime qualification record existant, inchangé
        └── terminal execution receipt externe
```

L'authority future devra lier le contrat d'exécution approuvé, le contrat
runtime, le qualificateur exact, le contrat d'authority de matérialisation et
le rôle primaire. Elle sera single-use, limitée à une invocation et sans retry.
Elle ne contient pas son propre SHA ; celui-ci sera calculé extérieurement.
Sa liste `required_fields` est l'ensemble exact des clés autorisées; tout champ
supplémentaire est interdit. La même fermeture canonique s'applique au claim et
au receipt afin que leurs SHA externes identifient des objets non ambigus.

`single-use` signifie structurellement un seul claim total par authority. Le
slot du claim sera dérivé uniquement de `authority_id` et de son SHA brut
externe, puis créé en create-exclusive atomique. La première tentative de
création consomme l'authority, même si le marker est partiel ou corrompu. Un
autre `claim_id`, chemin ou processus ne peut ouvrir un second slot; aucun
delete, replace ou retry n'est admis.

Les champs `execution_authority_contract_commit` et
`execution_authority_contract_raw_sha256` du claim doivent être strictement
hérités des champs correspondants de l'authority consommée. Ils ne peuvent être
ni choisis indépendamment par l'appelant, ni remplacés par un wildcard ou un
fallback.

Le claim futur devra lier l'identité et le SHA externe exacts de cette
authority, ainsi que les commits, blobs et SHA du contrat runtime et du
qualificateur. Il sera créé durablement et consommé avant l'observer. Son
existence signifie consommation, même après `QUALIFIED`, `DISQUALIFIED`,
`INCONCLUSIVE`, exception ou fichier partiel. Il ne pourra être supprimé,
remplacé ou réutilisé.

La consommation du claim ne prouve pas à elle seule que l'observer a démarré.
Une preuve d'entrée distincte ne pourra être créée que depuis l'intérieur de
la frontière d'entrée de `observe_primary_runtime`, en liant la même authority,
le même claim et le qualificateur exact. Elle ne pourra jamais être fournie par
l'appelant ou précréée.

Cette preuve possède un schéma canonique à dix champs exacts : identity/version,
`observer_entry_evidence_id`, identity/SHA de l'authority, identity/SHA du
claim, commit/blob du qualificateur et ordinal `1`. Les authority et claim
doivent être exactement ceux déjà consommés. L'identifiant et le slot sont
dérivés uniquement de leurs quatre valeurs identity/SHA, jamais choisis par
l'appelant. Il existe au maximum une preuve par claim, créée en create-exclusive
à l'intérieur de l'entrée observer. Une tentative partielle ou corrompue
consomme le slot; aucun autre ID, chemin, processus, delete, replace ou retry ne
peut produire une seconde preuve.

## Receipt terminal

Le schéma futur `H26_RUNTIME_QUALIFICATION_EXECUTION_RECEIPT_V1` lie notamment :

- identité et SHA brut externe du claim ;
- identité et SHA brut externe de l'authority ;
- commit/blob du qualificateur ;
- commit et SHA brut du contrat runtime ;
- identité et SHA externe de la preuve réelle d'entrée observer ;
- existence et SHA brut du runtime record ;
- statut terminal ;
- `observer_invocation_count=1` ;
- `claim_consumed=true` ;
- `retry_allowed=false`.

Lorsqu'un record a été publié atomiquement, son SHA est obligatoire et le
statut du receipt doit être celui redérivé depuis ce record. Si une exception
post-claim empêche toute publication atomique du record, l'absence est liée
explicitement par `runtime_record_exists=false` et SHA `null`, avec terminal
`H26_MATERIALIZATION_RUNTIME_QUALIFICATION_INCONCLUSIVE_CONSUMED`. Ce receipt
n'est possible que si la preuve d'entrée interne existe réellement.
Son `observer_entry_evidence_id` et son SHA brut doivent correspondre exactement
à cette unique preuve canonique et aux mêmes authority/claim; toute identité,
empreinte ou liaison alternative est refusée.

Si l'authority et le claim sont consommés mais qu'une panne survient avant
l'entrée de l'observer, aucun runtime record et aucun execution receipt
affirmant une invocation ne peuvent être produits. Le claim durable reste la
preuve terminale de l'échec administratif, authority et claim restent
consommés, et aucun retry n'est possible.

Un record artificiel, isolé de l'authority, du claim consommé et du receipt de
la même invocation, ne constitue donc jamais une preuve d'exécution autorisée.

## Non-récursivité

Authority, claim et receipt ne contiennent jamais leur propre SHA. Les SHA des
objets antérieurs sont calculés extérieurement puis liés seulement par les
objets ultérieurs. Aucun fixed-point n'est demandé. Un éventuel seal externe
nécessitera une autorisation future séparée.

## Conséquence pour la matérialisation

Le seul `qualified_runtime_record_sha256` ne suffira pas à émettre une future
authority de matérialisation. Une preuve approuvée reliant ce record à
l'unique claim et invocation autorisés sera également obligatoire. Le contrat
d'authority de matérialisation actuel ne porte pas encore cette liaison : sa
correction future nécessitera une autorisation et une revue séparées. Elle
n'est pas effectuée ici.

## Frontière actuelle

Tous les états authority/claim/entrée observer/exécution/record/receipt/
matérialisation/science restent `false`, et tous les identifiants ou SHA
courants restent `null`. Aucun
issuer, capability, authority, claim, receipt, destination ou record réel
n'existe. Aucun Python scientifique, NumPy, BLAS, `otool`, runtime secondaire,
waveform, population, index, P2, P0/P1/P2, donnée réelle, modèle, entraînement,
calibration ou locked-test n'a été utilisé.

Les seuls contrôles autorisés sont statiques : syntaxe JSON, blobs Git, SHA
liés, sémantique claim-before-invocation/one-shot/no-retry, absence de
self-hash, périmètre exact, `git diff --check` et propreté après commit.
