from cryptography.fernet import Fernet
from config import config

fernet = Fernet(config.encryption_key.encode())

def encrypt(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()