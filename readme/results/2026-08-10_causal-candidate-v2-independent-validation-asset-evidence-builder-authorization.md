# Autorisation séparée du builder de preuve d'actifs V2 indépendante

## Portée

La seconde revue externe du correctif de provenance `5fd4fc8` est approuvée.
Cette étape ne construit aucun registre : elle scelle uniquement le protocole
qui autorisera l'unique construction byte-level de la preuve d'actifs pour la
cohorte indépendante V2 de 30 prises validation.

Le commit ne lit aucun audio ou label du projet, ne charge ni TensorFlow, ni
modèle, ni checkpoint, ne contacte pas le Mac et ne lance ni inférence, ni
évaluation, ni fit, ni calibration, ni export, ni live, ni test verrouillé.
`locked_test_used=false` reste inchangé.

## Nouveau protocole scellé

Le fichier canonique
`configs/causal_candidate_fit_v2_independent_validation_protocol.json` a pour
SHA-256 :

```text
d63655c388991f3782a738e5bba58f0409ae79f297a3d5009dab7971349ba015
```

Il fixe exactement :

```text
status                       = independent_validation_asset_evidence_builder_authorized
allowed_now                  = independent_validation_asset_evidence_build
builder_authorized_now       = true
reader_authorized_now        = false
source_evidence_protocol_sha256 = null
expected_evidence_sha256     = null
```

L'autorisation est donc volontairement à sens unique. Elle permet seulement au
builder contrôlé de hacher les 30 audio et 30 labels sélectionnés et de publier
sans écrasement un JSON canonique. Elle ne permet pas de lire, valider ou
employer ce JSON : une étape ultérieure devra inscrire à la fois le SHA-256 de
ce registre et le SHA-256 du présent protocole de construction.

## Garde-fous conservés

- le loader de cohorte exige toujours l'instance attestée et les octets exacts
  du protocole, du manifeste et de la sélection historique ;
- build, publication, parsing, validation et vérification à l'ouverture restent
  des capacités distinctes ;
- la publication rehache les 60 fichiers juste avant l'écriture atomique et
  sans remplacement ;
- aucune API lecteur ne peut démarrer tant que `reader_authorized_now=false` ;
- le lecteur de manifeste reste pur et sans TensorFlow.

## Vérifications locales sans actifs projet

Cette autorisation ajoute une assertion versionnée sur le statut, l'action
unique autorisée et les quatre champs du contrat de preuve. Avant commit :

```text
python -m unittest \
  tests.test_causal_candidate_v2_independent_asset_evidence \
  tests.test_run_causal_candidate_v2_independent_validation

py_compile des modules modifiés
git diff --check
```

Ces tests utilisent uniquement des fichiers factices temporaires ; aucun actif
du projet, modèle, checkpoint, Mac ou calcul scientifique n'est concerné.

## Suite explicitement bornée

La prochaine opération possible est une revue externe de ce protocole, puis,
seulement si elle l'approuve, une construction unique de la preuve byte-level.
Cette future construction devra s'arrêter après publication et rapporter le
chemin, la taille et le SHA-256 du registre. Elle ne donne aucune autorisation
de lecture, d'évaluation V2 indépendante ou de promotion.
