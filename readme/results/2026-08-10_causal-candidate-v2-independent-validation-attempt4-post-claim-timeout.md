# Attempt4 — clôture provenance-only après timeout post-claim

## Classification

```text
status = post_claim_execution_timeout_scientific_phase_indeterminate
attempt4_authorization_consumed = true
scientific_phase = indeterminate
ab_metrics_produced = unknown
ab_metrics_observed = false
independent_v2_verdict = inconclusive_fail_closed
automatic_retry = false
locked_test_used = false
```

L'unique invocation Attempt4 autorisée a été exécutée au commit
`df2a2a0641d7897195ee0712002bcc48e97858e6`, avec la request SHA-256
`70650da50ceb796e29b4e179dcd824487c94bf0201fd98b63c4aa098d74bc12b`
et l'approval externe de `416` octets, SHA-256
`92cd94b5c9ecd9751e0aa42a582ef105b0ec4003021d8d3a25d1ddb8ea71a73e`.

Le wrapper Python scellé a exécuté l'entrypoint avec le Python du venv Mac et
un timeout externe de `900 s`. Il a ensuite levé exactement
`subprocess.TimeoutExpired` après `899.9999793339812` secondes. Aucun retry n'a
été effectué après la création du marker.

## État durable observé après l'arrêt

```text
HEAD = df2a2a0641d7897195ee0712002bcc48e97858e6
git status --short = vide
processus wrapper = absent
processus enfant = absent
marker_present = true
marker_size = 628
marker_sha256 = 00c677be7d78771e1b8c82d6bdf394dc8c9af64441a7f12f99c02f832908f1b0
destination_present = true
destination_present_empty = true
lock_present = true
lock_size = 0
published_report = absent
published_metrics = absent
```

La présence simultanée du marker, de la destination et du lock prouve que le
runner a franchi les préflights et est entré dans la section sous lease. Elle ne
permet pas de déterminer s'il a timeout avant la première ouverture d'actif,
pendant l'inférence ou après la création d'un premier résultat A/B uniquement
en mémoire. L'absence de rapport prouve seulement qu'aucune métrique n'a été
publiée ou observée ; elle ne prouve pas qu'aucune métrique n'a été produite.

## Décision fail-closed

Attempt4 est définitivement consommée. Le marker, la destination et le lock
restent intacts. Aucun nettoyage destiné à autoriser une relance n'est permis.
La cohorte ne peut plus être présentée comme indépendante pour une nouvelle
validation V2. V2 est donc close avec un verdict indépendant inconclusif et
fail-closed, sans promotion du modèle ou du seuil.

Ce rapport est documentaire et provenance-only. Il n'a nécessité aucune
lecture d'audio ou de labels, aucun TensorFlow, aucune inférence, aucun calcul
de métrique et aucun accès au test verrouillé.
