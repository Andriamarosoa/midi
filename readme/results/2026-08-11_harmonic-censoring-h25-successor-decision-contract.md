# H25 — contrat de décision successeur après la clôture inconclusive H24

## Portée

La revue externe de la clôture H24 autorise uniquement la définition du
successeur :

```text
AUTHORIZED_TO_DEFINE_POST_H24_SUCCESSOR_DECISION_CONTRACT_ONLY
```

Ce commit ne doit contenir aucune implémentation, population, capability,
claim, exécution ou mesure scientifique.

Contrat canonique :

```text
configs/harmonic_censoring_h25_successor_decision_contract.json
6343 octets
SHA-256 a50189acc47c1999935212e8549403992a663dee316fa3e88812eca159043fd4
```

## Point de départ irréversible

H24 est définitivement :

```text
H24_EXECUTION_INCONCLUSIVE_CONSUMED
P0/P1/P2 = 0/0/0
scientific verdict = absent
retry = forbidden
```

Le claim `5e7bf032…` reste la preuve durable de consommation. Le résultat ne
peut être réinterprété ni comme un succès ni comme un échec scientifique.

## Décision H25

H25 ne commence pas par une nouvelle hypothèse harmonique. Sa première question
est opérationnelle :

> Le cycle one-shot complet peut-il avancer, dans un unique processus revu,
> depuis le préflight jusqu'aux fermetures success/failure/inconclusive sans
> injection après claim, perte d'autorité process-local ou intervention
> manuelle sur les preuves ?

La qualification de ce cycle doit réussir avant de définir une population ou
une hypothèse scientifique H25.

## Correction du défaut du sas passif

Le futur exécuteur devra satisfaire simultanément :

- un seul entrypoint possède capability, claim, phases et fermeture ;
- toutes les autorisations scientifiques sont fixées avant le claim ;
- aucune pause humaine ne survient après le claim ;
- le transport du script ne partage pas le stdin de contrôle ;
- EOF, déconnexion SSH, signal et timeout ont une fermeture préenregistrée ;
- le claim est la dernière action irréversible avant l'exécution automatique ;
- aucune capability process-local n'est supposée survivre au processus ;
- aucune injection ou `exec` interactif n'est permis après claim.

## Qualification pré-claim

Avant toute population scientifique, un namespace administratif jetable devra
rejouer la forme complète du contrôle avec un claim substitutif. Il ne pourra
utiliser ni le claim H24, ni ses waveforms, ni NumPy scientifique.

La qualification couvrira le nominal et les inverses suivants : EOF avant et
après claim substitutif, déconnexion du parent SSH, `SIGINT`, timeout dans chaque
phase, échec d'écriture des preuves, échec de publication du transcript ou du
terminal et échec du renommage atomique final.

Chaque inverse devra aboutir à un état préenregistré, sans retry, suppression
de claim ou fabrication manuelle. Les événements et hashes devront être
recalculés indépendamment.

## Nouvelle identité scientifique différée

Les namespaces suivants sont seulement réservés :

```text
H25_SYNTHETIC_V1
H25_TEST_V1
```

Aucun manifest ni fichier n'existe encore. H24 ne peut fournir ni population,
test, claim ou résultat à H25. Après qualification opérationnelle et nouvelle
revue, un contrat scientifique séparé devra définir une population neuve, de
nouveaux identifiants, un nouveau one-shot, un seal, une activation et un
binding OS.

## Interdictions actuelles

Ce contrat n'autorise aucun retry H24, aucune capability H24/H25, aucun claim,
aucune implémentation de runner, population, waveform, P0/P1/P2, donnée réelle,
H17, locked-test, modèle, checkpoint, calibration, training, export ou live.

La prochaine étape est uniquement la revue externe du contrat H25.
