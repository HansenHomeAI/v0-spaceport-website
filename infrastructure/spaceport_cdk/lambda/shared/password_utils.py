import secrets
import string

# Avoid characters that cause confusion when typed quickly
_WORDS = [
    "orbit",
    "rocket",
    "nova",
    "astro",
    "comet",
    "vector",
    "launch",
    "stellar",
    "saturn",
    "galaxy",
    "fusion",
    "cosmic",
    "nebula",
    "zenith",
    "quasar",
    "meteor",
    "lunar",
    "solis",
]

_DIGITS = "23456789"  # skip 0/1 to avoid confusion with O/I
_LOWER = "abcdefghjkmnpqrstuvwxyz"  # omit easily confused chars
_UPPER = "ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_user_friendly_password() -> str:
    """Return a Cognito-compliant password that is easier to read and type."""

    word = secrets.choice(_WORDS)
    digits = ''.join(secrets.choice(_DIGITS) for _ in range(2))
    suffix_upper = secrets.choice(_UPPER)
    suffix_lower = secrets.choice(_LOWER)

    # Capitalize first letter to guarantee uppercase + lowercase usage
    return f"{word.capitalize()}{digits}{suffix_upper}{suffix_lower}"
