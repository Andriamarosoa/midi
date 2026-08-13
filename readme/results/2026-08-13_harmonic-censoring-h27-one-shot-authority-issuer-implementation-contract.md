# H27 - contrat de future implementation de l'issuer one-shot

La revue externe de `005c4e5eedfbb10b0452f9fa3e1939e589234f89`
conclut `PASS`. Cette etape definit uniquement les exigences fail-closed d'une
future implementation de l'issuer; aucun module issuer n'est cree.

Le contrat lie les quatre artefacts PASS/scelles du contrat d'artefact
d'issuance et leurs 72 identites transitives, soit 76 chemins uniques rehashes.
Il preserve l'issuer H27 exact, le schema ferme de neuf champs, le manifeste
canonique 72 et la destination exacte. Il exige validation complete avant
toute consommation, create-exclusive sans ecrasement et aucun retry apres
consommation.

Seuls les futurs tests par adapters fake ou in-memory sont admis par ce
contrat. Issuance, authority, claim, capability, observation de destination,
filesystem reel, execution, materializer, population, locked test et science
restent interdits. La seule prochaine action est la revue externe des bytes du
contrat et de son seal.
