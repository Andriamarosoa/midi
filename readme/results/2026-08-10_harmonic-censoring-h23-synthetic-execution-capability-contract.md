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
taille : 13 216 octets
SHA-256 brut : 3f386e15171fd4c41fa258fa83877bb8c86e24b39ea5df642f39b32b5760a4b5
blob Git avant commit : b3834559f0dfde24df5a027e46a36225e9f75602
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
`null/false`. Il devra autoriser explicitement et simultanément l’émission de
la capability, l’exécution synthétique/scientifique et chacune des phases
`P0/P1/P2`. L’absence d’un seul de ces droits interdira l’émission.

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
→ publication atomique du résultat terminal
```

Aucun skip, ajout, ordre dynamique ou changement post-observation n’est admis.

## Publication et verdict

La publication future distingue trois sorties :

- **succès complet** : seuls les `175` IDs et `72` tests ordonnés complets
  peuvent produire `AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL` dans la destination
  de succès ;
- **échec scientifique** : arrêt immédiat, puis publication atomique obligatoire
  d’un terminal négatif avec le préfixe exact exécuté, le premier test fautif,
  tous les IDs restants marqués `NOT_RUN_BY_KILL_RULE`, le marker de
  consommation et le verdict négatif ;
- **crash/timeout/incomplétude opérationnelle** : statut
  `H23_EXECUTION_INCONCLUSIVE_FAIL_CLOSED`, jamais présenté comme un verdict
  scientifique et jamais publié dans la destination de succès. Si le processus
  ne peut pas finaliser son terminal inconclusif, le marker de consommation
  demeure l’autorité durable et interdit le retry.

Ainsi, l’exigence `175/72` ne concerne que le succès complet et ne peut plus
empêcher la conservation autoritative d’une falsification précoce.

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

Résultat : `11 tests réussis en 0,156 s`.

Les tests ne font que parser le JSON, vérifier ses valeurs et comparer les
blobs Git déjà versionnés. Aucun import NumPy/TensorFlow, actif, waveform,
modèle ou test scientifique n’est impliqué.

La vérification finale élargie aux tests du harness et aux contrats historiques
H17/H20 donne `42 tests réussis en 0,572 s`. `json.tool`, `py_compile` et
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

La séquence future est explicitement non auto-référentielle : commit
d’implémentation du runner/capability, revue, commit de seal séparé liant cette
implémentation déjà revue, revue du seal, puis seulement émission/claim/exécution.
La seule prochaine action reste la revue externe de ce contrat corrigé.
