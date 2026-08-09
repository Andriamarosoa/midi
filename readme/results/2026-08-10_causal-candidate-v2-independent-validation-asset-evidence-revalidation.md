# Revalidation unique de la preuve byte-level V2 indépendante

## Portée consommée

Après l'approbation externe du contrat lecteur `e667a5c`, une seule
revalidation a été exécutée sur le Mac. Elle est bornée à la lecture du JSON
canonique, à la vérification de ses liens de provenance et au rehash des 60
fichiers déclarés. Elle ne décode aucun actif et ne charge ni TensorFlow, ni
modèle, ni checkpoint.

Préflight :

```text
checkout Mac                   = e667a5c532eb26c5656cc46be11f7060624a81cf
worktree Git                   = propre
registre                       = présent
manifeste                      = présent
processus polyphonique         = absent
protocole lecteur SHA-256      = 6bf7619a109e6141470a99eacd4eaecf83edaf7ce0fd76bb03bc60e5bfc8ab3e
builder_authorized_now         = false
reader_authorized_now          = true
locked_test_used               = false
```

## Résultat de revalidation

```text
validation_completed           = true
evidence_path                  = /Users/amcarene/midi/tmp/local/causal_candidate_v2_independent_validation_asset_evidence_20260810.json
evidence_sha256                = 10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee
expected_evidence_sha256       = 10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee
source_evidence_protocol_sha256 = d63655c388991f3782a738e5bba58f0409ae79f297a3d5009dab7971349ba015
manifest_sha256                = b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7
entries / recording_keys       = 30 / 30
asset_types                    = audio, labels
rehash                         = 30 audio + 30 labels, tous conformes
locked_test_used               = false
```

La fonction de validation a aussi vérifié pour chaque entrée l'identité, le
groupe de fuite, `audio_member`, taille et SHA-256 des deux fichiers, puis la
liaison du registre au protocole builder exact. Elle a créé la capacité validée
en mémoire et le processus s'est terminé immédiatement après le rapport.

## Fermeture du lecteur

Le protocole courant est immédiatement refermé au SHA-256 :

```text
def274de1d1c738c7d4342f8f16ef2aaab99e9b2f87d6641d012d36ab6a34119
```

Il impose :

```text
allowed_now                    = external_review
builder_authorized_now         = false
reader_authorized_now          = false
source_evidence_protocol_sha256 = null
expected_evidence_sha256       = null
```

Une seconde construction ou revalidation échoue donc avant tout hachage ou
accès au registre via le protocole versionné.

## Arrêt explicite

Cette étape ne fournit aucune métrique scientifique et ne constitue pas une
évaluation V2. Elle n'autorise pas l'ouverture/décodage des actifs, le modèle,
la transcription, l'inférence, l'évaluation, le fit, la calibration, l'export,
le live ou le test verrouillé.

La seule suite est une revue externe de la provenance complète désormais
validée, suivie — si elle est explicitement approuvée — de la définition d'un
nouveau contrat d'exécution scientifique. Aucun calcul réel supplémentaire
n'est autorisé ici.
