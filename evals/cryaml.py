import argparse
import base64
import os
from dataclasses import dataclass
from getpass import getpass
from typing import Callable

import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SECRET_META_KEY = "$secret_meta"
SECRET_META_SALT = "salt"
SECRET_META_VERIFIER = "verifier"
SECRET_FIELD_NAME = "$secret"
SECRET_VERIFIER_PLAINTEXT = "cryamlsecret0.1"
SECRET_DEFAULT_ITERATIONS = 390000


decrypt_function = Callable[[str], str]
encrypt_function = Callable[[str], str]


@dataclass
class SecretMeta:
    salt_bytes: bytes
    verifier: str

    @property
    def salt_b64(self) -> str:
        return base64.b64encode(self.salt_bytes).decode("utf-8")

    def assert_password(self, password: str):
        try:
            plain = _decrypt_with_password(self.verifier, password, self.salt_bytes, SECRET_DEFAULT_ITERATIONS)
        except Exception as exc:
            raise ValueError(f"Incorrect password for encrypted secrets. {exc}") from exc

        if plain != SECRET_VERIFIER_PLAINTEXT:
            raise ValueError(f"Incorrect password for encrypted secrets. {plain}")

    def store(self) -> dict:
        return {
            SECRET_META_SALT: self.salt_b64,
            SECRET_META_VERIFIER: self.verifier,
        }

    @classmethod
    def load(cls, meta: dict) -> "SecretMeta":
        missing = [field for field in (SECRET_META_SALT, SECRET_META_VERIFIER) if field not in meta]
        if missing:
            raise ValueError(f"missing {', '.join(missing)} in {SECRET_META_KEY}.")

        salt_b64 = meta[SECRET_META_SALT]
        if not isinstance(salt_b64, str):
            raise ValueError(f"{SECRET_META_SALT} must be a base64 string.")
        try:
            salt_bytes = base64.b64decode(salt_b64.encode("utf-8"))
        except Exception as exc:
            raise ValueError("invalid base64 salt.") from exc

        verifier = meta[SECRET_META_VERIFIER]
        if not isinstance(verifier, str):
            raise ValueError(f"{SECRET_META_VERIFIER} must be a string.")

        return cls(
            salt_bytes=salt_bytes,
            verifier=verifier,
        )

    @classmethod
    def new_from_password(cls, password: str) -> "SecretMeta":
        if not password:
            raise ValueError("Password cannot be empty.")

        salt_bytes = os.urandom(16)
        verifier = _encrypt_with_password(SECRET_VERIFIER_PLAINTEXT, password, salt_bytes, SECRET_DEFAULT_ITERATIONS)

        return cls(
            salt_bytes=salt_bytes,
            verifier=verifier,
        )


def _derive_key(password: str, salt_bytes: bytes, iterations: int) -> bytes:
    if not password:
        raise ValueError("Password for encrypted secrets cannot be empty.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_bytes,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _build_fernet(password: str, salt_bytes: bytes, iterations: int) -> Fernet:
    return Fernet(_derive_key(password, salt_bytes, iterations))


def _encrypt_with_password(value: str, password: str, salt_bytes: bytes, iterations: int) -> str:
    token = _build_fernet(password, salt_bytes, iterations).encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def _decrypt_with_password(token: str, password: str, salt_bytes: bytes, iterations: int) -> str:
    plaintext = _build_fernet(password, salt_bytes, iterations).decrypt(token.encode("utf-8"))
    return plaintext.decode("utf-8")


def _replace_secret_nodes(node, decrypt_cb: decrypt_function, path=""):
    if isinstance(node, dict):
        if SECRET_FIELD_NAME in node:
            secret_value = node[SECRET_FIELD_NAME]
            if not isinstance(secret_value, str):
                raise ValueError(f"{path}: {SECRET_FIELD_NAME} values must be strings.")
            try:
                return decrypt_cb(secret_value)
            except Exception as exc:
                raise ValueError(f"{path}: Failed to decrypt secret: {exc}") from exc
        for key in list(node.keys()):
            if key == SECRET_META_KEY:
                continue
            node[key] = _replace_secret_nodes(node[key], decrypt_cb, f"{path}/{key}")
        return node
    if isinstance(node, list):
        for idx, item in enumerate(node):
            node[idx] = _replace_secret_nodes(item, decrypt_cb, f"{path}/{idx}")
        return node
    return node


def process_config_secrets(cfg: dict, password: str | None = None) -> dict:
    # if our header isn't there, then it's probably not encrypted and we just do identity
    if SECRET_META_KEY not in cfg or not isinstance(cfg[SECRET_META_KEY], dict):
        return cfg

    meta = SecretMeta.load(cfg[SECRET_META_KEY])

    def ensure_password():
        nonlocal password
        if password is None:
            _password: str | None = getpass("Enter password for encrypted config secrets: ")
            if not _password:
                raise ValueError("Password for encrypted secrets cannot be empty.")

            meta.assert_password(_password)
            password = _password

        return password

    def decrypt_token(token: str) -> str:
        return _decrypt_with_password(token, ensure_password(), meta.salt_bytes, SECRET_DEFAULT_ITERATIONS)

    return _replace_secret_nodes(cfg, decrypt_token)


def handle_secret_creation(
    cfg: dict | None, password: str | None = None, value: str | None = None
) -> tuple[SecretMeta, str]:
    cfg = cfg or {}
    if password is None:
        password = getpass("Enter password for encrypted config secrets: ")
        if not password:
            raise ValueError("Password for encrypted secrets cannot be empty.")

    if SECRET_META_KEY in cfg:
        meta = SecretMeta.load(cfg[SECRET_META_KEY])
    else:
        meta = SecretMeta.new_from_password(password)

    meta.assert_password(password)

    if value is None:
        value = getpass("Enter value to encrypt (input hidden): ")
    token = _encrypt_with_password(value, password, meta.salt_bytes, SECRET_DEFAULT_ITERATIONS)

    return meta, token


def main_secret_creation(yaml_path: str):
    cfg: dict | None = None
    if yaml_path and os.path.exists(yaml_path):
        with open(yaml_path, "r") as f:
            cfg = yaml.safe_load(f)

    meta, token = handle_secret_creation(cfg)
    print("Encrypted YAML snippet:")
    print(f"{SECRET_FIELD_NAME}: {token}")
    if cfg is None:
        print("\nAdd this top-level block to your config to enable secret verification:")
        print(f"{SECRET_META_KEY}:")
        print(f"  {SECRET_META_SALT}: {meta.salt_b64}")
        print(f"  {SECRET_META_VERIFIER}: {meta.verifier}")


def main_decrypt(yaml_path: str):
    cfg: dict | None = None
    if yaml_path and os.path.exists(yaml_path):
        with open(yaml_path, "r") as f:
            cfg = yaml.safe_load(f)

    if cfg is None:
        print("No config found at", yaml_path)
        return

    yaml.dump(process_config_secrets(cfg))


def main_test_roundtrip():
    password = base64.b64encode(os.urandom(16)).decode()
    print("# password:", password)
    secret = base64.b64encode(os.urandom(16)).decode()
    print("# secret:", secret)
    meta, encrypted = handle_secret_creation(None, password, secret)
    document = {
        SECRET_META_KEY: meta.store(),
        "secret": {SECRET_FIELD_NAME: encrypted},
    }
    print("# document:\n", yaml.safe_dump(document), sep="")

    decrypted = process_config_secrets(document, password)
    print("# decrypted:\n", yaml.safe_dump(document), sep="")

    assert decrypted["secret"] == secret
    print("works!")


def main():
    parser = argparse.ArgumentParser(description="Decrypt a yaml file or encrypt a secret value")
    subparsers = parser.add_subparsers(dest="command")
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt a secret value")
    encrypt_parser.add_argument("--yaml", help="Path to the yaml file", required=False)
    decrypt_parser = subparsers.add_parser("decrypt", help="Decrypt a yaml file")
    decrypt_parser.add_argument("--yaml", help="Path to the yaml file", required=False)
    decrypt_parser = subparsers.add_parser("test", help="Test encryption and decryption")
    args = parser.parse_args()

    if args.command == "encrypt":
        main_secret_creation(args.yaml)
    elif args.command == "decrypt":
        main_decrypt(args.yaml)
    elif args.command == "test":
        main_test_roundtrip()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
