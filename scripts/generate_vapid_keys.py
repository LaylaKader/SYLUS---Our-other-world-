"""Generate a VAPID key pair for Web Push.

Run locally with: python scripts/generate_vapid_keys.py
Keep the private key secret. Put it only in Render as WEB_PUSH_VAPID_PRIVATE_KEY.
The public key may be stored as WEB_PUSH_VAPID_PUBLIC_KEY.
"""
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

private_key = ec.generate_private_key(ec.SECP256R1())
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
public_bytes = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint,
)
public_key = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii")

print("WEB_PUSH_VAPID_PUBLIC_KEY=" + public_key)
print("WEB_PUSH_VAPID_PRIVATE_KEY_PEM_BEGIN")
print(private_pem.decode("ascii"), end="")
print("WEB_PUSH_VAPID_PRIVATE_KEY_PEM_END")
