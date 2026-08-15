# H27 — Review 4 constructor gate read-only preflight

Date : 2026-08-16

## Autorisation et portée

La revue externe de `45b1108d7d185eee678992596871bfb35dfd7449`
conclut `PASS` sur l'exécution terminale du creator Review 4 et autorise une
unique action suivante : un préflight strictement read-only du gate constructor
publié. Ce préflight ne doit ni définir l'ACK, ni ouvrir le registre, ni changer
le checkout, ni invoquer constructor, materializer ou science.

Le code exact exécuté par stdin SSH est versionné sous :

```text
scripts/h27_review4_constructor_gate_readonly_preflight.py
size_bytes=15349
raw_sha256=9b36057eddb31b19ea8b6484d86dedacf534aafa618c8af8173647c537c59782
git_blob_sha1=3e2dc473b778bd7cca5855030a476c92947e2a7d
arguments=0
ACK H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE=absent
```

La connexion autorisée utilise exclusivement `amcarene@100.89.128.87`. Le
script est transmis sur stdin à l'interpréteur Python du worker, sans créer de
fichier distant.

## Bundle administratif vérifié

Le bundle exact est :

```text
/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1
file_count=6
closed_bundle_digest=879d547c6fa4f1da36b83733bd658f10f48582fb6130470bb4657b70e55253fe
execution_authority_artifact_id=45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e
```

Les six fichiers ont été lus avec `O_NOFOLLOW`, mode réel `0400`, stabilité du
descripteur, taille, blob Git et SHA-256 byte-exacts. Les liens gate, authority,
binding et external seals concordent.

## Checkout et constructor

```text
observed_head=7ee0a8977208bfa389e284b07207abc40a3517fd
required_head=46a6bdf81a56a7a7a10524d4e55092301a452207
head_match=false
required_head_is_ancestor=true
commits_back_to_required_head=11
detached=true
worktree_clean=true
index_lock_absent=true
```

Le constructor exigé au commit requis est :

```text
src/polyphonic/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor.py
git_blob_sha1=0c1a2aca42baa77edbd77ab42c0bd0cefaaa2b62
size_bytes=12599
raw_sha256=0b8ad2a7efcd875b0102619eefe7ca9f015d9349693959803b9004bccf15b807
```

Le scan read-only des scripts et modules de l'arbre observé n'identifie aucun
entrypoint qui lie le HEAD requis à une transition checkout/switch/reset/detach :

```text
transition_runner_candidates=[]
transition_entrypoint_identified=false
```

La commande de transition possible a seulement été décrite dans la sortie ;
elle n'a pas été exécutée et n'est pas autorisée par ce préflight.

## État terminal et STOP

Le préflight termine avec code `0` et :

```text
status=H27_REVIEW4_CONSTRUCTOR_GATE_READ_ONLY_PREFLIGHT_PASS_STOP
constructor_registry_state=absent
constructor_final_state=absent
constructor_staging_state=absent
constructor_ack_present=false
registry_appended=false
authority_reserved=false
authority_consumed=false
constructor_invoked=false
materializer_invoked=false
science_or_locked_test=false
head_changed=false
transition_executed=false
```

STOP respecté. Aucun retry, `flock`, append, checkout, reset, switch, detach,
mkdir, rename ou effet scientifique n'a eu lieu. La prochaine action nécessite
une revue externe explicite de cette preuve et une décision séparée sur un
éventuel runner de transition exact vers `46a6bdf8...`.
