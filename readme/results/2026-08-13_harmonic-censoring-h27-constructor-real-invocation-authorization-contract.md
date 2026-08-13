# H27 - contrat de future autorisation d'invocation reelle du constructor

La revue externe de `df0c4996fe3118197985ffb4aead9e0588681396`
conclut `PASS`. Cette etape ajoute uniquement le contrat declaratif et son seal
pour une future autorisation distincte. Module, module seal, binding, binding
seal et 100 identites amont forment 104 chemins uniques rehashes.

L'ordre fail-closed futur impose notamment rehash et types natifs avant runtime,
registre persistant puis reservation terminale avant une invocation unique,
observation destination seulement apres, create-exclusive et aucun retry.
Aucune de ces operations n'est autorisee ni executee ici; les huit edges restent
fermes.

Identites corrigees : contrat blob
`c5262db444bc0852403cfd76770470946b53abdb`, `5836` octets, SHA-256
`6f4557d33d0134057a84b6adaf5a18fc57b77117a2eedc034b91615c82ddd2bb` ;
seal blob `1657b358595c1864f147b5a07c56e0f910eb7d81`, `1520` octets,
SHA-256 `308b991d3adb78f012c60fda205171ec89db7d5eaedea76e9b2035491721b486`.

Validation locale : `3/3` tests administratifs et `373/373` tests H27.

Correction apres revue : un futur artefact d'autorite distinct/revu/scelle doit
lier un `expected_git_head` natif exact en hex40 minuscule. Le runtime devra
imposer `HEAD == expected_git_head` et un worktree propre avant le rehash104;
aucun fallback vers le HEAD courant ni selection automatique n'est permis.
