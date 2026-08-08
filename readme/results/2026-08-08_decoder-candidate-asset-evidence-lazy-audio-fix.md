# Correctif de lecture audio paresseuse — contrat d'actifs candidats

## Portée

- Branche : `codex/independent-note-neural-v2`.
- Point de départ revu : `7440d093ffc4d5e2a533a05cf53053429d753b85`.
- Nature : garde-fou d'ouverture et tests synthétiques uniquement.
- Aucun manifeste réel, plan réel, registre réel, actif du projet, modèle,
  décodeur, minage, entraînement, évaluation, export, live ou test verrouillé
  n'a été ouvert, produit ou exécuté.

## Anomalie corrigée

La revue de `7440d093` a confirmé le registre d'empreintes, mais a relevé une
fenêtre TOCTOU avant minage : `PolyphonicCorpus` charge les labels dans son
constructeur, tandis que l'audio est chargé plus tard par `corpus.audio()`.
Une vérification faite seulement avant le constructeur ne garantissait donc pas
les octets réellement lus par ce chargement paresseux.

Le contexte officiel attache désormais deux vérificateurs au même
`ManifestItem` issu du snapshot attesté :

```text
labels : SHA/tailles vérifiés juste avant np.load() dans le constructeur
audio  : SHA/tailles vérifiés juste avant np.load()/ZipFile/soundfile dans audio()
```

Les deux vérificateurs rejettent aussi tout objet qui ne serait pas exactement
le `ManifestItem` du snapshot. Dans le chemin protégé, le chargement `.npy`
désactive le `mmap` : les octets lus après vérification sont matérialisés lors
de ce chargement, au lieu d'être demandés paresseusement à l'OS plus tard.

Le registre et le plan persistent restent revérifiés à chaque vérification.
Un registre, plan, identité, partition, membre d'archive, taille ou digest
incompatible échoue avant que le corpus ne lise l'actif concerné.

## Tests ajoutés

1. Un corpus NumPy/NPZ synthétique complet suit le chemin public exact :

   ```text
   création du plan temporaire
   -> pre_register_decoder_candidate_asset_evidence
   -> relecture du contexte
   -> open_recording réel
   -> mutation de l'audio après construction du corpus
   -> corpus.audio() refuse avant np.load()
   ```

   Le même test vérifie qu'une mutation des labels échoue au chargement réel du
   constructeur. Aucun mock ne remplace `PolyphonicCorpus` dans ce test.

2. Deux captures synthétiques qui partagent le même conteneur audio vérifient
   que la préinscription appelle `_digest_file` une seule fois pour ce chemin
   résolu. Les labels distincts restent hachés chacun une fois.

## Vérification locale

La compilation Python, `git diff --check` et la suite ciblée complète ont été
rejoués sur Windows :

```text
Ran 136 tests in 9.718s
OK
```

La suite couvre notamment l'instrumentation, provenance, retriggers,
snapshot/plan, registre d'actifs et ce nouveau chargement paresseux. Les
fichiers créés sont tous sous des répertoires temporaires de test.

## Décision et limites

Le correctif ferme la fenêtre identifiée avant un futur minage sur le chemin
officiel. Il ne constitue pas une préinscription des actifs du projet et
`locked_test_used=false` reste inchangé.

Une revue externe de ce petit correctif est requise avant toute préinscription
réelle sur le Mac. Après approbation explicite seulement, la préinscription
réelle du plan et du registre sera elle-même soumise à revue avant toute
collecte train-only.
