# Guitar MIDI AI Android 1.0.0

Application Android native qui exécute les mêmes modèles TFLite, le même contrat de 20 features et le même décodeur MIDI global que le live PC.

Pré-requis : Android Studio récent, JDK 17 et Android SDK 35. Ouvrir ce dossier comme projet, synchroniser Gradle, puis lancer `app` sur un appareil Android 6.0+ (API 23). Une vraie interface audio guitare USB est recommandée ; le micro du téléphone fonctionne mais ne correspond pas au domaine d'entraînement « guitare propre ».

Au démarrage, accorder la permission microphone et rester silencieux une seconde. La capture `UNPROCESSED` est préférée et bascule sur `MIC` si le téléphone ne l'expose pas. La première entrée MIDI USB/Bluetooth exposant un port d'entrée est utilisée automatiquement. Sans périphérique MIDI, la hauteur reste affichée à l'écran et aucune note n'est envoyée.

Le profil livré privilégie la réduction des fausses notes : il peut fusionner deux répétitions rapides de la même hauteur. Le MIDI est toujours remis à zéro lors d'un arrêt, d'une erreur audio ou de la fermeture de l'activité.
