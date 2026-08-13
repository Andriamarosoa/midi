# H27 - artefact administratif d'autorite d'execution du constructor

La revue externe de `46a6bdf81a56a7a7a10524d4e55092301a452207`
conclut `PASS`. Ce lot cree uniquement l'artefact administratif conforme au
schema PASS et son seal externe. Il n'ouvre aucun registre et n'invoque pas le
constructor.

Le `expected_git_head` est choisi explicitement comme
`46a6bdf81a56a7a7a10524d4e55092301a452207`, dernier commit PASS qui scelle
le contrat et son binding. Il n'est pas derive automatiquement du HEAD pendant
la construction. L'identite de l'artefact est
`45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e`,
calculee par la formule SHA-256 scellee.

Les quatre identites du contrat/binding et leurs 108 predecesseurs forment 112
chemins uniques rehashes. Huit edges restent fermes. Registre, reservation,
invocation, destination, filesystem, materializer, population et science
restent interdits.

Identite exacte de l'artefact : blob
`fedcf0f1c2be368ddf619e8f1715a55f499815c8`, `688` octets, SHA-256
`dccc4afaf20390fe07226fbfd237c06b381b203d25f6f80908adc3753c985296`.
Seal : blob `4f3e49d29e5777b1ad5174b24870ac21f348ac78`, `1683` octets,
SHA-256 `5b2b985f694b1e360afc9aec84a6ba8329cf6bc7b4cfea106a67108ac550decc`.

Validation locale : `3/3` tests administratifs et `385/385` tests H27.
