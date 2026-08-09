# Contrat d'exécution déclaratif — validation V2 indépendante

## Portée de ce commit

Ce commit ne crée ni runner exécutable, ni job Mac, ni capacité de lecture des
actifs. Il scelle uniquement la future expérience A/B indépendante après la
revalidation byte-level déjà close. Aucun audio, label, registre, modèle,
checkpoint, TensorFlow, inférence, métrique, fit, calibration, export, live ou
test verrouillé n'a été ouvert ou exécuté.

## Nouvelle ancre immuable

Le nouveau fichier versionné, en LF explicite, est :

```text
configs/causal_candidate_fit_v2_independent_validation_execution_contract.json
SHA-256 = 269efb65f225cf2522eab895cf59c351bea6bb97bc20229160f611c5e3ae63ed
```

Son unique état autorisé est :

```text
status      = independent_validation_execution_contract_pending_external_review
allowed_now = external_review
```

Il interdit explicitement le builder/lecteur de preuve, le décodage d'actifs,
le chargement de modèle, l'implémentation du runner, l'exécution réelle, fit,
calibration, recherche de seuil, réutilisation historique, export, live et
test verrouillé. `locked_test_used=false` reste exigé.

## Provenance et intervention gelées

Le contrat relie simultanément :

```text
protocole indépendant fermé      = def274de1d1c738c7d4342f8f16ef2aaab99e9b2f87d6641d012d36ab6a34119
registre d'actifs indépendant    = 10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee
protocole builder source         = d63655c388991f3782a738e5bba58f0409ae79f297a3d5009dab7971349ba015
manifeste                         = b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7
sélection historique V1          = 8c3cf53c7f5dcf086b70767e28499c3164aa307059652a6d0a2fc87159f9dcbc
plan Policy A                    = a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4
```

La population est fixée à `30` prises validation et `20` groupes indépendants
(`10` GAPS, `10` Guitar-TECHS direct input, `10` Guitar-TECHS mic/amp,
`0` GuitarSet). Les clés/groupe historiques et les groupes train Policy A
restent exclus. L'absence de GuitarSet est une limite de portée et ne peut
jamais devenir une conclusion d'effet nul.

L'intervention est strictement identique à V2 : checkpoint transcription,
modèle V1, standardiseur, `12` features causales pré-ranking, politique audio,
seuil `0,31` et placement `post_ranking_pre_noteon`. La référence reste sans
porte ; A et B devront partager une unique inférence et les mêmes masques
audio, puis garder deux états de décodeur indépendants après divergence.

## Conditions exigées pour un futur runner

Le futur code, qui n'est **pas** ajouté ici, devra être revu sans exécution
puis lié à une autorisation d'invocation séparée au commit exact. Avant tout
modèle ou actif, il devra notamment :

1. rehacher ce contrat, le protocole fermé et la sélection historique ;
2. redériver les 30 prises depuis le manifeste complet ;
3. vérifier toutes les empreintes V1/V2 ;
4. rehacher le registre canonique et les `30` audio + `30` labels dans le même
   processus, puis ouvrir seulement les objets attestés ;
5. exiger CPU, worktree propre, commit exact, absence de job lourd et
   destination fraîche ;
6. appliquer V2 après ranking/sélection et avant NoteOn, sans backfill ;
7. publier le rapport puis s'arrêter, sans retry automatique.

Le futur rapport devra fournir les métriques A/B globales, par corpus, par
prise et par groupe indépendant, avec provenance complète. La décision est
déjà figée : réduction causale globale d'au moins `1 %`, aucune régression
corpus par corpus des faux NoteOn, limites de rappel/F1/latence, pas de hausse
de retriggers ou fragmentation, jamais de promotion automatique.

## Vérification locale sans données projet

```powershell
$py='C:\Users\user\Desktop\midi\.venv\Scripts\python.exe'
& $py -m py_compile `
  src\polyphonic\causal_candidate_v2_independent_validation_execution_contract.py `
  tests\test_causal_candidate_v2_independent_validation_execution_contract.py
& $py -m unittest `
  tests.test_causal_candidate_v2_independent_validation_execution_contract `
  tests.test_causal_candidate_v2_independent_asset_evidence `
  tests.test_run_causal_candidate_v2_independent_validation
```

Résultat : `19` tests réussis en `1,650 s`. Les tests ne chargent ni
TensorFlow ni actif projet. Ils vérifient l'empreinte LF, le statut
external-review only, les trois liens de provenance clés, le refus d'un
contrat construit à la main, le refus d'une mutation d'autorisation ou de
chemin, et l'échec du digest avant tout parsing JSON.

## Durcissement issu de la revue externe

Le contrat encode maintenant une consommation strictement one-shot : une
erreur n'est premetric_infrastructure_failure que si elle survient avant
tout actif scientifique, toute inférence et toute métrique A/B. Dès qu'une
métrique est produite ou observée, la cohorte est consommée ; toute analyse
ultérieure est exploratoire et ne restaure jamais l'indépendance.

Le futur rapport est scellé par vues reference, candidate et delta, avec une
liste explicite de métriques et de granularités. Toute valeur absente, non
numérique, non finie ou mal structurée force un verdict non positif.

Cette correction reste contract-only : aucun runner, actif, modèle,
TensorFlow, inférence ou calcul scientifique n'a été ajouté ou exécuté.

## Suite unique

Revue externe de ce contrat déclaratif. Si elle est approuvée, la seule étape
suivante possible sera une implémentation synthétique et fail-closed du runner,
sans ouvrir les actifs ni charger les artefacts V1. Une exécution scientifique
restera soumise à une autorisation séparée.
