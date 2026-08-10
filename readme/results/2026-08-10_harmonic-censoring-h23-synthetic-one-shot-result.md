# H23 — résultat terminal de l’unique passe synthétique

## Verdict

L’unique population synthétique H23 est consommée. Le résultat autoritatif est :

```text
H23_SYNTHETIC_HYPOTHESIS_KILLED
```

La règle d’arrêt préenregistrée a interrompu la passe sur le premier test P0,
`A01`. Aucun retry, aucune correction puis relance et aucune poursuite vers les
tests restants ne sont autorisés avec cette population.

## Autorité exécutée

```text
commit OS-bound
8c5e982fd57778c0bb8a3bfb27329a56841df582

commit d’implémentation
1025ac56706312718e93f9078fdf9c341276c8ea

SHA activation
81d0f0d6739e082745ae646a57ad31b17a62b5007dd4c0f718701c03dfe25906

SHA seal
381d83e5dd184a1ad72f29aa4f8450b3a1d066b582e8191ef2290640f7bd0899
```

L’exécution a utilisé le Mac arm64, CPython `3.11.9`, NumPy `1.26.4`, CPU et
un thread. Le worktree était propre au commit exact avant le claim. Le marqueur
durable a été créé par `O_EXCL` avant toute éventuelle première waveform.

## Résultat scientifique

```text
tests préenregistrés                 72
tests exécutés                        1
tests réussis                         0
premier échec                       A01
tests non exécutés                   71
fixtures préenregistrées            175
fixtures matérialisées                0
waveforms matérialisées               0
données réelles utilisées         false
population H17 utilisée           false
locked-test utilisé               false
training autorisé                 false
```

`A01` est un test analytique de direction harmonique. Son résultat persiste :

```text
primary_pass   false
inverse_pass   true
final_pass     false
elapsed_ns     155959
```

Le producteur a énuméré `1 060` arêtes du graphe `F0 + H1–H20`. Aucune n’est
descendante et aucune arête `C4 → C3` n’est présente. Cependant, `H1` engendre
nécessairement les arêtes identité `pitch → pitch`, tandis que l’oracle scellé
`all_edges_ascending` exige strictement `edge[1] > edge[0]`. Ces arêtes identité
font donc échouer le primaire. L’inverse injecte bien une arête descendante
`60 → 59` et réussit son contrôle.

Cette observation indique une incompatibilité entre la présence préenregistrée
de `H1` et l’inégalité stricte de l’oracle. Elle ne permet toutefois pas de
reclasser le résultat : la frontière one-shot impose le verdict terminal
`H23_SYNTHETIC_HYPOTHESIS_KILLED` dès tout échec P0.

## Artefacts autoritatifs Mac

Répertoire :

```text
/Users/amcarene/midi/tmp/h23_synthetic_execution_20260810/
```

```text
consumed.json
taille  1510 octets
SHA-256 23b6983d1e94a5a161dae98ca2f9c54118b5d0eab665a6996763c3dd7252149f

transcript.jsonl
taille  46323 octets
SHA-256 ff169cccf4ffce6ff863b7f102c448075b696eeffb37610250dbc5d45a1308d8

terminal/terminal_report.json
taille  2054 octets
SHA-256 670f072b70ae52786daa214b56871fae68b83aaf6e3caf8ac7c4c499c7ee7116
```

Le rapport terminal relie le transcript et le marqueur de consommation. Aucun
répertoire `success` n’existe. Après publication, aucun processus H23 n’était
actif et le worktree Mac était propre.

## Portée

Ce résultat clôt la population synthétique H23. Il n’autorise ni entraînement,
ni donnée réelle, ni H17, ni export, ni live, ni test verrouillé. Une éventuelle
reformulation de l’hypothèse devra être un nouveau contrat et une nouvelle
population explicitement autorisés ; elle ne pourra pas être présentée comme
un retry de H23.
