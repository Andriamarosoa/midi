# Contrat lecteur de preuve d'actifs V2 indépendante

## Portée

La revue externe du résultat `eb63f6a` autorise seulement la préparation d'un
contrat lecteur séparé. Ce commit ne lit pas le registre déjà publié, ne
rehache aucun audio ou label et ne contacte pas le Mac. Il ne charge ni
TensorFlow, ni modèle, ni checkpoint et ne lance ni inférence, ni évaluation,
ni fit, ni calibration, ni export, ni live, ni test verrouillé.

## Double liaison scellée

Le nouveau protocole canonique a le SHA-256 :

```text
6bf7619a109e6141470a99eacd4eaecf83edaf7ce0fd76bb03bc60e5bfc8ab3e
```

Il fixe exactement :

```text
status                         = independent_validation_asset_evidence_reader_authorized
allowed_now                    = independent_validation_asset_evidence_read
builder_authorized_now         = false
reader_authorized_now          = true
source_evidence_protocol_sha256 = d63655c388991f3782a738e5bba58f0409ae79f297a3d5009dab7971349ba015
expected_evidence_sha256       = 10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee
locked_test_used               = false
```

Le futur lecteur ne pourra donc pas simplement accepter un JSON de bonne forme
ou un registre produit avec un autre builder. Il devra vérifier les octets du
registre publié et constater que son champ
`independent_validation_protocol_sha256` correspond au protocole builder
source exact.

## Ce que l'étape ultérieure pourra faire, et rien de plus

Après revue externe de ce contrat, une unique lecture/revalidation pourra :

1. vérifier le SHA-256 canonique du JSON de registre ;
2. rehacher les `30` audio et les `30` labels de la cohorte scellée ;
3. comparer identité, groupe de fuite, `audio_member`, taille et SHA-256 ;
4. retourner la capacité validée, puis s'arrêter.

Elle restera interdite de décoder les actifs, de charger un modèle, d'exécuter
la transcription, d'évaluer V2, de fitter, calibrer, exporter, utiliser le
live ou d'ouvrir le test verrouillé. Elle ne donne pas non plus droit à une
seconde construction du registre : `builder_authorized_now=false`.

## Vérifications sans actifs

Le test versionné du protocole vérifie son SHA exact, l'action unique autorisée,
les flags builder/reader et les deux SHA scellés. Les suites suivantes sont
rejouées avant commit avec des fixtures synthétiques seulement :

```text
14 tests V2 purs
44 tests provenance/V2 ciblés
py_compile
git diff --check
```

La seule action suivante est une revue externe de ce contrat lecteur. Aucun
registre réel n'a été relu durant cette étape.
