# H27 — Review 4 constructor execution gate terminal

Date : 2026-08-16

## Autorisation et identité exécutée

La revue externe du correctif `342f46695974ece843dcdc5de86562d016edcd36`
rend `PASS — exécutable` et autorise une seule invocation Mac du gate exact :

```text
path=scripts/h27_review4_constructor_execution_gate_once.py
git_blob_sha1=231d7793fb7d016c3f150b5cd8eff56ddabe24e0
size_bytes=25156
raw_sha256=82953b3fb5a2227ac516cc4c1960b2308b7ac4ceb276dcb8b43ddf5e060ad482
ACK=H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE=1
arguments=0
```

Le canal autorisé est une unique connexion SSH vers
`amcarene@100.89.128.87`. Le bootstrap LF crée le root neuf
`/Users/amcarene/h27-review4-constructor-gate-342f4669`, télécharge le runner
depuis le commit exact, vérifie ses trois identités avant renommage atomique,
puis l'invoque dans un environnement fermé :

```text
env -i
HOME=/Users/amcarene
PATH=/usr/bin:/bin:/usr/sbin:/sbin
PYTHONDONTWRITEBYTECODE=1
GIT_TERMINAL_PROMPT=0
GIT_NO_LAZY_FETCH=1
GIT_OPTIONAL_LOCKS=0
H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE=1
```

## Résultat terminal

La connexion SSH unique termine avec code `0`. Le runner imprime :

```json
{"status":"H27_REVIEW4_CONSTRUCTOR_EXECUTION_GATE_TERMINAL_SUCCESS_STOP","required_head":"46a6bdf81a56a7a7a10524d4e55092301a452207","control_bundle_digest":"879d547c6fa4f1da36b83733bd658f10f48582fb6130470bb4657b70e55253fe","verified_target_identities":112,"verified_authority_identities":4,"verified_total_identities_before_registry":116,"execution_authority_artifact_id":"45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e","authority_instance_id":"d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a","invocation_nonce":"c8c7dc8162910a140bc1699b488478b8f9f343a855973453671f6cacdfcea165","issued_at_utc":"2026-08-16T08:36:14Z","canonical_sha256":"89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2","registry_created":true,"authority_reserved":true,"authority_consumed":true,"constructor_invoked_once":true,"constructor_filesystem_effects":0,"destination_observed":false,"authority_instance_artifact_exists":false,"materializer_invoked":false,"science_or_locked_test":false,"retry_authorized":false}
```

Le gate a donc vérifié avant sa frontière persistante :

```text
HEAD exact 46a6bdf8...
bundle fermé 879d547c...
112 identités checkout
4 identités d'autorité
total 116
constructor frozen exact
```

La création exclusive du registre a consommé la tentative. L'ordre terminal
attesté est : registre créé, réservation durable, consommation durable,
constructor figé invoqué une fois. Le constructor effect-free rend l'identité
d'instance `d44941a8...` et le SHA canonique `89d03ce3...`, avec zéro effet
filesystem propre au constructor et zéro invocation scientifique.

Le registre est un effet administratif réel et persistant. En revanche, le
constructor n'a pas observé ni créé la destination activation, n'a produit
aucun artefact d'instance sur disque et n'a invoqué aucun materializer.

## Consommation et STOP

Cette tentative est définitivement consommée. Aucun retry, second SSH,
suppression, cleanup, réparation ou seconde invocation n'a eu lieu et aucun ne
sera effectué.

Le résultat scientifique reste inchangé : aucun materializer, population,
P0/P1/P2, waveform/data, science, locked-test, training ou calibration. STOP
absolu avant toute prochaine frontière et revue externe obligatoire de cette
preuve terminale.
