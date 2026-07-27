# Correction de la metrique evenementielle

Les rapports `continuous_validation.json` et `continuous_test.json` comptaient par erreur les deux hops positifs d'une seule attaque comme deux evenements de reference. Ils sont conserves uniquement pour la tracabilite. Les fichiers suffixes `_corrected` comptent un evenement binaire par premiere trame causale et constituent les rapports valides.
