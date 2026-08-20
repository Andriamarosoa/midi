# H28 — préinscription du premier instant causal de certification

## Objet

H27 est définitivement clos après l'échec scientifique de P0-003. H28 est une
hypothèse distincte qui ne répare, ne rejoue et ne réinterprète pas H27. Elle
teste une seule variable : la quantité de signal causal disponible après
l'onset synthétique fixe.

La question préenregistrée est :

> Quel est le premier horizon causal auquel le certificat H27 inchangé accepte
> la naissance isolée P01 sans transformer le contrôle d'ancienne harmonique
> N01 en `BIRTH_SUPPORTED` ?

## Population et horizons

La future population H28 contient exclusivement deux fixtures synthétiques
héritées byte-exactement dans leur définition scientifique :

- `H27-F-P01`, vraie naissance isolée MIDI 40 ;
- `H27-F-N01`, ancienne harmonique sans naissance du candidat MIDI 52.

Chaque fixture est observée dans un snapshot indépendant aux trois horizons :

| Horizon | Fin de proposition | Samples après onset | Durée causale |
|---|---:|---:|---:|
| `N` | 16383 | 256 | 5,804988662 ms |
| `N_PLUS_1` | 16639 | 512 | 11,609977324 ms |
| `N_PLUS_2` | 16895 | 768 | 17,414965986 ms |

Le flux synthétique futur devra être étendu jusqu'à l'échantillon 17151 afin de
conserver le hop de résolution de `N_PLUS_2`. Son préfixe jusqu'à l'échantillon
16639 devra être byte-identique au rendu H27 correspondant. Les payloads H27
consommés ne seront ni réutilisés ni modifiés.

## Science inchangée

H28 fige sans modification : Hann, zero-padding FFT x8, bandes de 35 cents,
rangs harmoniques 1 à 8, NNLS 512 itérations et tous les seuils positifs et
négatifs H27. Aucun seuil ne pourra être choisi après observation.

Le moteur H27 reste la référence normative des formules, mais ne peut pas être
appelé directement : sa validation impose un signal de 16640 samples et refuse
un horizon supérieur ou égal à 16640. H28 exigera donc un moteur et un
recomputer séparés dont les seules différences autorisées sont la longueur
17152, les plans de masque correspondants, la borne d'horizon 16895 et la
sérialisation diagnostique complète. Toute autre dérive algorithmique échoue.

La seule variable expérimentale est donc :

```text
256 -> 512 -> 768 samples causaux après le même onset
```

Les snapshots sont indépendants. Une décision à `N` ne peut pas muter l'état
utilisé à `N_PLUS_1` ou `N_PLUS_2`.

## Observabilité obligatoire

Contrairement au rapport H27, chaque résultat futur devra persister les
puissances des quatre vues, rangs et énergies exclusifs, tous les ratios,
résidus avant/après candidat, amélioration résiduelle, montée d'onset,
persistance, bornes, marges, courbe complète de pitch-dilution MIDI 24–96,
booléens de chaque sous-condition, décision et
borne causale réellement lue. Le moteur H28 et un recomputer H28 indépendant devront
être réconciliés avant toute interprétation.

## Verdict préenregistré

La sécurité N01 précède toujours l'interprétation positive : si N01 devient
`BIRTH_SUPPORTED` à un seul horizon, H28 termine en échec de sécurité. Sinon,
le premier horizon où P01 devient `BIRTH_SUPPORTED` détermine le verdict. Si
P01 reste non certifié jusqu'à `N_PLUS_2`, le timing seul est insuffisant et un
successeur séparé pourra seulement alors examiner Hann, les bandes, NNLS ou les
seuils.

## Portée actuelle

Le présent lot contient uniquement :

- le contrat JSON dormant H28 ;
- un loader fail-closed lié aux octets H27 approuvés ;
- le schéma diagnostique complet ;
- la dérivation pure du verdict ;
- des tests locaux sans NumPy scientifique ni population.

Validation locale : `23/23` tests réussis, comprenant les `12` tests H28 et
les `11` régressions dormantes moteur/recomputer H27, puis `py_compile` et
`git diff --check`. Ces tests n'ont lu aucun payload scientifique H27/H28.

Aucune population H28, FFT, matérialisation Mac, exécution scientifique,
entraînement, calibration, checkpoint ou locked-test n'est autorisé. Une revue
externe explicite est obligatoire avant la matérialisation.
