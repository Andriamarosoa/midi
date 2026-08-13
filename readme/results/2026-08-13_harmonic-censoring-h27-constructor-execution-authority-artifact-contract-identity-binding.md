# H27 - binding du contrat de l'artefact d'autorite d'execution

La revue externe de `55bd7a533952d1ead5d7611580a066e7505698f4`
conclut `PASS`. Ce lot ajoute uniquement l'identity binding administratif du
contrat exact et son seal externe. Contrat + seal + 108 predecesseurs forment
110 chemins uniques rehashes.

Le binding preserve le schema ferme a sept champs, le `expected_git_head`
lowercase hex40 futur sans valeur concrete, l'identite derivee, le single-use,
les regles strict JSON/canonicales et les six regles du futur artefact. Huit
edges restent fermes. Aucun artefact runtime, registre, reservation,
invocation, destination, filesystem, materializer, population ou science
n'est ouvert.

Identite exacte du binding : blob
`71439f93f56f5f499ba29d6ee7fe334ed2421735`, `3340` octets, SHA-256
`1907b841a9defa5a9b3ac61ffc3660be6fb5447d63044d0816e8b2c94aae5d4d`.
Seal : blob `ed4a944d70d49e33c66d0d73f04a2e3a682cb79c`, `1530` octets,
SHA-256 `02c01af0276f98e91c992b566c95a33b8354ca57b80fa1cb3c056dc2a7954b06`.

Validation locale : `3/3` tests administratifs et `382/382` tests H27.
