# Decision V6.3.1

V6.3.1 est meilleur que V6.3 mais ne remplace pas encore V6.0 en live.

- AUC-PR validation extraite : 56,97 %.
- F1 evenementiel continu : 42,16 % sur joueur 04, 38,18 % sur joueur 05.
- Latence `tf.function` batch 1 p95 : 4,12 ms.
- Avec le seuil decodeur 0,029395 choisi uniquement sur quatre solos 04 et les
  retriggers conserves de V6.0, le test quatre solos 05 passe les contraintes
  relatives : 50,445 fantomes/minute, 79,531 % de precision conjointe, 5 notes
  manquantes et 15 retriggers non supportes.

Le gain net n'est que quatre evenements sur 103,48 s et ajoute un second modele.
Le resultat est donc une ablation positive a conserver, pas un remplacement live.
