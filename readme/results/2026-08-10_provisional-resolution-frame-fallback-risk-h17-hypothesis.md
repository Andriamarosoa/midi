# H17 — hypothèse de risque des NoteOn `frame_fallback`

## Portée

H17 est un contrat scientifique sans exécution. Aucun audio, label
scientifique, modèle, checkpoint, signal, target, métrique ou bootstrap n'a été
ouvert ou calculé. Aucune cohorte n'est sélectionnée ou consommée.

H7 reste `inconclusive_fail_closed`, H8 reste définitivement consommé pour H7,
H14/H15 restent clos et H16 reste une infrastructure future uniquement.

## Question unique

Parmi les NoteOn du chemin d'activation audio-aware pour pitch inactif, les
émissions dont la raison causale figée est `frame_fallback` sont-elles
matériellement enrichies en faux NoteOn causaux par rapport aux raisons :

```text
model_onset
frame_attack
chord_completion
```

L'exposition primaire est uniquement :

```text
F = 1  si candidate_reason_at_noteon == frame_fallback
F = 0  pour les trois raisons comparatrices exactes
```

`retrigger` et `legacy` sont exclus par chemin avant observation des résultats,
mais leurs comptes devront être rapportés. Toute nouvelle raison inattendue
fera échouer l'exécution future au lieu d'être regroupée silencieusement.

H17 ne teste ni persistance age-1, ni autre âge, ni S0/S1/D1, ni resolver,
seuil de rejet ou amélioration des événements du décodeur.

## Target et mesure

Le target réutilise sans modification le matcher causal existant, same-pitch,
one-to-one, sans référence future et à latence maximale `250 ms` :

```text
false_noteon = 1 - true_noteon
```

Les lignes non matchables restent exclues. La mesure primaire est la différence
de risque :

```text
RD_false = P(false_noteon=1 | F=1) - P(false_noteon=1 | F=0)
```

Le verdict positif exact exige simultanément :

- au moins `200` NoteOn éligibles ;
- au moins `50` NoteOn `frame_fallback` ;
- au moins `50` comparateurs ;
- `RD_false >= 0,10` ;
- borne basse de l'IC 95 % par groupes strictement supérieure à `0,0`.

Le bootstrap futur est figé à `10 000` réplications, seed `721629268`, unité
`leakage_group_key`, univers de groupes exact et scellé, `9 500` réplications
valides minimum et percentiles linéaires `[2,5 ; 97,5]`. Les groupes sans ligne
H17 resteront dans l'univers et contribueront zéro ligne lorsqu'ils sont tirés.

## Cohorte future

H17 ne choisit aucune prise :

```text
future_cohort_selection  null
recording_identities     null
asset_hashes             null
data_access_authorized   false
```

Après approbation seulement, un audit H18 distinct pourra examiner les
métadonnées pour soustraire tous les groupes H8, V2 consommés, test verrouillé
et, lorsque la provenance l'établit, ceux vus pendant le fit du checkpoint.
Tous les groupes `fresh_unseen_groups` admissibles devront être conservés. Il
en faudra au moins `20`; sinon l'état sera
`fresh_discovery_population_not_established` et une nouvelle acquisition de
données ou un autre contrat sera nécessaire.

Cette future cohorte ne pourra pas être appelée validation indépendante avant
une preuve de provenance séparée.

## Bindings

- commit H16 approuvé : `31d36165e65399750342159fef591fe65d4f7ce5` ;
- clôture H14/H15 : `dc295f773f83e61549d981ef572ccf5a660a9174` ;
- blob orchestrateur H16 : `80d7d17361a69203526dc40f79a9b2659dfc916d` ;
- contrat H5 : `df95797ff31993c021cd8f799f844c50aadd1351` ;
- taxonomie raison/décodeur revue : `27026d368081fadc4fa282954428f0377020e723` ;
- blobs target : `c63b9751e5acef49fb51b5e2a8264b00d6e60893`,
  `98c3f2e87b89df599e71068ab4ae874f69172c5a`,
  `42f7954b75b0994f43d7f59c62c1ff1b04c0a81d` ;
- grouping : `e43187b4e8ba0775a74114faf406703dd6c3187c` ;
- cohorte H8 consommée :
  `4dd76bd13c33ccb3946bfdbcf6f575d4550fb0c5588095e23da3b6e3f84bce1f`.

H12/H13 ne sont pas modifiés ni rendus exécutables.

## Interdictions et état

Les scores, probabilités, preuves audio, polyphonie, S0/S1/D1, interactions,
recherche d'âge, seuil et classifieur sont interdits comme entrées primaires.
Aucun résultat descriptif ou sous-groupe ne pourra sauver le verdict primaire.
Aucun inconclusif n'autorise un retry automatique.

```text
contract_only                    true
cohort_selected                  false
data_access_authorized           false
scientific_execution_authorized  false
signals_extracted                false
targets_extracted                false
metrics_computed                 false
model_loaded                     false
h8_reused                        false
consumed_v2_reused               false
locked_test_used                 false
```

La seule prochaine action est la revue externe de H17. Aucun audit H18, code
scientifique ou accès aux données ne suit automatiquement ce commit.

## Validation structurelle locale

`17` tests H17 + H7 ont réussi en `0,003 s`. `py_compile` et
`git diff --check` ont réussi. Aucun fichier sous `src/` n'est modifié.

Empreintes Git avant commit :

- contrat H17, `11 180` octets :
  `f8d8e71f8d2b98955c2e19fedf2f4019ab4cca2f` ;
- test structurel : `80e82338e9c0468602ac91cf5d0577eadf26edeb`.
