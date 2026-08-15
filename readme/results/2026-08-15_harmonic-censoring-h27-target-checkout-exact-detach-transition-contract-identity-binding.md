# H27 — identity binding du contrat de transition exacte du checkout

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Autorisation amont : PASS de `36d9ee11fc800a7e57edff1a73858c47ccbdb947`

## Portée

Lot administratif strictement déclaratif : identity binding du contrat de
transition PASS, external seal de ce binding, test déterministe et mise à jour
du journal. Aucun runner de transition, aucune commande Mac, aucun detach et
aucun effet scientifique.

## Graphe d'identités

Trois chemins uniques sont liés byte-exactement :

```text
contrat PASS
11fff0962fc0951a0bb06605e233d34756a2f4d9 / 3643
f1c7bf1b94b0a35e3f0bd1771e93addd594053cb155ed1c3a9e09670e57de1e5

seal du contrat
24a8c14fddd52eca148f961a31c39abaa4de018f / 1796
b62eff68cbca0c84c7483cbd9f3ea5049b1156129398e571b88adcbf553f0aba

preuve préflight approuvée b832f879...
bda7e1fae7379996563e73d8bbcf1b2d7a871aa0 / 1987
a28a73389a338c8d493b7c75ca82656fb01ce75eddf3aa0f277d4a928b5dbc95
```

Le binding interdit les doublons, toute dérive de chemin ou d'identité, toute
auto-référence et toute back-reference historique.

## Frontière liée

- checkout : `/Users/amcarene/midi-worker/repository` ;
- ODB : `/Users/amcarene/midi-worker/repository/.git` ;
- HEAD initial : `75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf` ;
- cible exacte de type commit :
  `7ee0a8977208bfa389e284b07207abc40a3517fd` ;
- unique mutation future : detach explicite vers ce SHA ;
- état terminal : HEAD cible exact, detached, worktree propre ;
- tentative unique, échec terminal et aucun retry/cleanup/réparation.

Fetch, pull, merge, reset, rebase, modification de branche, ACK/invocation
creator, registre, autorité, bundle, constructeur/matérialisation, science et
locked test restent interdits.

## Identité du binding

```text
path       configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_identity_binding.json
git blob   a514aa0270926dca1d8402ac84078a50754d2f17
size       4496
sha256     c614d733121451c65134f480427a6d883013256633b123f34aa57f2a25f09f82
```

Le seal externe porte cette identité et reproduit les racines, chemins, HEAD,
type commit, contraintes one-shot et tous les états aval faux.

## Micro-correction après première revue

La revue externe de `669e2f04...` rend `FAIL` sur un seul point : le binding
ne liait pas comme liste ordonnée les onze étapes normatives du contrat. La
correction ajoute `bound_future_fail_closed_order` au binding et
`future_fail_closed_order_exact` au seal. Le test exige maintenant que ces
deux listes soient exactement égales à
`contract["future_fail_closed_order"]`, en plus de la comparaison complète du
seal. Les trois racines byte-exactes restent inchangées.

## Validation locale

Le test recalcule les trois identités et celle du binding, vérifie LF sans BOM,
les racines de revue, les dictionnaires complets des frontières, interdictions,
états préservés/courants et le seal entier.

- `py_compile` : réussi ;
- test ciblé : `4/4` réussis ;
- suite H27 complète après micro-correction : `507/507` réussis en
  `62,065 s` ;
- `git diff --check` : requis avant commit.

## STOP

Prochaine action unique : revue externe de ce binding et de son seal. Aucun
runner de transition, checkout/switch/detach Mac ou effet aval n'est autorisé
par ce lot.
