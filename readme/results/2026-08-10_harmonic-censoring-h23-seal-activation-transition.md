# H23 — transition d’activation du seal sans circularité de hash

## Décision externe

La revue externe de `1640d425b9de846c4104e8de37956bc461800c29`
approuve l’implémentation dormante, mais interdit encore la création du seal.
Elle identifie une circularité : incorporer le SHA du futur seal dans le source
capability modifierait précisément le blob que ce seal doit attester.

Ce correctif reste administratif et dormant. Il ne crée ni seal, ni artefact
d’activation, ni capability, ni claim. Il ne synthétise aucune waveform et
n’exécute aucun test P0/P1/P2.

## Activation séparée

Le source capability ne contient plus de constante
`H23_AUTHORIZATION_SEAL_SHA256`. Le futur seal sera référencé par un artefact
distinct et canonique :

```text
configs/harmonic_censoring_h23_synthetic_execution_activation.json
```

Cet artefact devra lier exactement :

- le chemin canonique et le SHA-256 brut du seal ;
- le commit d’implémentation déjà revu ;
- les blobs Git exacts du source capability et du runner.

Le seal répétera ces trois bindings d’implémentation. Toute divergence entre
activation et seal sera refusée.

## Frontière OS et commit revu

Le commit contenant le futur couple `activation + seal` ne sera pas déduit
silencieusement de `HEAD`. Le worker mono-usage devra injecter explicitement :

```text
H23_AUTHORIZATION_ACTIVATION_COMMIT=<SHA complet revu>
```

Avant de charger le seal, le loader exigera :

```text
SHA complet minuscule de 40 caractères
worktree propre
HEAD == commit d’activation injecté par le worker OS
octets de l’activation == blob suivi dans ce commit
revue externe APPROVED dans l’activation
SHA du seal == SHA lié par l’activation
bindings activation == bindings seal
```

Le commit futur pourra donc ajouter le seal et l’activation sans modifier les
deux sources d’implémentation que le seal atteste. Il n’existe aucune
dépendance `source → SHA seal → source`.

Le champ `exact_changed_files` doit rester l’égalité exacte du `diff-tree` du
commit d’implémentation revu. Il n’est pas obligé de contenir une source restée
inchangée dans ce commit : les deux sources sont protégées séparément en
exigeant que leurs blobs liés soient identiques au commit revu **et** au
checkout courant. Cette séparation permet de sceller `7e19bba7…`, qui modifie
la capability mais réutilise volontairement le runner déjà revu.

## Dormance actuelle

L’ordre du loader est fail-closed : l’absence de la variable OS provoque
`PermissionError` avant la résolution du plan H23. Les deux fichiers futurs
restent absents. Le claim et l’exécuteur scientifique restent également
inconditionnellement désactivés :

```text
H23_CONSUMPTION_CLAIM_IMPLEMENTED=false
PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED=false
```

## Vérifications pures

Les tests couvrent le schéma d’activation, le chemin canonique, l’absence de
self-hash, l’absence de binding OS et le refus avant résolution du plan. Les
tests élargis restent purement administratifs : aucune donnée, aucun modèle,
aucune waveform et aucun test scientifique ne sont utilisés.

```text
contrat capability
taille       16 826 octets
SHA-256 brut 87f9288ad25816573fd6076856320f182829cb77e4643bf887d2b1571ad819ec
blob Git     92baa8e7b34172762ab5f7dd276df4541de3222f

source capability
taille       25 910 octets
SHA-256 brut ea5c887b71dd4d24077f6db76678d2098ce4ac7d5f3c24f98e43d9435a8074ca
blob Git     24efe3daee1e99a3d4298452cd5eba9e9fa5f6be

runner inchangé
taille       15 057 octets
SHA-256 brut cf2cf6c0fa3b9e3b48a1607d03174eacdd3511c3db790b154c4e00673dadd0d6
blob Git     3699212be4db17df99acfddb864c0a25f56dcea4
```

Résultats : `26` tests ciblés réussis en `0,172 s`, puis `57` tests H23/H17/H20
réussis en `0,694 s`. `json.tool`, `py_compile` et `git diff --check`
réussissent.

## État

```text
dormant_activation_transition_defined true
authorization_activation_exists        false
authorization_seal_exists              false
OS_activation_binding_present          false
capability_issued                       false
consumption_claimed                     false
waveforms_synthesized                   false
P0_P1_P2_executed                       false
real_data_used                          false
H17_population_used                     false
locked_test_used                        false
training_authorized                     false
```

La prochaine action est uniquement la revue externe de cette transition. La
création du seal et de l’activation reste interdite jusqu’à cette revue.
