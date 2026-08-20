# H28 — moteur et recomputer dormants à horizon causal étendu

## Résultat

Le lot H28 possède maintenant un moteur scientifique et un recomputer
indépendant, mais aucune voie d'exécution réelle. La capability scientifique
et le binding de population sont des types nominaux sans issuer ni loader :
les deux fonctions publiques s'arrêtent avant NumPy, le contrat, le filesystem
ou un payload.

## Changement contrôlé

Les formules scientifiques H27 restent inchangées. Un contrôle AST compare les
primitives de Hann, FFT x8, bandes de 35 cents, rangs 1–8, basis harmonique,
NNLS 512 itérations et résidu dans les deux implémentations. Les seules
différences admises sont :

- signal : `16640 -> 17152` échantillons ;
- masque role-major : `66560 -> 68608` octets ;
- dernière fin de proposition admise : `16895` ;
- sérialisation diagnostique complète.

Les payloads futurs sont fermés à exactement `waveform.f64le` et
`sample-valid-mask.u8`; un alternate payload est interdit pour cette population
P01/N01. Taille, SHA-256, containment et absence de symlink devront être
contrôlés avant décodage.

## Observabilité et réconciliation

Le résultat expose les quatre puissances totales, rangs et énergies exclusifs,
ratios harmoniques, nombre de ratios positifs, résidus avant/après candidat,
amélioration, onset, persistance, bornes, marges, courbe pitch-dilution MIDI
24–96, six booléens de sous-condition et décision complète.

Le sérialiseur n'accepte qu'un moteur et un recomputer concordants. Il
recalcule ensuite les relations dérivables : énergie/puissance, onset,
persistance, amélioration résiduelle, marges et point candidat de la courbe.
Les champs, leur ordre et les décisions sont enfin revalidés contre le schéma
préenregistré.

## Preuves locales

Commande ciblée :

```text
python -B -m unittest \
  tests.test_harmonic_censoring_h28_timing_contract \
  tests.test_harmonic_censoring_h28_engine_recomputer_dormant \
  tests.test_harmonic_censoring_h27_engine_recomputer_dormant
```

Résultat : `33 tests`, tous réussis. `py_compile` et `git diff --check` passent.
Les tests n'importent pas NumPy scientifique, ne lisent aucun payload H27/H28,
ne lancent ni FFT ni NNLS et ne créent aucune population.

Contrat du lot dormant :

```text
configs/harmonic_censoring_h28_engine_recomputer_dormant_contract.json
SHA-256 4fa739c2815872d4a5b7fd949288cea956590769269aa1906598b1f6fa15d90f
```

## Latence et limites

Ce commit n'ajoute aucun code au chemin live et n'a donc aucun impact mesuré
sur la latence du produit. Pour l'expérience future seulement, les trois
horizons correspondent à environ `5,805`, `11,610` et `17,415 ms` de signal
causal après l'onset. Aucun résultat ne permet encore de savoir lequel certifie
P01, ni si N01 reste sûr.

Aucun matérialiseur, population, autorité, claim ou exécution scientifique H28
n'existe dans ce lot. Training, calibration, checkpoint et locked-test restent
interdits.

## Suite unique

Implémenter le matérialiseur H28 dormant des six snapshots indépendants, avec
préfixe H27 byte-identique jusqu'à 16639 et extension déterministe jusqu'à
17151, puis le tester sans produire les payloads réels et sans émettre de
capability.
