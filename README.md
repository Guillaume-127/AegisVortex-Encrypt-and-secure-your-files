# 🔒 Sécu-Files V3.8 - "Matri-X Stability" 🏎️🛡️🟢

Sécu-Files est une suite professionnelle de sécurisation de données haute performance, conçue pour chiffrer et compresser des fichiers ou dossiers de plusieurs centaines de Go avec une stabilité absolue et une interface immersive.

## 🌟 Points Forts de la V3.8
- **🚀 Turbo Engine :** Utilisation intensive du streaming natif **Zstandard (Zstd)** et du chiffrement **AES-256 GCM** pour saturer la bande passante de vos disques.
- **🛡️ Résilience Totale :** Chiffrement par morceaux (Chunks de 32 Mo). Si une partie du fichier est corrompue, le reste demeure récupérable.
- **💎 Interface Matrix :** GUI immersive sous CustomTkinter avec support du **Drag & Drop** et thématique sombre néon.
- **🏗️ Architecture Stable (v3.8) :** Communication asynchrone par file d'attente (Queue) éliminant tout risque de crash système (GIL crash) sous Windows.
- **🔗 Support Dossiers :** Gère nativement les dossiers via une encapsulation Tar optimisée sans fichiers temporaires.

## 🛠️ Installation & Lancement

### Windows (Recommandé)
Lancez simplement `start.bat`. 
Le script s'occupe de tout :
1. Création de l'environnement virtuel (`venv`).
2. Installation des dépendances (`cryptography`, `zstandard`, `argon2-cffi`, `customtkinter`, `windnd`).
3. Lancement de l'interface graphique.

### Manuel
```bash
pip install -r requirements.txt
python gui.py
```

## 🔐 Spécifications de Sécurité
- **Standard ANSSI/OWASP :** Dérivation de clé via **Argon2id** (Itérations: 3, Mémoire: 64 Mo, Parallélisme: 4).
- **Chiffrement Authentifié :** AES-256 en mode GCM (vérifie l'intégrité à chaque morceau).
- **Zéro-Temp :** Aucun fichier temporaire n'est écrit sur le disque pendant le processus (protège votre SSD et votre vie privée).
- **Format propriétaire :** Génère des fichiers `.127` robustes.

## 🔄 Rétrocompatibilité
Sécu-Files V3.8 supporte l'ouverture des anciens formats :
- **V2 :** `.127` classiques.
- **V1 :** Anciens fichiers `.enc`.

---
*Développé pour la sécurité, optimisé par l'IA. Matri-X Edition stable.*
