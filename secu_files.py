import os
import sys
import secrets
import shutil
import tarfile
import io
import cryptography.exceptions
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.backends import default_backend
import zstandard as zstd

# --- CONFIGURATION ---
MAGIC_V2 = b"SECUV2"
MAGIC_V3 = b"SECUV3"
V2_EXTENSION = ".127"
CHUNK_SIZE_IO = 128 * 1024 # 128KB reads for performance
V3_DATA_CHUNK = 32 * 1024 * 1024 # 32MB chunks for AES-GCM (Balance between RAM and Speed)

# --- DÉRIVATION DE CLÉ ---

def derive_key_v23(password: str, salt: bytes) -> bytes:
    kdf = Argon2id(salt=salt, length=32, iterations=3, memory_cost=65536, lanes=4)
    return kdf.derive(password.encode('utf-8'))

# --- HELPERS ---

class ChunkedGCMWriter(io.IOBase):
    def __init__(self, f_out, key, chunk_size, progress_callback=None, total_size=None):
        self.f_out = f_out
        self.key = key
        self.chunk_size = chunk_size
        self.buffer = bytearray()
        self.progress_callback = progress_callback
        self.total_size = total_size
        self.raw_processed = 0
        self.last_reported = 0

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

    def report_progress(self, bytes_count):
        self.raw_processed += bytes_count
        # THROTTLING MASSIF : On ne met à jour l'interface que tous les 50 Mo
        # pour garantir qu'aucun débordement de buffer ne survienne sur Windows.
        if self.progress_callback and (self.raw_processed - self.last_reported >= 50 * 1024 * 1024):
            self.progress_callback(self.raw_processed, self.total_size)
            self.last_reported = self.raw_processed

    def finalize(self):
        if self.buffer:
            self._encrypt_and_write(bytes(self.buffer))
            self.buffer.clear()

    def writable(self): return True
    def seekable(self): return False

class TarStreamWriter(io.IOBase):
    def __init__(self, writer, gcm_writer):
        self.writer = writer
        self.gcm_writer = gcm_writer
    def write(self, b):
        self.gcm_writer.report_progress(len(b))
        return self.writer.write(b)
    def writable(self): return True

class ChunkReader:
    def __init__(self, f_in):
        self.f_in = f_in
    def read_next(self):
        nonce = self.f_in.read(12)
        if not nonce: return None, None, None
        lb = self.f_in.read(4)
        if not lb: return None, None, None
        length = int.from_bytes(lb, 'big')
        data = self.f_in.read(length)
        if len(data) < length: return None, None, None
        tag = self.f_in.read(16)
        return nonce, data, tag

# --- CORE LOGIC ---

def encrypt_target(target_path: str, password: str, comp_level: int = 3, delete_original: bool = False, progress_callback=None):
    if not os.path.exists(target_path): return False, "Path not found."
    is_folder = os.path.isdir(target_path)
    output_path = target_path + V2_EXTENSION
    salt = secrets.token_bytes(16)
    key = derive_key_v23(password, salt)
    
    total_size = 0
    if is_folder:
        for r, ds, fs in os.walk(target_path):
            for f in fs: total_size += os.path.getsize(os.path.join(r, f))
    else: total_size = os.path.getsize(target_path)

    try:
        with open(output_path, 'wb') as f_out:
            f_out.write(MAGIC_V3 + bytes([comp_level, 1 if is_folder else 0]) + salt)

            cctx = zstd.ZstdCompressor(level=comp_level, threads=-1)
            gcm_writer = ChunkedGCMWriter(f_out, key, V3_DATA_CHUNK, progress_callback, total_size)
            
            with cctx.stream_writer(gcm_writer) as zstd_stream:
                if is_folder:
                    tw = TarStreamWriter(zstd_stream, gcm_writer)
                    with tarfile.open(fileobj=tw, mode='w|') as tar:
                        tar.add(target_path, arcname=os.path.basename(target_path))
                else:
                    with open(target_path, 'rb') as f_in:
                        while True:
                            chunk = f_in.read(CHUNK_SIZE_IO)
                            if not chunk: break
                            zstd_stream.write(chunk)
                            gcm_writer.report_progress(len(chunk))
            
            gcm_writer.finalize()

        if delete_original:
            if is_folder: shutil.rmtree(target_path)
            else: os.remove(target_path)
        return True, "Encryption successful (V3.5 TURBO)."
    except Exception as e:
        if os.path.exists(output_path): os.remove(output_path)
        return False, str(e)

def decrypt_file(file_path: str, password: str, progress_callback=None, delete_original=False):
    if not os.path.exists(file_path): return False, "Target not found."
    f_size = os.path.getsize(file_path)
    
    with open(file_path, 'rb') as f_in:
        header = f_in.read(6)
        if header == MAGIC_V3:
            comp_level, flags = f_in.read(1)[0], f_in.read(1)[0]
            salt = f_in.read(16)
            key = derive_key_v23(password, salt)
            
            is_folder, output_tmp = bool(flags & 1), file_path + ".tmp"
            try:
                with open(output_tmp, 'wb') as f_out:
                    dctx = zstd.ZstdDecompressor()
                    with dctx.stream_writer(f_out) as decompressor:
                        reader = ChunkReader(f_in)
                        while True:
                            nonce, data, tag = reader.read_next()
                            if not nonce: break
                            try:
                                decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
                                decompressor.write(decryptor.update(data) + decryptor.finalize())
                            except cryptography.exceptions.InvalidTag:
                                return False, "Security Breach: Invalid Password."
                            
                            if progress_callback: progress_callback(f_in.tell(), f_size)
                
                if is_folder:
                    with tarfile.open(output_tmp, "r") as tar:
                        tar.extractall(path=os.path.dirname(file_path))
                    os.remove(output_tmp)
                else:
                    tn = file_path.replace(V2_EXTENSION, "")
                    if os.path.exists(tn): os.remove(tn)
                    os.rename(output_tmp, tn)
                
                # NETTOYAGE POST-OPÉRATION
                if delete_original:
                    os.remove(file_path)
                    
                return True, "Restoration complete."
            except Exception as e:
                if os.path.exists(output_tmp): os.remove(output_tmp)
                return False, str(e)
        return False, "Format unknown."

if __name__ == "__main__":
    print("AEGIS-VORTEX ENGINE V3.8 READY.")
