# H28 — résultat scientifique one-shot

Date de clôture UTC : `2026-08-21`.

## Verdict

```text
H28_TIMING_INSUFFICIENT_THROUGH_N_PLUS_2
```

L'hypothèse temporelle seule est rejetée dans la plage préenregistrée : conserver
exactement la science H27 et attendre `N`, `N+1`, puis `N+2` ne suffit pas à
transformer P01 en `BIRTH_SUPPORTED`. H28 est consommée sans retry.

## Identité et provenance

- commit exécuté : `9528889c5e7db30cd3030d15fa8e4ac0c62e5a2b` ;
- execution ID : `h28-20260820-mac-once-v1` ;
- execution contract SHA-256 :
  `286179fd68cf93b0c35ac6e8a54632772ada863a6c6041cac6738298461a9dd7` ;
- activation SHA-256 :
  `4e5ccb467b2e600292a67fff49f5d75b5765971db2713981aeb39bdba5fd9744` ;
- CLAIM SHA-256 :
  `3024e43837ad72c0f6d8eb88f2dae61bb20a4fd87e1073d1253082e88d858f0c` ;
- runtime : Darwin arm64, CPython `3.11.9`, NumPy `1.26.4`, CPU seul ;
- locked test, entraînement et calibration : `false` ;
- retry : `false`.

Le résultat final a été publié par rename no-replace. Il ne reste aucun staging,
aucun processus H28 et aucun fichier de failure.

## Attrition et réconciliation

```text
descripteurs préenregistrés       6
payloads rendus et préfixes H27   6
records engine                    6
records recomputer                6
records réconciliés               6
records publiés                   6
échecs                            0
BIRTH_SUPPORTED                   0
NO_BIRTH                          0
AMBIGUOUS                         6
```

Les six lignes téléchargées ont été revalidées hors runner par le schéma fermé
H28. Le verdict a été redérivé et les hashes de `report.json`,
`diagnostics.json` et `population_index.json` ont été comparés à `COMPLETE.json`.

## Résultats P01

| Horizon | Temps causal | Onset rise | Max ratio harmonique | Ratios >= 0,02 | Amélioration résiduelle | Persistance | Décision |
|---|---:|---:|---:|---:|---:|---:|---|
| N | 5,805 ms | 1,000000 | 0,008933 | 0 | 0,023038 | 1,000000 | AMBIGUOUS |
| N+1 | 11,610 ms | 0,966572 | 0,006249 | 0 | 0,031815 | 0,967994 | AMBIGUOUS |
| N+2 | 17,415 ms | 0,870973 | 0,002516 | 0 | 0,040885 | 0,878198 | AMBIGUOUS |

La preuve temporelle d'apparition est forte aux trois instants. En revanche,
les deux autres membres du certificat positif échouent toujours : aucun des
partiels exclusifs ne franchit le ratio `0,02`, et l'amélioration résiduelle reste
loin de `0,1`. Son augmentation régulière (`0,0230 -> 0,0318 -> 0,0409`) montre
qu'un délai apporte de l'information, mais pas assez dans la fenêtre H28 testée.

La courbe pitch-dilution confirme aussi une ambiguïté de pitch : la valeur du
candidat MIDI 40 suit l'amélioration résiduelle ci-dessus, tandis que le meilleur
pitch est MIDI 29 à N (`0,05248`), MIDI 29 à N+1 (`0,05641`) puis MIDI 42 à N+2
(`0,04783`). La géométrie actuelle n'isole donc pas encore proprement le
fondamental 40.

## Contrôle inverse N01

Pour N01, le candidat MIDI 52 a un onset rise `0`, une amélioration résiduelle
`0` et une valeur pitch-dilution `0` aux trois horizons. Il ne devient jamais
`BIRTH_SUPPORTED`, donc aucune défaillance de sécurité positive n'est observée.

N01 reste toutefois `AMBIGUOUS`, pas `NO_BIRTH`. Les ratios mesurés sont
extrêmement faibles (maximum entre `4,02e-11` et `1,15e-10`), mais les bornes
de détectabilité des partiels restent elles-mêmes sous `0,02`. Le contrat exige
au moins deux partiels dont la borne atteint `0,02` avant d'autoriser une preuve
négative. H28 refuse donc correctement de conclure à l'absence sur une preuve
spectrale insuffisamment bornée.

## Temps de calcul

```text
P01/N         851,131 s
N01/N        2052,574 s
P01/N+1       851,376 s
N01/N+1      2054,889 s
P01/N+2       850,968 s
N01/N+2      2070,466 s
total         8731,483 s
```

Cette forte différence vient du NNLS à deux composantes pour N01. Toute future
optimisation devra démontrer une parité numérique stricte avant de remplacer ce
chemin ; elle ne peut pas justifier un retry H28.

## Artefacts publiés

```text
report.json
343c8a50320826ae44c88d608ee77785b12aaa36da2c9add7dbe1b05f11c8edf

diagnostics.json
4226e3a6c375dd1e208f62d48bc1c37df6218934af804cd7650bfeee67bf3986

population/population_index.json
a281062ba2855d08f97affabdc6211ff104e8f6769e02c729af741ad995c2c1e

COMPLETE.json
9ee29057bc101feb09a86a3238bd96e8fdaade597cd9cfc406374a5228d8821a

terminal
9bc206b106423a26be92e703bc5017d7f88466edd83dbd2eeeb6db24769eddb1
```

## Conclusion scientifique

H27 n'échouait pas seulement parce que P01 était interrogé au tout premier hop.
Jusqu'à `N+2`, l'onset devient observable mais l'identité spectrale et la
réduction résiduelle restent insuffisantes. Une éventuelle H29 doit donc isoler
une seule modification de géométrie de preuve — par exemple la pondération
temporelle/normalisation ou la représentation des partiels — et conserver P01,
N01 et les contrôles inverses. Elle ne doit ni relancer H28 ni modifier plusieurs
seuils et fenêtres simultanément.

État final :
`H28_COMPLETE_ONE_SHOT_CONSUMED_TIMING_INSUFFICIENT_THROUGH_N_PLUS_2_NO_RETRY`.
