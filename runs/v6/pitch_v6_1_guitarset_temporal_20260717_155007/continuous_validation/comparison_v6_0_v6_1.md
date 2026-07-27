# Comparaison continue V6.0 / V6.1

Date : 2026-07-17

## Protocole

- Checkpoints choisis sur validation uniquement : `best_pitch.keras` pour les deux versions.
- Quatre solos GuitarSet du joueur 05, durée totale 103,48 s.
- Politique causale `detected_progressive` identique.
- Stabilisation identique : deux trames consécutives, délai maximal ajouté 5,805 ms.
- Aucun lookahead.

## Résultats agrégés stabilisés

| Mesure | V6.0 | V6.1 | Évolution V6.1 |
|---|---:|---:|---:|
| F1 activité | 84,87 % | 84,13 % | -0,74 pt |
| Précision activité | 90,48 % | 92,30 % | +1,82 pt |
| Rappel activité | 79,92 % | 77,29 % | -2,63 pt |
| Faux positifs par trame | 14,24 % | 10,92 % | -3,32 pt |
| Top-1 pitch actif mono | 90,33 % | 90,30 % | -0,03 pt |
| Précision conjointe | 79,50 % | 78,43 % | -1,07 pt |
| Événements générés | 369 | 393 | +24 |
| Événements supportés | 266 | 284 | +18 |
| Événements non supportés | 90 | 98 | +8 |
| Fantômes par minute | 52,18 | 56,82 | +4,64 |
| Notes couvertes majoritairement | 169 / 199 | 167 / 199 | -2 |
| Notes totalement manquées | 3 / 199 | 7 / 199 | +4 |

## Latence

Benchmark répété dans le même environnement sur `gsmono_05_bn1_129_eb_solo` :

- V6.0 `tf.function` : moyenne 13,52 ms, p95 15,91 ms.
- V6.1 `tf.function` : moyenne 12,58 ms, p95 17,55 ms.
- Budget d'un hop : 5,805 ms.
- Délai de stabilisation maximal : 5,805 ms.
- Lookahead : 0 ms.

Les architectures étant identiques, V6.1 n'ajoute pas de coût structurel. Les deux modèles restent trop lents pour une inférence CPU à chaque hop.

## Conclusion

L'extension V6.1 des âges de sustain et de release réduit les faux positifs par trame et augmente la précision, mais elle dégrade le rappel, la couverture des notes et le nombre d'événements fantômes. Elle ne doit donc pas remplacer V6.0 comme base live.

Le prochain changement contrôlé ne devrait pas être un nouvel ajout de fenêtres isolées. Il faut conserver V6.0 comme référence et introduire un apprentissage explicitement temporel sur des séquences continues, avec une cible de stabilité/changement de note, puis refaire cette même validation inverse.
