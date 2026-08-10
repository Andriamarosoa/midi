# H17 — Mesure réelle du risque causal `frame_fallback`

## Verdict

L’unique exécution réelle H17 est terminée avec succès et la population H21
est définitivement consommée. Le verdict préenregistré est :

```text
frame_fallback_false_risk_enrichment_not_demonstrated
```

Le résultat va dans le sens opposé à l’hypothèse d’enrichissement : sur la
population scellée, les NoteOn `frame_fallback` ont un risque causal de faux
NoteOn inférieur à celui du comparateur.

## Exécution et consommation H20

```text
commit runner/exécution : 2794ac91d1b1d038d24ca3995ea4fc4bc14a54c3
job                      : provisional-resolution-frame-fallback-h17-cpu-20260810
device                   : cpu
hard timeout             : 10800 s
début worker             : 2026-08-10T15:33:19Z
fin worker               : 2026-08-10T16:33:29Z
exit code                : 0
recordings traités       : 146 / 146
leakage groups           : 51 / 51
locked_test_used         : false
automatic_retry_allowed  : false
```

Le marqueur canonique a été déplacé atomiquement vers `.claimed`. L’état final
conserve `fresh_population_consumed=true`, `state=completed` et
`status=complete_atomic_result`. Aucun fichier d’échec n’existe et aucun retry
n’a été lancé.

Scellements principaux :

```text
contrat H22 SHA-256 : decb9e9398819294f797938dde834aa83cddb41bf537b757df74cf1291ea9ae6
H21 brut SHA-256    : acb8ced104ec99afd7f6f966be17b84ce4d436e5582137b6ec6048a90dfe3331
marker réclamé      : 445a4691ec2cd1622dd2c39bd9105831b5db7f7d4ee58c1ef21bb7699901e99e
état final          : 2865d0c962b6e1874f1b6f74d3777ca1cb21faec7b1877a8c826afe3118a0364
```

## Attrition complète

```text
NoteOn émis initialement considérés                 32 592
population activation audio-aware H17              30 648
exclus : harmonic_strong_frame                         476
exclus : legacy                                          0
exclus : retrigger                                    1 468
target non appariable ou exclu                        1 331
raison malformée                                          0
target malformé ou non fini                               0
NoteOn éligibles finaux                              29 317
  frame_fallback                                     7 567
  comparateur                                       21 750
```

La réconciliation est exacte :

```text
32 592 - 476 - 0 - 1 468 = 30 648
30 648 - 1 331             = 29 317
7 567 + 21 750             = 29 317
```

Comptes bruts par raison figée, avant exclusion du target non appariable :

| Raison | NoteOn |
|---|---:|
| `model_onset` | 13 961 |
| `frame_attack` | 8 700 |
| `frame_fallback` | 7 987 |
| `chord_completion` | 0 |
| `harmonic_strong_frame` | 476 |
| `retrigger` | 1 468 |
| `legacy` | 0 |

## Mesure primaire

La métrique scellée est :

```text
RD_false = P(false=1 | frame_fallback)
         - P(false=1 | comparateur)
```

Résultat :

| Mesure | Valeur |
|---|---:|
| Faux `frame_fallback` | 2 895 / 7 567 |
| Taux faux `frame_fallback` | 0,3825822651 |
| Faux comparateur | 11 582 / 21 750 |
| Taux faux comparateur | 0,5325057471 |
| `RD_false` | **−0,1499234820** |
| Risk ratio | 0,7184565935 |
| Part `frame_fallback` de la population éligible | 0,2581096292 |

L’écart absolu est donc de **−14,99 points de pourcentage**. Le risque relatif
observé pour `frame_fallback` est environ **28,15 % inférieur** à celui du
comparateur. Ces formulations sont descriptives ; le verdict reste celui du
contrat préenregistré.

## Bootstrap groupé préenregistré

```text
unité de rééchantillonnage : leakage_group_key
groupes scellés           : 51
réplications demandées    : 10 000
réplications valides      : 10 000
réplications invalides    : 0
RNG                       : numpy.random.Generator(PCG64)
seed                      : 721629268
méthode percentile        : numpy.percentile(method=linear)
IC95 RD_false             : [-0,19290474895676746 ; -0,08174647652290222]
```

L’IC95 entier est négatif. Les conditions positives préenregistrées
`RD_false >= 0,10` et borne basse strictement positive ne sont donc pas
satisfaites.

## Résultats secondaires par corpus

| Corpus | NoteOn éligibles | `RD_false` |
|---|---:|---:|
| `gaps_poly_mix` | 6 172 | −0,1881927175 |
| `guitar_techs_poly_directinput` | 6 820 | −0,1140750119 |
| `guitar_techs_poly_micamp` | 6 567 | −0,0592713983 |
| `guitarset_poly_mix` | 9 758 | −0,2300839200 |

Les quatre corpus ont un `RD_false` négatif. Ces sorties sont secondaires et
ne modifient pas le verdict.

## Artefacts atomiques

Répertoire Mac :

```text
/Users/amcarene/midi-worker/repository/tmp/local/
provisional_resolution_frame_fallback_h17_real_execution/
```

| Fichier | Octets | SHA-256 |
|---|---:|---|
| `attrition_report.json` | 99 947 | `1b63455a129d116041dd1945854a4493af1ef8f64fd7553d77db18cdbdde78e1` |
| `execution_provenance.json` | 754 | `020396d8cce23d1e4bf02a1f61006fd507d30855045b6f0fb071e5f91cc2c5a6` |
| `grouped_scientific_rows.json` | 11 194 751 | `3c41d6d70ce10a424bb9251f9604376fc6b69e9c72a322909af6ea7ca424ddcc` |
| `h17_metric_and_verdict_report.json` | 3 588 | `72e437a1060cc8a1bb8e59929ec0879cb63a6595f00963348e9f717c905d4bd8` |

Les quatre SHA ont été vérifiés après copie binaire en lecture seule vers le
worktree Windows. Le résultat Mac reste en place et n’a pas été modifié.

## Interprétation et limites

H17 ne démontre pas que `frame_fallback` est une source enrichie de faux
NoteOn causaux. Sur cette cohorte de découverte fraîche, il est au contraire
associé à un taux faux nettement plus faible que les raisons comparatrices.
Cela invalide l’hypothèse opérationnelle précise qui motivait H17 : supprimer
ou filtrer spécifiquement `frame_fallback` n’est pas soutenu par cette mesure.

Ce résultat ne prouve pas que tous les événements `frame_fallback` sont
corrects ni qu’ils doivent être promus sans autre analyse. Il reste limité à la
population H21, au décodeur/checkpoint scellés, au target causal de 250 ms et
aux 1 331 événements dont le target n’était pas appariable et qui ont été
exclus conformément au contrat. La cohorte est classée
`fresh_discovery_only_not_independent_validation` : elle ne constitue pas un
test verrouillé et ne doit pas être recyclée pour une nouvelle hypothèse.

## Décision

La mesure H17 est close. La population H21 est consommée et aucun retry n’est
autorisé. Aucun seuil, target, bootstrap, corpus ou taxonomie n’a été modifié.
Le test verrouillé est resté fermé. Toute suite scientifique devra faire
l’objet d’une hypothèse distincte et d’une nouvelle population autorisée.
