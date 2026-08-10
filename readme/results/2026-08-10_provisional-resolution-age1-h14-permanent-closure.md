# H14/H15 — échec post-consommation et clôture permanente

## Classification finale

```text
H14 classification
post_consumption_runtime_failure_scientific_result_indeterminate

H7 terminal outcome
inconclusive_fail_closed

terminal status
provisional_resolution_age1_persistence_h14_closed_inconclusive_after_consumed_runtime_failure

root-cause status
h14_runtime_failure_root_cause_not_identified
```

Ce résultat n'est ni positif ni négatif. H8 est définitivement consommée pour
H7 et aucun retry n'est autorisé.

## Exécution et provenance persistante

- HEAD d'exécution : `9f498c36022f2d8043843bbab2e7fffa6d7d177b`;
- contrat H13 :
  `76e40426921c3c972adc465a5197136d3ff675d15504816aa5f149878dd0bd0d`;
- SHA du payload authorization/claimed :
  `1a6ea8ac4f77b8d3ffc8ca1a2b51c33ac8f38a72997eb6254027e67b0cd839af`.

État final relevé en lecture seule :

```json
{
  "authorization_json": "absent",
  "authorization_claimed": "present",
  "authorization_claimed_state": {
    "h8_discovery_consumed": true,
    "state": "claimed_running"
  },
  "final_result_directory": "absent",
  "failure_json": {
    "contract_sha256": "76e40426921c3c972adc465a5197136d3ff675d15504816aa5f149878dd0bd0d",
    "error_type": "RuntimeError",
    "h8_discovery_consumed": true,
    "state": "failed"
  },
  "runner_process": "absent",
  "mac_worktree": "clean"
}
```

Les fichiers `.claimed`, `.claimed.state.json` et `.failure.json` n'ont été ni
renommés, ni supprimés, ni modifiés.

## Déroulement opérationnel

La première commande de lancement s'est arrêtée avant import avec
`No module named src.polyphonic.provisional_resolution_age1_h13`. Le marqueur
était encore non réclamé et H8 non consommée. La revue externe a autorisé une
unique invocation de remplacement avec le même marqueur et un `PYTHONPATH`
absolu. Cette invocation a réclamé l'autorisation, franchi la frontière H11 et
a terminé environ vingt minutes plus tard avec `RuntimeError`. Aucun stdout ou
stderr persistant plus précis n'était disponible.

## Audit statique H15 des sites candidats

L'audit porte exclusivement sur le code au HEAD d'exécution. Les contrôles de
preflight avaient réussi avant le claim; les erreurs préflight ne sont donc pas
retenues comme cause post-consommation, sauf mutation externe non prouvée.

| Phase | Sites `RuntimeError` post-consommation atteignables | Niveau de preuve |
|---|---|---|
| asset/opening | construction/accès `PolyphonicCorpus`, labels ou audio par l'adapter | possible; aucun message conservé |
| inference/model | CPU/GPU fail-closed, chargement Keras, `predict_compat`, type ou nombre de frames de sortie | possible; le modèle n'était chargé qu'après consommation |
| decoder | garde du seuil baseline, erreurs internes de `decoder.step`, identité passive age-1 dupliquée | possible; aucune phase persistée |
| end-of-stream | `require_no_pending_age1_at_end()` ou `pending_age1 != 0` | possible; messages perdus |
| target extraction | partition causal match/false non exacte ou erreur RuntimeError d'un composant appelé | possible |
| signal/target reconciliation | identités dupliquées/différentes ou comptes emitted/signal/target divergents | possible |
| metric evaluation | AUC hors `[0,1]`, percentile bootstrap non fini, ou RuntimeError d'un composant appelé | possible; AUC en mémoire ni prouvée ni exclue |
| final publication | RuntimeError d'un composant de sérialisation/publication ou provenance d'échec déjà existante | théoriquement atteignable; les erreurs fichier natives seraient normalement d'un autre type |
| other operational | RuntimeError d'une dépendance appelée non détaillé par H11 | possible |

La durée observée ne prouve aucune phase. L'absence du résultat final prouve
seulement que la publication atomique n'a pas abouti. Le seul `error_type` ne
permet pas de sélectionner l'un des sites candidats.

## État scientifique obligatoire

```text
H8 consumed                         true
H7 final scientific report exists  false
AUC proven produced                false
AUC proven absent                  false
scientific result state            indeterminate
H7 verdict                         inconclusive_fail_closed
retry                              forbidden
locked test used                   false
consumed V2 cohort reused          false
```

Aucun audio/label H8 n'a été rouvert, aucun modèle chargé, aucune inférence
relancée, et aucun S0/S1/D1, target, équilibre de classes, ligne partielle, AUC
ou bootstrap n'a été inspecté ou reconstruit pendant H15.

## Limite de provenance et recommandation future

H11 persiste uniquement `error_type`, ce qui est insuffisant pour localiser un
échec post-consommation. Une future infrastructure distincte pourrait enregistrer
avant chaque phase un identifiant non scientifique, puis conserver phase,
message d'erreur borné et traceback opérationnelle. Cette recommandation
n'autorise ni une correction rétroactive, ni un retry H14, ni le réemploi de H8.
