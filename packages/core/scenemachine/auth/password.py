"""
Password Hashing Utilities

Provides secure password hashing using Argon2.
Argon2 is the winner of the Password Hashing Competition (2015)
and is considered more secure than bcrypt/scrypt for password hashing.
"""

from passlib.context import CryptContext

# Password hashing context using Argon2
# Argon2 is memory-hard and resistant to GPU/ASIC attacks
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,  # Number of iterations
    argon2__parallelism=4,  # Number of parallel threads
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)
