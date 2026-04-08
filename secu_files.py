import secrets
import os
import tarfile
import zstandard as zstd
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
import cryptography.exceptions

# --- CONFIGURATION V3.8 ---
MAGIC_V3 = b'SEC127'
V2_EXTENSION = ".127"
CHUNK_SIZE = 32 * 1024 * 1024 # 32 Mo par bloc pour la résilience

class ChunkedGCMWriter:
    def __init__(self, f_out, key, chunk_size=CHUNK_SIZE):
        self.f_out = f_out
        self.key = key
        self.chunk_size = chunk_size
        self.buffer = bytearray()

    def write(self, b):
        self.buffer.extend(b)
        while len(self.buffer) >= self.chunk_size:
            chunk = self.buffer[:self.chunk_size]
            self._encrypt_and_write(chunk)
            del self.buffer[:self.chunk_size]
        return len(b)

    def _encrypt_and_write(self, data):
        nonce = secrets.token_bytes(12)
        encryptor = Cipher(algorithms.AES(self.key), modes.GCM(nonce)).encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        self.f_out.write(nonce)
        self.f_out.write(len(ciphertext).to_bytes(4, 'big'))
        self.f_out.write(ciphertext)
        self.f_out.write(encryptor.tag)

    def close(self):
        if self.buffer:
            self._encrypt_and_write(self.buffer)
            self.buffer = bytearray()

class ChunkReader:
    def __init__(self, f_in):
        self.f_in = f_in

    def read_next(self):
        nonce = self.f_in.read(12)
        if not nonce: return None, None, None
        size = int.from_bytes(self.f_in.read(4), 'big')
        data = self.f_in.read(size)
        tag = self.f_in.read(16)
        return nonce, data, tag

class ProgressReporter:
    def __init__(self, total_size, progress_callback):
        self.total_size = total_size
        self.progress_callback = progress_callback
        self.raw_processed = 0
        self.last_reported = 0

    def report_progress(self, bytes_count):
        self.raw_processed += bytes_count
        # THROTTLING MASSIF : On ne met à jour l'interface que tous les 50 Mo
        # pour garantir qu'aucun débordement de buffer ne survienne sur Windows.
        if self.progress_callback and (self.raw_processed - self.last_reported >= 50 * 1024 * 1024):
            self.progress_callback(self.raw_processed, self.total_size)
            self.last_reported = self.raw_processed

def derive_key_v23(password: str, salt: b''):
    kdf = Argon2id(salt=salt, length=32, iterations=3, memory_cost=65536, parallelism=4)
    return kdf.derive(password.encode())

def encrypt_target(source_path: str, password: str, compression_level: int, delete_original=False, progress_callback=None):
    if not os.path.exists(source_path): return False, "Path not found."
    
    is_folder = os.path.isdir(source_path)
    output_path = source_path + V2_EXTENSION if not is_folder else source_path.rstrip('\\/') + V2_EXTENSION
    
    salt = secrets.token_bytes(16)
    key = derive_key_v23(password, salt)
    
    total_size = 0
    if is_folder:
        for root, _, files in os.walk(source_path):
            for f in files: total_size += os.path.getsize(os.path.join(root, f))
    else:
        total_size = os.path.getsize(source_path)

    try:
        reporter = ProgressReporter(total_size, progress_callback)
        with open(output_path, 'wb') as f_out:
            f_out.write(MAGIC_V3)
            # Flags: bit 0 = is_folder
            flags = 1 if is_folder else 0
            f_out.write(bytes([compression_level, flags]))
            f_out.write(salt)
            
            cctx = zstd.ZstdCompressor(level=compression_level, threads=0)
            with cctx.stream_writer(ChunkedGCMWriter(f_out, key)) as compressor:
                if is_folder:
                    with tarfile.open(fileobj=compressor, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                        for root, _, files in os.walk(source_path):
                            for f in files:
                                full_path = os.path.join(root, f)
                                arcname = os.path.relpath(full_path, source_path)
                                with open(full_path, 'rb') as f_in:
                                    tarinfo = tar.gettarinfo(full_path, arcname)
                                    tar.addfile(tarinfo, f_in)
                                    reporter.report_progress(tarinfo.size)
                else:
                    with open(source_path, 'rb') as f_in:
                        while chunk := f_in.read(1024*1024):
                            compressor.write(chunk)
                            reporter.report_progress(len(chunk))
        
        if delete_original:
            if is_folder:
                import shutil
                shutil.rmtree(source_path)
            else:
                os.remove(source_path)
        return True, f"Encrypted to {os.path.basename(output_path)}"
    except Exception as e:
        if os.path.exists(output_path): os.remove(output_path)
        return False, str(e)

def decrypt_file(file_path: str, password: str, progress_callback=None, delete_original=False):
    if not os.path.exists(file_path): return False, "Target not found."
    f_size = os.path.getsize(file_path)
    success, msg = False, "Format unknown."
    
    output_tmp = file_path + ".tmp"
    try:
        with open(file_path, 'rb') as f_in:
            header = f_in.read(6)
            if header == MAGIC_V3:
                comp_level, flags = f_in.read(1)[0], f_in.read(1)[0]
                salt = f_in.read(16)
                key = derive_key_v23(password, salt)
                is_folder = bool(flags & 1)
                
                with open(output_tmp, 'wb') as f_out:
                    dctx = zstd.ZstdDecompressor()
                    with dctx.stream_writer(f_out) as decompressor:
                        reader = ChunkReader(f_in)
                        while True:
                            nonce, data, tag = reader.read_next()
                            if not nonce: break
                            decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
                            decompressor.write(decryptor.update(data) + decryptor.finalize())
                            if progress_callback: progress_callback(f_in.tell(), f_size)
                
                if is_folder:
                    with tarfile.open(output_tmp, "r") as tar:
                        tar.extractall(path=os.path.dirname(file_path))
                    os.remove(output_tmp)
                else:
                    tn = file_path.replace(V2_EXTENSION, "")
                    if os.path.exists(tn): os.remove(tn)
                    os.rename(output_tmp, tn)
                
                success, msg = True, "Restoration complete."
    except cryptography.exceptions.InvalidTag:
        msg = "Security Breach: Invalid Password."
    except Exception as e:
        msg = f"System Error: {str(e)}"
    finally:
        if not success and os.path.exists(output_tmp):
            try: os.remove(output_tmp)
            except: pass
    
    # NETTOYAGE FINAL (En dehors du bloc with pour éviter WinError 32)
    if success and delete_original:
        try: os.remove(file_path)
        except: pass
        
    return success, msg

if __name__ == "__main__":
    print("AEGIS-VORTEX ENGINE V3.8 READY.")
