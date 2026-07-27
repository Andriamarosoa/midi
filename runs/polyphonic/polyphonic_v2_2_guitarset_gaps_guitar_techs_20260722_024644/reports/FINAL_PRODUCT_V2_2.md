# Bilan produit polyphonique V2.2

Date de clôture automatique : 22 juillet 2026.

## Intégrité expérimentale

- Checkpoint sélectionné sur validation uniquement : `epoch-08`.
- Seuils gelés avant ouverture du test : frame `0.535`, onset `0.665`.
- Test ouvert seulement après sélection finale.
- 49 enregistrements précédemment touchés par un ancien contrôle de parité correspondent à 48 identifiants de groupe uniques, tous exclus.
- Aucun poids, seuil, format ou paramètre de décodeur n'a été resélectionné sur le test.
- Validation inverse finale : 12 enregistrements de test, sélection équilibrée par dataset et groupes distincts.

## Exports et contrats

- TFLite float16 : SHA256 conforme à `metadata.json`.
- ONNX : SHA256 conforme et rapport de parité validé.
- Comparaison événementielle Keras FP32 / TFLite float16 sur validation : validée.
- APK debug V2.2 assemblé : `android/app/build/outputs/apk/debug/app-debug.apk`.
- SHA256 APK : `809a829171b64469bc228d8e667b8813396d2743a2a2812d4c42bf39cbc87358`.
- Contrat desktop corrigé : live et transcription chargent V2.2 par défaut et acceptent les 3 threads mesurés.
- Tests de non-régression Python finaux : 34/34 réussis.
- Tests unitaires Android : 9/9 réussis, aucune erreur.

## Généralisation sur le test propre

- F1 frame : `0.536143`.
- Précision frame : `0.557950`.
- Rappel frame : `0.515977`.
- F1 onset par frame : `0.080580`.
- F1 frame monophonique : `0.70517`.
- F1 frame polyphonique : `0.50800`.
- Exactitude frame polyphonique : `3.59 %`.

Le score frame reste proche de la validation, sans signe majeur de surapprentissage. L'onset reste la principale faiblesse du réseau.

## Validation inverse événementielle

Sur 4 916 notes annotées et 8 485 notes générées :

- Notes appariées sur onset : `1 623`.
- Précision onset : `0.191279`.
- Rappel onset : `0.330146`.
- F1 onset : `0.242221`.
- Notes générées non appariées : `6 862`.
- Notes annotées manquantes : `3 293`.
- F1 onset + offset : `0.068950`.
- Erreur onset absolue p95 des notes appariées : `47.82 ms`.

Par dataset :

| Dataset | Enregistrements | F1 onset | F1 onset + offset |
|---|---:|---:|---:|
| GAPS poly mix | 4 | 0.2271 | 0.0460 |
| Guitar-TECHS direct input | 2 | 0.2357 | 0.1537 |
| Guitar-TECHS mic/amp | 1 | 0.3294 | 0.1384 |
| GuitarSet poly mix | 5 | 0.2797 | 0.0960 |

## Diagnostic spectral bidirectionnel

MIDI généré vers WAV :

- Supporté par annotation : `1 623`.
- Support spectral sans appariement d'annotation : `5 499`.
- Suspect harmonique : `17`.
- Faible : `634`.
- Non supporté : `712`.
- Ratio spectral médian : `0.8440`.

WAV vers MIDI généré :

- Notes annotées manquantes : `3 293`.
- Notes manquantes avec support spectral fort : `1 932`.

Le spectre indique qu'une partie des sorties non appariées possède une énergie audio réelle, mais cela ne suffit pas à les considérer comme des notes correctes : résonances, harmoniques et fragmentation restent possibles.

## Latence

- Budget d'un hop : `5.805 ms`.
- Benchmark TFLite court validé, 3 threads : p95 `2.597 ms`.
- Validation inverse continue : seulement 4/12 enregistrements ont un p95 inférieur au hop.
- P95 continu le plus défavorable : `18.105 ms`.
- Pointe maximale observée : `835.066 ms`.
- Moyenne pondérée par la durée : `4.827 ms`.

Le diagnostic spectral est hors ligne et n'ajoute aucune latence au live. En revanche, les pointes d'inférence continues imposent un stress live réel avant certification desktop. Le réglage Android à un thread n'a pas encore été mesuré sur un appareil réel.

## Verdict

V2.2 est un prototype polyphonique causal exporté et testable sur desktop/Android. L'intégrité du bundle, la parité de format et la généralisation frame sont établies. L'acceptation runtime valide le format TFLite float16, pas la qualité musicale du produit.

V2.2 n'est pas encore production-ready musicalement : trop de notes événementielles non appariées, trop de notes manquantes, offsets faibles et latence longue durée instable. Le modèle est limité à MIDI 40–76 et à six notes simultanées. L'APK est une version debug non signée, sans validation thermique, audio ou MIDI sur téléphone réel. La prochaine validation utile est un essai live instrumenté avec guitare sèche, casque, WAV enregistré, trace MIDI/debug et mesure de backlog. Toute amélioration V2.3 devra être sélectionnée sur validation ou nouvelles données, jamais sur ce test final.
