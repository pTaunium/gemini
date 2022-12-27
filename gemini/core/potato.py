import binascii
from itertools import cycle

BASE64_TABLE = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
I2B = dict(enumerate(BASE64_TABLE))
B2I = dict((b, i) for i, b in enumerate(BASE64_TABLE))


class Potato(object):
    def __init__(self, key: str):
        self._key = self.base64_encode(key.encode())
        self._ck = cycle(self._key)

    @staticmethod
    def base64_encode(data: bytes) -> bytes:
        padding = -len(data) % 3
        r = binascii.b2a_base64(data, newline=False)
        if padding:
            r = r[:-padding]
        return r

    @staticmethod
    def base64_decode(data: bytes) -> bytes:
        padding = -len(data) % 4
        d = data + b"=" * padding
        return binascii.a2b_base64(d.decode())

    def encrypt(self, data: bytes) -> bytes:
        return bytes(I2B[(B2I[d] + B2I[k]) % 64] for k, d in zip(self._ck, data))

    def decrypt(self, data: bytes) -> bytes:
        return bytes(I2B[(64 + B2I[d] - B2I[k]) % 64] for k, d in zip(self._ck, data))

    def pack_bytes(self, data: bytes) -> str:
        return self.encrypt(self.base64_encode(data)).decode()

    def pack_str(self, data: str) -> str:
        return self.pack_bytes(data.encode())

    def unpack_bytes(self, data: str) -> bytes:
        return self.base64_decode(self.decrypt(data.encode()))

    def unpack_str(self, data: str) -> str:
        return self.unpack_bytes(data).decode()

    def reset(self) -> None:
        self._ck = cycle(self._key)
