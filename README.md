# Verrouilleur de Fichiers (AES-256)

Outil de sécurisation de fichiers et dossiers en Python utilisant le chiffrement AES-256-GCM.

## Fonctionnalités
- Chiffrement de fichiers individuels.
- Chiffrement de dossiers complets (compression ZIP automatique).
- Chiffrement par flux (Streaming) pour supporter des fichiers de taille illimitée (> 2 Go).
- Dérivation de clé sécurisée via PBKDF2.

## Utilisation
Lancez simplement `start.bat` sur Windows pour démarrer l'interface.
L'outil créera automatiquement un environnement virtuel Python et installera la bibliothèque `cryptography` s'il ne la trouve pas.

## Sécurité
- Algorithme : AES-256 en mode GCM (Authentifié).
- Dérivation : SHA-256 avec 480 000 itérations.
- Aucun mot de passe n'est stocké sur le disque.
