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

Le claim futur devra lier l'identité et le SHA externe exacts de cette
authority, ainsi que les commits, blobs et SHA du contrat runtime et du
qualificateur. Il sera créé durablement et consommé avant l'observer. Son
existence signifie consommation, même après `QUALIFIED`, `DISQUALIFIED`,
`INCONCLUSIVE`, exception ou fichier partiel. Il ne pourra être supprimé,
remplacé ou réutilisé.

## Receipt terminal

Le schéma futur `H26_RUNTIME_QUALIFICATION_EXECUTION_RECEIPT_V1` lie notamment :

- identité et SHA brut externe du claim ;
- identité et SHA brut externe de l'authority ;
- commit/blob du qualificateur ;
- commit et SHA brut du contrat runtime ;
- existence et SHA brut du runtime record ;
- statut terminal ;
- `observer_invocation_count=1` ;
- `claim_consumed=true` ;
- `retry_allowed=false`.

Lorsqu'un record a été publié atomiquement, son SHA est obligatoire et le
statut du receipt doit être celui redérivé depuis ce record. Si une exception
post-claim empêche toute publication atomique du record, l'absence est liée
explicitement par `runtime_record_exists=false` et SHA `null`, avec terminal
`H26_MATERIALIZATION_RUNTIME_QUALIFICATION_INCONCLUSIVE_CONSUMED`. Dans les deux
cas, le claim reste consommé et aucun retry n'est possible.

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

Tous les états authority/claim/exécution/record/receipt/matérialisation/science
restent `false`, et tous les identifiants ou SHA courants restent `null`. Aucun
issuer, capability, authority, claim, receipt, destination ou record réel
n'existe. Aucun Python scientifique, NumPy, BLAS, `otool`, runtime secondaire,
waveform, population, index, P2, P0/P1/P2, donnée réelle, modèle, entraînement,
calibration ou locked-test n'a été utilisé.

Les seuls contrôles autorisés sont statiques : syntaxe JSON, blobs Git, SHA
liés, sémantique claim-before-invocation/one-shot/no-retry, absence de
self-hash, périmètre exact, `git diff --check` et propreté après commit.
