# H27 - implementation effect-free de l'issuer one-shot

La revue externe de `cb581c7e989715b808a8334127dd1dd50ad816fd`
conclut `PASS` et autorise uniquement une implementation dormante avec adapters
fake ou in-memory.

Le module rehache les 78 identites avant toute logique issuer. Il exige l'issuer
H27 exact, un nonce caller-supplied lowercase hex64, un timestamp UTC strict et
la destination logique exacte. Il construit seulement les neuf champs et les
bytes JSON canoniques en memoire.

Les adapters doivent attester qu'aucune destination n'a ete observee, qu'aucun
create/write n'a eu lieu et que les bytes n'ont pas change. Le resultat indique
explicitement zero artefact, authority, claim, capability, effet filesystem et
science. Aucun `open`, `O_EXCL`, write, fsync ou rename n'existe dans le module.

Cette etape n'autorise ni seal/binding du module, ni invocation reelle.
