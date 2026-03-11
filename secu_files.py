import os
import sys
import getpass
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import cryptography.exceptions

def derive_key(password: str, salt: bytes) -> bytes:
    """Derive une clé de 256 bits à partir du mot de passe et du sel."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))

def encrypt_target(target_path: str, password: str, delete_original: bool = False):
    """Chiffre un fichier spécifié ou compresse et chiffre un dossier entier."""
    if not os.path.exists(target_path):
        print(f"❌ Erreur : Le fichier ou dossier '{target_path}' n'existe pas.")
        return

    import shutil
    
    file_to_encrypt = target_path
    is_folder = os.path.isdir(target_path)
    
    # 1. Préparation : si c'est un dossier, on le zippe automatiquement
    if is_folder:
        print("[INFO] Le chemin indique un dossier. Compression automatique en cours...")
        # Crée un ZIP du même nom juste à côté du dossier
        file_to_encrypt = shutil.make_archive(target_path, 'zip', target_path)
        print(f"[INFO] Dossier compressé temporairement en : {file_to_encrypt}")

    print("Chiffrement en cours, veuillez patienter...")

    # 2. Génération de composantes aléatoires
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12) # Le Nonce standard pour GCM est de 96 bits (12 octets)

    # 2. Dérivation de la clé
    key = derive_key(password, salt)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()

    try:
        # L'extension sera .enc pour les fichiers simples, ou .zip.enc pour les dossiers
        output_path = file_to_encrypt + '.enc'
        
        # 4. Lecture et Chiffrement par morceaux (Streaming) pour supporter des fichiers > 2 Go
        with open(file_to_encrypt, 'rb') as f_in, open(output_path, 'wb') as f_out:
            f_out.write(salt)
            f_out.write(nonce)
            
            while True:
                chunk = f_in.read(64 * 1024) # 64 Ko
                if not chunk:
                    break
                f_out.write(encryptor.update(chunk))
                
            f_out.write(encryptor.finalize())
            f_out.write(encryptor.tag)
        
        print(f"✅ Succès : Données chiffrées -> '{output_path}'")
        
        # Nettoyage automatique du ZIP temporaire si on avait compressé un dossier
        if is_folder:
            os.remove(file_to_encrypt)
            print("[INFO] Archive zip temporaire supprimée.")
            
        # Suppression du dossier ou fichier original si demandé
        if delete_original:
            if is_folder:
                import shutil
                shutil.rmtree(target_path)
                print(f"🗑️ Dossier original '{target_path}' supprimé par sécurité.")
            else:
                os.remove(target_path)
                print(f"🗑️ Fichier original '{target_path}' supprimé par sécurité.")
            
    except Exception as e:
        print(f"❌ Erreur lors du chiffrement : {e}")

def decrypt_file(file_path: str, password: str):
    """Déchiffre un fichier .enc."""
    if not os.path.exists(file_path):
        print(f"❌ Erreur : Le fichier '{file_path}' n'existe pas.")
        return
        
    if not os.path.isfile(file_path):
        print(f"❌ Erreur : '{file_path}' est un dossier, pas un fichier chiffré .enc.")
        return

    if not file_path.endswith('.enc'):
        print("⚠️ Avertissement : Le fichier ne se termine pas par '.enc'.")

    print("Déchiffrement en cours, veuillez patienter...")

    try:
        output_path = file_path[:-4] if file_path.endswith('.enc') else file_path + '.decrypted'
        
        # Sécurité pour ne pas écraser un fichier existant par erreur
        if os.path.exists(output_path):
            choice = input(f"Attention, le fichier '{output_path}' existe déjà. Voulez-vous l'écraser ? (o/N) : ")
            if choice.lower() != 'o':
                output_path = file_path + '.decrypted'
                print(f"Le fichier sera sauvegardé sous '{output_path}' à la place.")

        with open(file_path, 'rb') as f_in:
            f_in.seek(0, 2) # On lit la taille totale
            file_size = f_in.tell()

            # Taille minimale = 16 (Sel) + 12 (Nonce) + 16 (Tag AES-GCM) = 44 octets
            if file_size < 44: 
                print("❌ Erreur : Fichier corrompu ou illisible.")
                return

            # 1. Extraction du Tag final
            tag_pos = file_size - 16
            f_in.seek(tag_pos)
            tag = f_in.read(16)

            # 2. Extraction du Sel et Nonce
            f_in.seek(0)
            salt = f_in.read(16)
            nonce = f_in.read(12)

            # 3. Dérivation de la clé (doit correspondre à celle du chiffrement)
            key = derive_key(password, salt)
            decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()

            # 4. Déchiffrement par morceaux (Streaming) pour des fichiers illimités
            f_in.seek(28) # On démarre après le salt et le nonce
            with open(output_path, 'wb') as f_out:
                pos = 28
                while pos < tag_pos:
                    read_size = min(64 * 1024, tag_pos - pos)
                    chunk = f_in.read(read_size)
                    if not chunk:
                        break
                    f_out.write(decryptor.update(chunk))
                    pos += len(chunk)
                
                # Vérification indispensable de l'intégrité
                f_out.write(decryptor.finalize())
            
        print(f"🔓 Succès : Données déchiffrées -> '{output_path}'")
        
        # 5. Décompression automatique si c'était un dossier (qui a fini en .zip.enc)
        if output_path.endswith('.zip'):
            folder_target = output_path[:-4]
            import shutil
            import zipfile
            
            # Vérification de sécurité avant d'extraire
            if os.path.exists(folder_target):
                print(f"⚠️ Avertissement : Le dossier '{folder_target}' existe déjà, le contenu de l'archive y sera ajouté.")
                
            print(f"[INFO] Extraction du dossier en cours vers '{folder_target}'...")
            try:
                with zipfile.ZipFile(output_path, 'r') as zip_ref:
                    zip_ref.extractall(folder_target)
                os.remove(output_path)
                print(f"🔓 Succès complet : Dossier original restauré -> '{folder_target}'")
            except Exception as zip_e:
                print(f"❌ Erreur lors de l'extraction de l'archive : {zip_e}")
                print(f"[INFO] L'archive chiffrée a tout de même été restaurée ici : '{output_path}'")

    except cryptography.exceptions.InvalidTag:
        print("❌ Accès Refusé : Mot de passe incorrect ou fichier altéré/corrompu !")
    except Exception as e:
        print(f"❌ Erreur lors du déchiffrement : {e}")

def main():
    while True:
        print("\n========================================")
        print(" 🔒 Verrouilleur de Fichiers")
        print("========================================")
        print("1. Chiffrer un document")
        print("2. Déchiffrer un document")
        print("3. Quitter")
        print("========================================")
        
        choice = input("Choisissez une option (1-3) : ")
        
        if choice == '1':
            target_path = input("Chemin du fichier ou dossier à chiffrer : ").strip('\"\'')
            password = getpass.getpass("Mot de passe fort : ")
            confirm = getpass.getpass("Confirmez le mot de passe : ")
            
            if password != confirm:
                print("❌ Erreur : Les mots de passe ne correspondent pas.")
                continue
                
            del_choice = input("Supprimer l'original après chiffrement ? (o/N) : ")
            delete_original = del_choice.lower() == 'o'
            
            encrypt_target(target_path, password, delete_original)
            
        elif choice == '2':
            file_path = input("Chemin du fichier à déchiffrer (.enc) : ").strip('\"\'')
            # L'input masqué est important pour ne pas qu'on lise par dessus l'épaule
            password = getpass.getpass("Mot de passe : ") 
            
            decrypt_file(file_path, password)
            
        elif choice == '3':
            print("Fermeture sécurisée...")
            sys.exit(0)
        else:
            print("Option invalide, veuillez réessayer.")

if __name__ == "__main__":
    main()
