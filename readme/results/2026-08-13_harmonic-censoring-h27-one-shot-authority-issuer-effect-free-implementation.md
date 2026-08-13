# H27 - implementation effect-free de l'issuer one-shot

La revue externe de `cb581c7e989715b808a8334127dd1dd50ad816fd`
conclut `PASS` et autorise uniquement une implementation dormante avec adapters
fake ou in-memory.

Le module rehache les 78 identites avant toute logique issuer. Il exige l'issuer
H27 exact, un nonce caller-supplied lowercase hex64, un timestamp UTC strict et
la destination logique exacte. Il construit seulement les neuf champs et les
bytes JSON canoniques en memoire.

La premiere revue conclut FAIL : des dependances etaient parsees avant leur
verification, des callbacks arbitraires pouvaient produire des effets et le
nonce etait reutilisable. La correction verifie chaque artefact avant de parser
ou suivre ses references, remplace les callbacks par une probe immutable sans
code executable et consomme chaque nonce une seule fois dans un registre
in-memory verrouille.

La deuxieme revue conclut FAIL sur une derniere frontiere Python : les
annotations de types de la probe et des quatre entrees caller-supplied
n'interdisaient pas un objet personnalise avec une comparaison executable. La
micro-correction exige maintenant des `str` natifs exacts avant toute
operation sur les entrees, puis des `bool`/`str` natifs exacts dans la probe
avant toute comparaison. Un test adversarial injecte un objet dont toutes les
methodes magiques leves et confirme son rejet sans execution ni consommation
du nonce.

Identite du module corrige avant commit : blob Git
`e9cc159e6d6284f692feb5d42d03d8682aa202c3`, `10333` octets et SHA-256
`2d7224dda54b901b89a3b5392c41433a2df72e0a259ac8d0b3519ecf0d63a34b`.
Validation locale : `7/7` tests cibles, `331/331` tests H27, `py_compile` et
`git diff --check` passent.

La probe doit attester qu'aucune destination n'a ete observee et qu'aucun
create/write n'a eu lieu. Le resultat indique
explicitement zero artefact, authority, claim, capability, effet filesystem et
science. Aucun `open`, `O_EXCL`, write, fsync ou rename n'existe dans le module.

Cette etape n'autorise ni seal/binding du module, ni invocation reelle.
