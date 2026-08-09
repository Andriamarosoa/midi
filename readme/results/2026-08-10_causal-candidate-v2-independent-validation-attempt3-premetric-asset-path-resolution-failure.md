# Attempt3 — échec pré-métrique de résolution des actifs

Attempt3 a été exécutée exactement une fois au commit
`bc3e805971fed0fec4b76c817b5ee34289601624`. Son marker persistant est
conservé, SHA-256
`41da74ab8f0894b5236f33e68e8fafa163830021d6be38b282e73b0fd5d10939`.

Le registre worker a passé son contrôle, puis `Path.resolve(strict=True)` a
échoué sur
`/Users/amcarene/midi-worker/repository/data/processed/polyphonic_v2_1_gaps`.
La destination attempt3 est absente et le lock est absent. TensorFlow
scientifique, modèle, audio/labels, inférence, A/B et métriques n'ont pas été
atteints. L'autorisation attempt3 est consommée; la cohorte scientifique ne
l'est pas et aucune métrique n'a été produite ou observée.

Le diagnostic TensorFlow-free ultérieur a établi que le data-root correct est
`/Users/amcarene/midi-worker/data`. Avec `MIDI_DATA_ROOT` fixé à cette valeur,
les 270 lignes GAPS résolvent vers `polyphonic_v2_1_gaps` et les 92+92 lignes
Guitar-TECHS vers la racine réelle partagée `polyphonic_v2_2_guitar_techs`.
Les 454 chemins audio et 454 chemins labels distincts existent et sont des
fichiers. Seules existence et type ont été interrogés : aucun contenu actif
n'a été ouvert ou haché et TensorFlow est resté absent.

Attempt4 reste une demande sans approval ni marker réel. Son préflight doit,
avant marker, dériver `worker_root/data`, fixer/refuser `MIDI_DATA_ROOT`,
reconstruire la cohorte scellée et vérifier existence, type, canonicalité et
absence de symlink pour les 30 audio et 30 labels exacts. Le runner, l'evidence
gate, les protocoles et toute science restent inchangés.

Validation locale synthétique uniquement : `py_compile`, `88` tests ciblés
réussis en `4,779 s`, `git diff --check`, et blobs scientifiques inchangés.
