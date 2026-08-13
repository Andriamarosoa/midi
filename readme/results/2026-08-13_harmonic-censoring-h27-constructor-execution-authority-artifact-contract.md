# H27 - contrat de l'artefact d'autorite d'execution du constructor

La revue externe de `a786d5730b488694728088368a33e7584f8f13e7`
conclut `PASS`. Ce lot definit uniquement le schema ferme du futur artefact
d'autorite d'execution et son seal externe. Il ne cree pas cet artefact et ne
selectionne aucune valeur concrete de `expected_git_head`.

Le schema futur impose sept champs ordonnes, des types JSON natifs exacts, un
`expected_git_head` lowercase hex40 fourni dans un commit distinct revu et
scelle, et une identite hex64 derivee du HEAD attendu et de la chaine
d'autorisation. Tout fallback vers le HEAD courant est interdit.

Les quatre identites PASS/scellees de l'autorisation d'invocation et leurs 104
predecesseurs forment 108 chemins uniques a rehasher. Les huit edges publics
restent fermes. Aucun registre, reservation, invocation, destination,
filesystem, materializer, population, science, locked-test, entrainement ou
calibration n'est autorise.

Identite exacte du contrat : blob
`2cb37c422877dea184811cd66f7b48d47ad034db`, `5915` octets, SHA-256
`4a6539a5a4e85f5017919a6b676ed06587405fdbb06360cea386aee6513be86e`.

Validation locale : `3/3` tests administratifs et `379/379` tests H27.
