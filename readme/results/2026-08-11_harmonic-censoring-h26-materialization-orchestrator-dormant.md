# H26 — orchestrateur dormant de matérialisation

Statut : `PENDING_BATCH_EXTERNAL_REVIEW`. Il lie le gate `QUALIFIED` à un
materializer injecté appelé exactement une fois. Le materializer réel n'est ni
importé ni appelé; les tests utilisent exclusivement un double.
