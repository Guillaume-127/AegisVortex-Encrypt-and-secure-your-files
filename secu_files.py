import os
import sys
import getpass
import secrets
import shutil
import tarfile
import time
import cryptography.exceptions
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import zstandard as zstd
from tqdm import tqdm

# --- CONFIGURATION V2 ---
MAGIC_HEADER = b"SECUV2"
V2_EXTENSION = ".127"
V1_EXTENSION = ".enc"
CHUNK_SIZE = 1024 * 1024  # 1 Mo pour l'I/O

# --- DÉRIVATION DE CLÉ ---

def derive_key_v1(password: str, salt: bytes) -> bytes:
    """Ancienne méthode V1 (PBKDF2)."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))

def derive_key_v2(password: str, salt: bytes) -> bytes:
    """Nouvelle méthode V2 (Argon2id)."""
    # Paramètres robustes (recommandés par l'ANSSI / OWASP)
    kdf = Argon2id(
        salt=salt,
        length=32,
        iterations=3,
        memory_cost=65536,
        lanes=4
    )
    return kdf.derive(password.encode('utf-8'))

# --- UTILITAIRES DE STREAMING ---

class EncryptingWriter:
    """Wrapper pour chiffrer les données au fur et à mesure qu'elles sont écrites."""
    def __init__(self, target_file, encryptor):
        self.target = target_file
        self.encryptor = encryptor

    def write(self, data):
        if data:
            self.target.write(self.encryptor.update(data))

    def flush(self):
        self.target.flush()

class DecryptingReader:
    """Wrapper pour déchiffrer les données lors de la lecture par le flux Zstd."""
    def __init__(self, source_file, decryptor, total_payload_size):
        self.source = source_file
        self.decryptor = decryptor
        self.remaining = total_payload_size

    def read(self, size=-1):
        if self.remaining <= 0:
            return b""
        read_size = size if size > 0 else CHUNK_SIZE
        read_size = min(read_size, self.remaining)
        
        chunk = self.source.read(read_size)
        if not chunk:
            return b""
        
        self.remaining -= len(chunk)
        return self.decryptor.update(chunk)

# --- CORE LOGIC V2 ---

def encrypt_target(target_path: str, password: str, comp_level: int = 3, delete_original: bool = False):
    """Chiffre et compresse (V2) un fichier ou dossier avec Zstd et AES-GCM."""
    if not os.path.exists(target_path):
        print(f"❌ Erreur : '{target_path}' n'existe pas.")
        return

    is_folder = os.path.isdir(target_path)
    output_path = target_path + V2_EXTENSION
    
    print(f"🔒 Chiffrement V2 en cours ({'Dossier' if is_folder else 'Fichier'})...")
    start_time = time.time()

    # 1. Préparation cryptographie
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = derive_key_v2(password, salt)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()

    # 2. Pipeline de streaming
    try:
        # Calculer la taille totale approximative pour la barre de progression
        total_size = 0
        if is_folder:
            for root, dirs, files in os.walk(target_path):
                for f in files:
                    total_size += os.path.getsize(os.path.join(root, f))
        else:
            total_size = os.path.getsize(target_path)

        with open(output_path, 'wb') as f_out:
            # Header V2
            f_out.write(MAGIC_HEADER)
            f_out.write(bytes([comp_level]))
            f_out.write(salt)
            f_out.write(nonce)

            # Writer chiffrant
            enc_writer = EncryptingWriter(f_out, encryptor)
            
            # Compresseur Zstd multi-threadé
            cctx = zstd.ZstdCompressor(level=comp_level, threads=-1)
            
            with tqdm(total=total_size, unit='B', unit_scale=True, desc="Progression") as pbar:
                with cctx.stream_writer(enc_writer) as compressor:
                    if is_folder:
                        # On utilise TAR pour packer le dossier sans fichier temp
                        with tarfile.open(fileobj=compressor, mode='w|') as tar:
                            # Ajout personnalisé pour mettre à jour pbar
                            def pbar_add(tarinfo):
                                pbar.update(tarinfo.size)
                                return tarinfo
                            tar.add(target_path, arcname=os.path.basename(target_path), filter=pbar_add)
                    else:
                        with open(target_path, 'rb') as f_in:
                            while True:
                                chunk = f_in.read(CHUNK_SIZE)
                                if not chunk:
                                    break
                                compressor.write(chunk)
                                pbar.update(len(chunk))
            
            # Finalisation AES-GCM
            f_out.write(encryptor.finalize())
            f_out.write(encryptor.tag)

        # Rapport final
        duration = time.time() - start_time
        final_size = os.path.getsize(output_path)
        print(f"✅ Succès : '{output_path}'")
        print(f"⚡ Vitesse moy: {(total_size/1e6)/duration:.2f} Mo/s | Taille: {final_size/1e6:.2f} Mo")

        if delete_original:
            if is_folder:
                shutil.rmtree(target_path)
            else:
                os.remove(target_path)
            print(f"🗑️ Original supprimé.")

    except Exception as e:
        if os.path.exists(output_path):
            os.remove(output_path)
        print(f"❌ Erreur critique : {e}")

def decrypt_file(file_path: str, password: str):
    """Déchiffre un fichier (détecte V1 .enc ou V2 .127)."""
    if not os.path.exists(file_path):
        print("❌ Fichier introuvable.")
        return

    with open(file_path, 'rb') as f_in:
        header = f_in.read(len(MAGIC_HEADER))
        
        if header == MAGIC_HEADER:
            # --- LOGIQUE V2 ---
            print("🔓 Détection Format V2 (.127)...")
            comp_level = int(f_in.read(1)[0])
            salt = f_in.read(16)
            nonce = f_in.read(12)
            
            # On cherche le tag et la taille du payload
            f_in.seek(0, 2)
            total_size = f_in.tell()
            tag_pos = total_size - 16
            payload_size = tag_pos - (len(MAGIC_HEADER) + 1 + 16 + 12)
            
            f_in.seek(tag_pos)
            tag = f_in.read(16)
            
            # Dérivation clé V2
            key = derive_key_v2(password, salt)
            decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
            
            # Output path
            output_path = file_path.replace(V2_EXTENSION, "")
            if output_path == file_path: output_path += ".dec"

            f_in.seek(len(MAGIC_HEADER) + 1 + 16 + 12)
            
            try:
                # Reader déchiffrant
                dec_reader = DecryptingReader(f_in, decryptor, payload_size)
                dctx = zstd.ZstdDecompressor()
                
                # Décompression streamée
                # Note: On ne connaît pas la taille décompressée exacte, donc tqdm est moins précis ici
                with open(output_path + ".tmp", 'wb') as f_out:
                    with tqdm(total=payload_size, unit='B', unit_scale=True, desc="Déchiffrement") as pbar:
                        # Wrapper pour mettre à jour pbar pendant la décompression
                        class PbarReader:
                            def read(self, size):
                                data = dec_reader.read(size)
                                pbar.update(len(data))
                                return data
                        
                        # Correction: Utilisation d'un reader streamé
                        with dctx.stream_reader(PbarReader()) as reader:
                            shutil.copyfileobj(reader, f_out)
                
                # Vérification finale AES
                decryptor.finalize()
                
                # Si c'était un dossier (TAR), on extrait
                if tarfile.is_tarfile(output_path + ".tmp"):
                    print("[INFO] Extraction du dossier...")
                    with tarfile.open(output_path + ".tmp", "r:") as tar:
                        tar.extractall(path=os.path.dirname(output_path))
                    os.remove(output_path + ".tmp")
                    print(f"✅ Dossier restauré.")
                else:
                    os.rename(output_path + ".tmp", output_path)
                    print(f"✅ Fichier restauré : {output_path}")

            except cryptography.exceptions.InvalidTag:
                if os.path.exists(output_path + ".tmp"): os.remove(output_path + ".tmp")
                print("❌ Accès Refusé : Mot de passe incorrect ou fichier corrompu.")
            except Exception as e:
                print(f"❌ Erreur : {e}")

        else:
            # --- LOGIQUE V1 (Rétrocompatibilité) ---
            print("🔓 Détection Format V1 (.enc)...")
            f_in.seek(0)
            salt = f_in.read(16)
            nonce = f_in.read(12)
            
            f_in.seek(0, 2)
            file_size = f_in.tell()
            tag_pos = file_size - 16
            f_in.seek(tag_pos)
            tag = f_in.read(16)
            
            key = derive_key_v1(password, salt)
            decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
            
            output_path = file_path[:-4] if file_path.endswith('.enc') else file_path + ".dec"
            
            try:
                f_in.seek(28)
                with open(output_path, 'wb') as f_out:
                    pos = 28
                    while pos < tag_pos:
                        chunk = f_in.read(min(CHUNK_SIZE, tag_pos - pos))
                        if not chunk: break
                        f_out.write(decryptor.update(chunk))
                        pos += len(chunk)
                    f_out.write(decryptor.finalize())
                
                # Gestion ZIP historique
                if output_path.endswith('.zip'):
                    print("[INFO] Extraction Archive ZIP V1...")
                    shutil.unpack_archive(output_path, output_path[:-4])
                    os.remove(output_path)
                
                print(f"✅ Succès V1 : {output_path}")
            except Exception as e:
                print(f"❌ Erreur V1 : {e}")

def main():
    while True:
        print("\n" + "="*40)
        print(" 🔒 SÉCU-FILES V2 (Argon2id + Zstd)")
        print("="*40)
        print("1. Chiffrer (Dossier ou Fichier) -> .127")
        print("2. Déchiffrer (.127 ou .enc)")
        print("3. Quitter")
        print("="*40)
        
        choice = input("Option (1-3) : ")
        
        if choice == '1':
            target = input("Chemin : ").strip('\"\'')
            if not os.path.exists(target):
                print("❌ Chemin invalide.")
                continue
                
            password = getpass.getpass("Mot de passe : ")
            confirm = getpass.getpass("Confirmation : ")
            if password != confirm:
                print("❌ Mots de passe différents.")
                continue
                
            print("\nNiveau de compression :")
            print("1. Rapide (Vitesse max)")
            print("2. Équilibré (Recommandé)")
            print("3. Max (Lent, archive optimisée)")
            c_choice = input("Choix (1-3) [2] : ")
            levels = {'1': 1, '2': 3, '3': 19}
            comp_level = levels.get(c_choice, 3)
            
            del_choice = input("Supprimer l'original ? (o/N) : ")
            encrypt_target(target, password, comp_level, del_choice.lower() == 'o')
            
        elif choice == '2':
            path = input("Fichier à déchiffrer : ").strip('\"\'')
            password = getpass.getpass("Mot de passe : ")
            decrypt_file(path, password)
            
        elif choice == '3':
            break

if __name__ == "__main__":
    main()
