# H24 — seal et contrat d'activation de matérialisation

Date : `2026-08-10`

## Autorisation reçue

La revue externe a approuvé le materializer dormant corrigé au commit :

```text
101103e63420de3703c045142291a9f231373f77
```

et a autorisé uniquement :

```text
AUTHORIZED_TO_DEFINE_H24_POPULATION_MATERIALIZATION_AUTHORIZATION_SEAL_AND_ACTIVATION_CONTRACT_ONLY
```

Cette étape ne crée aucune autorité opérationnelle et n'exécute aucun chemin
scientifique.

## Seal contractuel

Le seal lie exactement :

- commit materializer : `101103e63420de3703c045142291a9f231373f77` ;
- blob source materializer : `16210df0830eb62cc32f6900af51ad3d9e4972e5` ;
- SHA-256 du contrat de matérialisation :
  `b48aa4f417a9857983c79809efe24137d6b82ad0984d20e906286477f05a14ca` ;
- les quatre fichiers modifiés exacts du commit approuvé.

Les octets LF du seal ont le SHA-256 :

```text
3d5849b89c31037bbd07be391c3a7e8e5ef53b55f65fa4c6a8be0e19bb0ef218
```

Le contrat d'activation LF a le SHA-256 :

```text
5d7a7bbedabdeac79fc0d54f93a4eacd7d2f949e3f6cf5604a302e5667495512
```

## Contrat d'activation distinct

Le contrat d'activation ne contient pas son propre commit. Le futur commit
d'activation sera lié hors dépôt par :

```text
H24_POPULATION_MATERIALIZATION_AUTHORIZATION_COMMIT
```

Le checkout devra avoir un HEAD exactement égal à cette valeur, et les octets
du seal devront égaler le blob du même commit. Le HEAD courant non revu ne peut
jamais être inféré comme autorité.

Le contrat recopie exactement les chemins fixes claim/staging/success/terminal
et le runtime CPython 3.11.9 / NumPy 1.26.4 / arm64 / CPU / un thread. Il borne
les droits futurs à une seule matérialisation des 175 fixtures de
`H24_SYNTHETIC_V1`.

## Dormance et interdictions

Le statut reste :

```text
contract_only_pending_external_review_no_runtime_authority
```

La présence du seal et du contrat n'autorise actuellement ni émission de
capability opérationnelle, ni claim/marker, ni bridge NumPy, ni waveform, ni
population. P0/P1/P2, preuve scientifique, données réelles, H17, locked-test et
training restent tous explicitement faux.

Le bridge NumPy public demeure refusé dans le materializer ; aucune exécution
one-shot n'est donc possible par cette étape contractuelle seule.

## Validation administrative

Les tests contractuels vérifient le SHA du seal, son parsing fermé, la topologie
Git et le blob source du commit approuvé, les liaisons croisées, les chemins, le
runtime, le one-shot et toutes les interdictions. Le test dormant confirme que
l'absence de variable OS bloque la factory avant le preflight, même si le fichier
seal est désormais présent.

Aucun import NumPy opérationnel, aucune waveform et aucun accès scientifique
n'ont été effectués.

```text
167 tests H24/H23/H20 réussis en 1,971 s
py_compile réussi
git diff --check réussi
```

La prochaine action est uniquement la revue externe de ce seal et de ce contrat.
