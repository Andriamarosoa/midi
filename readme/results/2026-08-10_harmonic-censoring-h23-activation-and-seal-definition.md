# H23 — définition séparée de l’activation et du seal

## Autorisation

La revue externe de `f384cea35d12d6952f995f66cd954fe605ad1c83`
conclut `APPROUVÉ` et autorise uniquement la définition administrative du
couple canonique `activation + seal`. Elle interdit encore l’injection du
commit d’activation, l’émission d’une capability, le claim et toute exécution
scientifique.

## Seal défini

```text
configs/harmonic_censoring_h23_synthetic_execution_authorization_seal.json
taille       2 326 octets
SHA-256 brut 0074a29682d2847f70bdd2260a7f57f5b079fa94b92ba84cb01307dcdea8defa
blob Git     7294e9898c959ac0e664c3c7974e8a4b223c9e64
```

Le seal lie exactement :

```text
reviewed_execution_commit f384cea35d12d6952f995f66cd954fe605ad1c83
capability_source_blob    24efe3daee1e99a3d4298452cd5eba9e9fa5f6be
runner_source_blob        3699212be4db17df99acfddb864c0a25f56dcea4
H23 contract SHA          719eba0aa440fc1e77ae7d204adee9e5b51517f455fad3bfed7e761d3c00a74a
capability contract SHA   87f9288ad25816573fd6076856320f182829cb77e4643bf887d2b1571ad819ec
fixtures manifest SHA     acfa37b987deb19884c9f60cf3410717b68788eb466396402aaf992b3224e19c
tests manifest SHA        0d059d3f2540f2b08279bb8363e9036ae0f71b2bea11575bfebfce76b7fe7504
```

`exact_changed_files` reproduit le vrai `diff-tree` de `f384cea…`. Le runner
n’y est pas ajouté artificiellement : son blob inchangé reste lié et sera
comparé au commit revu puis au checkout courant.

Les six droits synthétiques sont explicitement vrais. Tous les droits
data/train/H17/locked-test restent faux. Le runtime est CPython 3.11.9,
NumPy 1.26.4, arm64 CPU et un thread. Les trois chemins one-shot sont nouveaux
et distincts sous `tmp/h23_synthetic_execution_20260810/`.

## Activation définie

```text
configs/harmonic_censoring_h23_synthetic_execution_activation.json
taille       732 octets
SHA-256 brut f4b0eaf26d9d5572eb69b38896718aac11575e290129fed8bc05bbb57fed22b1
blob Git     a14002c758d36406a84f23b6960ca75373991ea5
```

L’activation lie le chemin canonique du seal, son SHA brut `0074a296…`, le
commit `f384cea…` et les deux blobs source exacts. Elle ne contient ni son
propre hash ni le hash de son futur commit.

## Dormance conservée

La variable suivante n’est pas injectée :

```text
H23_AUTHORIZATION_ACTIVATION_COMMIT
```

Par conséquent, la factory refuse avant `load_h23_harness_plan()`. De plus :

```text
H23_CONSUMPTION_CLAIM_IMPLEMENTED=false
PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED=false
```

Aucune capability ne peut être claimée et aucun résultat autoritatif ne peut
être publié.

## Vérifications administratives

Les tests parsèrent les deux fichiers canoniques, recalculent le SHA du seal,
comparent les bindings activation/seal, vérifient le vrai `diff-tree` de
`f384cea…` et les deux blobs au commit revu et dans le checkout. Ils vérifient
également que l’absence du binding OS refuse avant le plan.

Résultats : `27` tests ciblés réussis en `0,500 s`, puis `58` tests H23/H17/H20
réussis en `0,851 s`. Les trois JSON passent `json.tool`; `py_compile` et
`git diff --check` réussissent.

## État

```text
activation_defined                       true
seal_defined                             true
activation_commit_injected               false
capability_issued                        false
consumption_claimed                      false
waveforms_synthesized                    false
P0_P1_P2_executed                        false
real_data_used                           false
H17_population_used                      false
locked_test_used                         false
training_authorized                      false
```

La prochaine action est la revue externe du commit exact contenant ces deux
artefacts. Aucune injection OS ni exécution n’est autorisée avant cette revue.
