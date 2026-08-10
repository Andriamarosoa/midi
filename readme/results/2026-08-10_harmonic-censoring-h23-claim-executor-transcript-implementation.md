# H23 — claim, exécuteur et transcript implémentés mais dormants

## Portée

Cette étape implémente exclusivement la chaîne autorisée après la revue du
contrat `45fecb9f…` : capability étendue, claim durable, exécuteur scientifique
synthétique, transcript append-only et finalizer autoritatif.

Elle ne crée ni nouveau seal, ni nouvelle activation, ni marker de production.
Elle ne lance aucune waveform, aucun test P0/P1/P2 et aucun calcul scientifique.

## Autorité et consommation

La nouvelle capability snapshotte notamment :

- activation et seal complets ;
- blobs Git exacts de la capability et du runner ;
- contrat H23 et contrat de capability ;
- contrat claim/transcript au SHA-256 brut
  `8126edc0a27fe43bbb41f0d8e874c1355e01f9f1185c1a71d70048fcaea661ef` ;
- manifests ordonnés `175 fixtures / 72 tests` ;
- runtime CPU mono-thread ;
- quatre chemins one-shot distincts, dont le transcript.

La claim utilise `O_CREAT|O_EXCL|O_WRONLY` en mode binaire, écrit un JSON
canonique UTF-8+LF, fsync le fichier puis son dossier sur POSIX et ne supprime
jamais le marker après création. Une seconde claim, même après incident, échoue.

## Exécuteur scientifique

L’entrée publique n’accepte que `repository_root` et la capability process-local
attestée. Elle dérive exclusivement le plan canonique, effectue la claim avant
l’import NumPy et avant la première allocation de waveform, puis exécute dans
l’ordre scellé :

```text
claim durable
→ HEADER fsync
→ 175 fixtures déterministes
→ 72 tests P0 → P1 → P2 avec arrêt au premier échec
→ TERMINAL
→ relecture et finalisation autoritative
```

Le synthétiseur couvre les enveloppes old/new, les harmoniques, gains, phases,
cents/inharmonicité, bruit blanc/rose, accords, voisinages, intervalles,
techniques, harmoniques naturelles, résonance sympathique, unisson physique,
frontières, silence et six familles OOD. Le noyau calcule le spectre partagé,
les censeurs hard/cosine, les courbes raw/normalisées/null/résiduelles, le
système de factorisation et un NNLS Lawson-Hanson déterministe ainsi que le
tuple causal de naissance.

## Transcript et finalizer

Chaque ligne JSONL est canonique, indexée et liée au SHA-256 exact de la ligne
précédente avec son LF. Le HEADER lie marker, activation, seal, sources,
contrats, manifests, runtime et hashes des listes ordonnées. Les événements de
fixture lient spec, waveform et target. Les résultats lient contrat résolu,
evidence schema, evidence hash, inverse, masques, latence et mémoire.

Le finalizer n’accepte aucun résultat, booléen ou chemin fourni par le caller.
Il rouvre le marker et le transcript aux chemins scellés, vérifie la chaîne,
les ordres, les dépendances, les hashes et recalcule chaque PASS/FAIL puis le
kill rule. Une réussite exige exactement `72 PASS` et les `175` fixtures. Un
incident opérationnel reste `H23_EXECUTION_INCONCLUSIVE_FAIL_CLOSED` avec
`scientific_verdict=null`.

## Tests sans science

Les tests utilisent des répertoires temporaires et des lignes administratives
factices; ils n’appellent jamais le synthétiseur. Ils couvrent notamment :

- ancien seal/activation rejeté avant résolution du plan ;
- marker canonique exclusif et marker corrompu bloquant toute reprise ;
- capability forgée/non claimée refusée ;
- ordre claim → HEADER avant tout import scientifique ;
- chaîne JSONL, mutation, préfixe terminal et dépendances ;
- recomputation d’un échec P0 et suffixe exact `NOT_RUN` ;
- succès impossible sans `72/72` et `175/175` ;
- incident opérationnel non scientifique ;
- événement après premier échec refusé ;
- objets PASS fabriqués par le caller sans route vers le finalizer ;
- staging partiel jamais publié.

Commande ciblée archivée :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest tests.test_harmonic_censoring_h23_harness tests.test_harmonic_censoring_h23_execution_dormant tests.test_harmonic_censoring_h23_claim_transcript_implementation tests.test_harmonic_censoring_h23_execution_capability_contract tests.test_harmonic_censoring_h23_executor_claim_transcript_contract
```

Résultat ciblé : `60 tests réussis`. Une suite élargie incluant les contrats
H17a/H20/H17 réussit `82 tests`. `py_compile` réussit également.

## État de sécurité scientifique

```text
nouveau seal/activation       absent
marker production             absent
transcript production         absent
waveform synthétisée          non
P0/P1/P2 exécuté              non
donnée réelle / H17           non
modèle / checkpoint           non
locked-test                   non
fit / calibration             non
```

Étape suivante : revue externe de ce commit complet. Un nouveau seal et une
nouvelle activation liant ses blobs exacts resteront obligatoires avant toute
claim ou exécution réelle.
