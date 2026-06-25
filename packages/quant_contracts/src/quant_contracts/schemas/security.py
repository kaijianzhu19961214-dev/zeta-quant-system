from typing import Any


SECRET_KEY_FRAGMENTS = (
    "access_key",
    "api_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


def assert_no_secret_keys(value: Any, path: str = "metadata") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).lower()
            if any(fragment in normalized_key for fragment in SECRET_KEY_FRAGMENTS):
                raise ValueError(f"{path}.{key} must not contain secret-like data")
            assert_no_secret_keys(item, f"{path}.{key}")
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_secret_keys(item, f"{path}[{index}]")

