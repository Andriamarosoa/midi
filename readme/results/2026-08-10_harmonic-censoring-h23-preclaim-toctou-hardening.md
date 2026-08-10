# H23 — durcissement TOCTOU pré-claim dormant

## Portée

La revue externe de `a84f106a7d19e29f5ea858f5f3fc788d7b0c25c6`
approuve le correctif sémantique dormant et autorise uniquement un commit
TOCTOU séparé avant toute discussion d'un nouveau seal. Cette étape ne crée ni
seal, ni activation, ni capability de production, ni marker. Elle n'exécute
aucune procédure scientifique H23.

## Frontière renforcée

La capability continue d'être émise seulement après le préflight complet.
Immédiatement avant le futur `O_CREAT|O_EXCL|O_WRONLY`, elle revalide désormais
les dépendances qui déterminent l'exécution :

- octets de l'activation et du seal liés à la capability ;
- contrat de capability, contrat claim/executor/transcript et contrat H23 ;
- reconstruction du plan depuis le contrat rehaché ;
- SHA des manifests générés des 175 fixtures et des 72 tests résolus ;
- blobs Git approuvés du contrat, du harness et de son test contractuel ;
- blobs du commit d'implémentation pour la capability, le runner et le
  recomputer pur `harmonic_censoring_h23_oracles.py` ;
- worktree toujours propre ;
- `HEAD` toujours égal au commit d'activation attesté ;
- identité CPython/NumPy/arm64/CPU et quatre variables de threads toujours
  identiques au snapshot émis ;
- absence des quatre destinations one-shot.

La préparation réversible du répertoire du marker est déplacée avant cette
revalidation. Le payload canonique est également préparé en mémoire avant elle.
Après son retour, `_write_exclusive_durable_file(..., create_parent=False)`
effectue directement le `os.open(...O_EXCL...)` irréversible.

Le premier reload post-claim du contrat scientifique prend désormais le SHA
attesté en argument. Il lit le fichier une fois, compare
`sha256(raw) == claimed.contract_sha256`, puis parse ces mêmes octets. Une
mutation entre préclaim et consommation scientifique produit donc une erreur
après consommation, sans jamais faire utiliser le contrat divergent.

## Tests administratifs

Les nouveaux tests prouvent qu'une divergence des octets contractuels, du
manifest résolu, du recomputer pur, du runtime ou d'un `HEAD` pourtant propre
est rejetée avant l'appel à la primitive exclusive. Un autre test modifie le
contrat avant son reload post-claim et vérifie son refus avant parsing. Le test
d'ordre impose la séquence exacte :

```text
revalidate
→ O_EXCL
```

Validation locale sans science :

```text
74 tests H23 réussis
7 tests H20 réussis
py_compile réussi
git diff --check réussi
```

Les tests ne chargent aucun evaluator scientifique et ne synthétisent aucune
waveform.

## État de sécurité

```text
nouveau seal / activation       absent
claim de production             absent
marker                          absent
waveform                        absente
P0 / P1 / P2                    non exécutés
population H17                  non utilisée
donnée réelle / modèle          non chargé
locked-test                     non utilisé
```

La prochaine étape reste une revue externe de ce commit dormant. Un nouveau
seal ou une activation restent interdits avant son approbation explicite.
