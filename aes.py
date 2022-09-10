import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES


class AESCipher(object):

    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw.encode('utf-8'))).decode('utf-8')

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]

    def pad_f(self, s):
        return s + b"\0" * (AES.block_size - len(s) % AES.block_size)
    
    def encrypt_f(self, message):
        message = self.pad_f(message)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(message)
    
    def decrypt_f(self, ciphertext):
        iv = ciphertext[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        plaintext = cipher.decrypt(ciphertext[AES.block_size:])
        return plaintext.rstrip(b"\0")
    
    def encrypt_file(self, file_in, file_out):
        with open(file_in, 'rb') as fo:
            plaintext = fo.read()
        enc = self.encrypt_f(plaintext)
        with open(file_out, 'wb') as fo:
            fo.write(enc)
    
    def decrypt_file(self, file_in, file_out):
        with open(file_in, 'rb') as fo:
            ciphertext = fo.read()
        dec = self.decrypt_f(ciphertext)
        with open(file_out, 'wb') as fo:
            fo.write(dec)
