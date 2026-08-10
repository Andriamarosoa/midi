# H23 — contrat de future capability d’exécution synthétique

## Autorisation et portée

Après l’approbation du harness `e97674cd1d1c3a12ff113f98789105941ab17030`
et sa clôture documentaire `2cc826b1b672d10ecd4d4ab23050cc7050cc91d8`,
le pilote a autorisé uniquement la **définition contract-only** de la future
capability d’exécution.

Cette étape ne modifie pas `src/polyphonic/harmonic_censoring_h23.py`, ne crée
aucune factory/capability et maintient la garde inconditionnelle existante.
Aucune fixture n’est synthétisée et aucun test P0/P1/P2 n’est exécuté.

## Contrat créé

Fichier :

```text
configs/harmonic_censoring_h23_synthetic_execution_capability_contract.json
taille : 10 747 octets
SHA-256 brut : 230ee3bd9c60f87a794473a70483a3e24be8300d78037632d18ef4f703bf9f77
blob Git avant commit : 37e69ef5bd2c84cc52a2f53786151b5a8b157553
```

Le contrat lie :

- le commit harness approuvé `e97674cd…` ;
- le contrat H23 brut `719eba0a…` et son blob Git `864abd12…` ;
- le harness `548e6cc1…` et son test `e9c03542…` ;
- les `175` fixtures et le manifeste attendu `acfa37b9…` ;
- les `72` tests `27/35/10` et leur manifeste attendu `0d059d3f…`.

## Capability future

La capability future devra être non constructible par le caller, non copiable,
non sérialisable et attestée par identité via une factory séparément revue.
Une dataclass, un mapping ou une copie `dataclasses.replace()` ne pourra jamais
être une capability.

La factory devra notamment vérifier avant émission :

```text
contrat H23 + SHA
contrat capability + futur seal d’autorisation séparé
blobs exacts du harness
recalcul des deux manifests
commit d’exécution + ensemble exact de fichiers
worktree propre
runtime CPython 3.11.9 / NumPy 1.26.4 / arm64 CPU / 1 thread
destination et marker absents
aucun chemin H17 ou locked-test
```

Le futur seal n’existe pas encore : chemins, SHA, commit et droits restent
`null/false`.

## Frontière one-shot

La résolution/hachage des manifests reste zéro-science et ne consomme rien.
La consommation sera persistée atomiquement **avant la première synthèse de
waveform**. Après cette frontière, tout échec maintiendra
`synthetic_population_consumed=true` et interdira tout retry de la même
population.

L’ordre futur est scellé :

```text
zero-science preflight
→ capability issue
→ atomic consumption claim
→ P0
→ P1 seulement si tout P0 passe
→ P2 seulement si tout P1 passe
→ publication atomique
```

Aucun skip, ajout, ordre dynamique ou changement post-observation n’est admis.

## Publication et verdict

La publication future exigera staging, vérification complète et rename
atomique, avec égalité exacte des 175 IDs et des 72 tests ordonnés. Un timeout
ou une erreur ne pourra pas créer la destination finale.

Le seul statut positif possible reste :

```text
AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL
```

Il ne signifie jamais `TRAIN_AUTHORIZED`. Un résultat négatif, incomplet ou
inconclusif ne pourra ni autoriser un fit ni rouvrir la population.

## Vérification pure

Commande :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest tests.test_harmonic_censoring_h23_execution_capability_contract
```

Résultat : `10 tests réussis en 0,130 s`.

Les tests ne font que parser le JSON, vérifier ses valeurs et comparer les
blobs Git déjà versionnés. Aucun import NumPy/TensorFlow, actif, waveform,
modèle ou test scientifique n’est impliqué.

La vérification finale élargie aux tests du harness et aux contrats historiques
H17/H20 donne `36 tests réussis en 0,538 s`. `json.tool`, `py_compile` et
`git diff --check` réussissent; l'ensemble modifié contient exactement les cinq
fichiers autorisés par ce contrat.

## État final de cette étape

```text
contract_only                         true
capability_implementation_authorized  false
capability_issuance_authorized        false
synthetic_execution_authorized        false
P0/P1/P2_execution_authorized         false
scientific_execution_authorized       false
real_data_access_authorized           false
training_authorized                   false
H17_population_used                   false
locked_test_used                      false
```

La seule prochaine action est la revue externe de ce contrat. Même une revue
positive n’exécutera rien : elle pourra seulement autoriser séparément
l’implémentation de la capability toujours dormante.
