# Construction unique de la preuve byte-level V2 indépendante

## Autorisation consommée

Après l'approbation externe du commit `e241bd8`, l'unique construction
autorisée a été exécutée sur le Mac, car le manifeste et les actifs ne sont pas
présents dans le worktree Windows. Cette opération ne relève pas d'un runner
scientifique : elle calcule uniquement taille et SHA-256, sans décoder les
audio/labels et sans charger TensorFlow, modèle ou checkpoint.

Préflight avant construction :

```text
checkout Mac              = e241bd862237b167ea69816b74c36b1af8b38ceb
worktree Git              = propre
manifeste                 = présent
processus polyphonique    = absent
destination               = absente
protocole builder SHA-256 = d63655c388991f3782a738e5bba58f0409ae79f297a3d5009dab7971349ba015
builder_authorized_now    = true
reader_authorized_now     = false
locked_test_used          = false
```

## Résultat publié

Le builder a produit exactement une entrée par prise de la cohorte scellée :

```text
destination : /Users/amcarene/midi/tmp/local/causal_candidate_v2_independent_validation_asset_evidence_20260810.json
size_bytes  : 17873
sha256      : 10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee
entries     : 30
recording_keys : 30
asset_types : audio, labels
manifest_sha256 : b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7
independent_validation_protocol_sha256 : d63655c388991f3782a738e5bba58f0409ae79f297a3d5009dab7971349ba015
locked_test_used : false
```

La publication a employé l'écriture atomique sans écrasement du builder déjà
testé. Un contrôle post-publication a retrouvé exactement `17 873` octets et
le même SHA-256, sans fichier `.part` résiduel. Le registre est sous `tmp/`,
donc volontairement non versionné; le worktree Git Mac est resté propre.

## Fermeture immédiate du builder

L'autorisation builder est consommée. Le protocole courant est maintenant
refermé et scellé au SHA-256 :

```text
79c11de0d1a9cfc25f0d2de6bd5228e4a29a85e1e7c3eebecbe569db585cd0e7
```

Il impose de nouveau :

```text
allowed_now               = external_review
builder_authorized_now    = false
reader_authorized_now     = false
source_evidence_protocol_sha256 = null
expected_evidence_sha256  = null
```

Ainsi, aucun second builder ne peut démarrer via le protocole versionné.

## Limites et prochaine action

Le JSON publié n'a pas été relu, validé ni utilisé. Cette étape n'autorise pas
le modèle, la transcription, une évaluation V2, un entraînement, une
calibration, une exportation, le live ni le test verrouillé.

La seule action suivante est une revue externe de cette construction. Si elle
l'approuve, une étape distincte devra d'abord sceller un protocole lecteur qui
porte simultanément :

1. le SHA-256 du registre publié `10307a64…22aee` ;
2. le SHA-256 du protocole builder source `d63655c3…9ba015`.

Seul ce futur protocole pourra autoriser lecture et rehash du registre avant
toute ouverture d'actif ou calcul V2.
