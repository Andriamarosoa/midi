# H27 — contrat de transition exacte du checkout cible

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Autorisation amont : PASS de `b832f8797b557256dda85e40e8f952c59402fa3d`

## Portée

Lot strictement déclaratif : contrat de la future transition one-shot du
checkout cible et seal externe, test déterministe et mise à jour du journal.
Aucun runner de transition, aucune commande Mac et aucun effet scientifique.

## Frontière scellée

- checkout exact : `/Users/amcarene/midi-worker/repository` ;
- ODB exact : `/Users/amcarene/midi-worker/repository/.git` ;
- HEAD initial exact :
  `75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf` ;
- HEAD cible exact :
  `7ee0a8977208bfa389e284b07207abc40a3517fd` ;
- objet cible préalablement vérifié comme `commit` ;
- future mutation unique : détachement explicite vers le SHA cible exact ;
- état terminal exigé : HEAD exact, détaché et worktree propre.

Le contrat interdit tout fetch, pull, merge, reset, rebase, sélection implicite
de branche et toute modification de branche. La transition HEAD/worktree est
la seule mutation future autorisable. Un échec impose STOP terminal sans
retry, reset, cleanup ou réparation automatique.

## Identité du contrat

```text
path       configs/harmonic_censoring_h27_target_checkout_detach_transition_contract.json
git blob   11fff0962fc0951a0bb06605e233d34756a2f4d9
size       3643
sha256     f1c7bf1b94b0a35e3f0bd1771e93addd594053cb155ed1c3a9e09670e57de1e5
```

Le seal externe conserve cette identité byte-exacte ainsi que les deux HEAD,
les chemins, la nature `commit`, le caractère one-shot et toutes les
interdictions aval.

## État préservé

Le registre reste non ouvert, non écrit et vide selon le préflight approuvé.
L'autorité n'est ni réservée ni consommée. Aucun ACK creator, aucune invocation
creator, aucun staging/final bundle, constructeur, matérialisation, science ou
locked test. Le runner control-parent terminalement consommé reste non
rejouable.

## Validation locale

Le test déterministe compare les octets LF sans BOM, recalcule blob Git,
taille et SHA-256, puis impose les dictionnaires complets du contrat et du seal
ainsi que l'ordre fail-closed exact.

- `py_compile` : réussi ;
- test ciblé : `3/3` réussis ;
- suite H27 complète : `503/503` réussis en `63,223 s` ;
- parse JSON strict par les tests et PowerShell : réussi ;
- `git diff --check` : requis avant commit.

## STOP

Ce lot n'autorise ni l'implémentation d'un runner ni la modification réelle du
checkout Mac. Prochaine action unique : revue externe du commit déclaré. Une
future transition exige un nouveau PASS explicite et un lot séparé.
