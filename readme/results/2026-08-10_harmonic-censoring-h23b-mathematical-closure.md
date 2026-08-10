# H23b — fermeture mathématique avant implémentation

## Portée

Ce correctif répond au verdict externe `NON APPROUVÉ` du commit
`90388048b02af5a1efb754b3c371043535adb4a6`. Il reste strictement
contract/doc-only. Aucun fixture n'a été synthétisé, aucun P0 exécuté, aucun
audio ou label projet ouvert, aucun modèle chargé et aucun fit réalisé.

## B9 — trois domaines distincts

Le contrat sépare désormais sans ambiguïté :

```text
sources latentes de factorisation : MIDI 24..76, 53 hypothèses
candidats d'émission live         : MIDI 40..76, 37 candidats
coordonnées d'observation         : 40..128, 89 coordonnées
```

Les sources latentes sous 40 sont evidence-only. Le cas conceptuel S1C reste
donc permis sans émission, tandis que S2–S5 utilisent maintenant l'analogue
produit `MIDI40 + MIDI64`, où H4(40) et H1(64) partagent la même fréquence.

## B10/B11 — vrai censoring et null support-aware

Le chemin primaire construit réellement :

```text
P_c(p,c,k) = P[k] × M(p,c,k)
```

avant de recalculer les énergies harmoniques censurées. Le hard mask coupe à
`c×F0`; le contrôle raised-cosine possède une transition scellée de 25 cents.

Le null utilise maintenant la réponse effective de chaque noyau sous le même
masque. Un harmonique sous Nyquist mais sans bin RFFT dans le noyau est masqué
et ne contribue à aucun numérateur ou dénominateur.

## B12 — summaries corrigées

`AUC_raw` intègre `S_raw` sans division par `B` et conserve donc les unités de
puissance. `AUC_normalized` reste gain-invariante. Le résidu final toujours nul
est supprimé et remplacé par `peak_absolute_residual` et `residual_at_c4`.
La clé normative est uniquement `regime_change` au singulier.

## B13 — factorisation et source-birth fermés

Le contrat définit une observation `y_q`, un dictionnaire harmonique `A[q,r]`,
une reconstruction additive non négative, le résidu quadratique `R(H)`, le
tie-break exact et la règle scellée `Delta_R(H,r)` pour `K` contre `K+1`.
Les collisions sont additives et jamais attribuées exclusivement.

La source-birth utilise uniquement deux fenêtres causales hop-alignées et le
tuple exact :

```text
(onset_rise, harmonic_novelty, new_energy,
 old_source_explanation, Delta_R, improvement_valid)
```

Chaque composante a une formule audio définie. Aucun score pondéré appris ou
ajustable n'est introduit. La règle synthétique BIRTH/NO_BIRTH/AMBIGUOUS est
préenregistrée et le cas de waveform identique reste obligatoirement ambigu.

## B14 — tenseurs séparés

La matrice live de censoring est exactement `37×6`. Le vecteur analytique de
factorisation possède séparément 89 coordonnées. Une coordonnée d'observation
ne devient jamais un candidat F0 ou une sortie MIDI.

## B15 — transformations des 175 fixtures

Les six bases et les 169 variantes OFAT restent inchangées en nombre. Chaque
famille possède maintenant une transformation déterministe précisant : source
ajoutée/remplacée, fréquence, enveloppe, pitch, target/cardinalité et cas
spécial evidence-only. Le matérialisateur futur n'a plus de choix scientifique.

## État

Les compteurs structurels restent `27 P0 + 35 P1 + 10 P2 = 72`, et
`6 + 169 = 175` fixtures. La seule action suivante est une nouvelle revue
externe du contrat. Toute implémentation/exécution P0, donnée réelle, modèle,
fit, population H17 ou test verrouillé demeure interdite.
