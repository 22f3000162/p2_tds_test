"""
API Key Rotation Manager for avoiding rate limits.
Cycles through multiple Google API keys safely.
Logs all activity (usage, rotation, exhaustion).
"""

import os
import threading
from typing import List


def _log(msg: str):
    """Unified logger (goes to Tee → file → GitHub Gist)."""
    print(f"[API_ROTATOR] {msg}")


class APIKeyRotator:
    """Thread-safe manager for rotating multiple Google API keys."""

    def __init__(self):
        self._lock = threading.Lock()
        self._current_index = 0
        self._api_keys = self._load_api_keys()
        self._exhausted_keys = set()
        self._all_exhausted = False

        if not self._api_keys:
            raise ValueError("No Google API keys found in environment")

        _log(f"Loaded {len(self._api_keys)} API key(s)")

    # --------------------------------------------------
    # LOAD KEYS
    # --------------------------------------------------
    def _load_api_keys(self) -> List[str]:
        keys = []

        primary = os.getenv("GOOGLE_API_KEY")
        if primary:
            keys.append(primary)

        i = 2
        while True:
            key = os.getenv(f"GOOGLE_API_KEY_{i}")
            if not key:
                break
            keys.append(key)
            i += 1

        return keys

    # --------------------------------------------------
    # GET KEY
    # --------------------------------------------------
    def get_next_key(self) -> str:
        """
        Return the next usable API key.
        Skips exhausted keys automatically.
        """
        with self._lock:
            attempts = 0

            while self._current_index in self._exhausted_keys and attempts < len(self._api_keys):
                self._current_index = (self._current_index + 1) % len(self._api_keys)
                attempts += 1

            if attempts >= len(self._api_keys):
                _log("⚠️ All keys exhausted, returning current key anyway")

            key = self._api_keys[self._current_index]
            preview = f"...{key[-4:]}" if len(key) > 4 else "****"

            _log(
                f"Using key {self._current_index + 1}/{len(self._api_keys)} {preview}"
            )

            return key

    def get_current_key(self) -> str:
        """Return the current key without rotating."""
        with self._lock:
            return self._api_keys[self._current_index]

    def available_key_count(self) -> int:
        """Return number of non-exhausted keys (thread-safe)."""
        with self._lock:
            return self.key_count - len(self._exhausted_keys)

    # --------------------------------------------------
    # ROTATION / EXHAUSTION
    # --------------------------------------------------
    def rotate_to_next_key(self):
        """Manually rotate to the next available key."""
        with self._lock:
            old = self._current_index
            self._current_index = (self._current_index + 1) % len(self._api_keys)

            attempts = 0
            while self._current_index in self._exhausted_keys and attempts < len(self._api_keys):
                self._current_index = (self._current_index + 1) % len(self._api_keys)
                attempts += 1

            _log(f"🔄 Rotated key {old + 1} → {self._current_index + 1}")

    def mark_key_exhausted(self, key_index: int | None = None):
        """Mark a key as exhausted (rate-limited)."""
        with self._lock:
            idx = key_index if key_index is not None else self._current_index
            self._exhausted_keys.add(idx)

            _log(f"⚠️ Key {idx + 1}/{len(self._api_keys)} marked exhausted")

            if len(self._exhausted_keys) >= len(self._api_keys):
                self._all_exhausted = True
                _log(f"🚨 ALL {len(self._api_keys)} API keys exhausted")

    def are_all_keys_exhausted(self) -> bool:
        """Check if all keys are exhausted."""
        with self._lock:
            return self._all_exhausted

    def reset_exhaustion(self):
        """Reset exhaustion tracking (after cooldown)."""
        with self._lock:
            self._exhausted_keys.clear()
            self._all_exhausted = False
            _log("✓ Exhaustion state reset")

    # --------------------------------------------------
    # PROPERTIES
    # --------------------------------------------------
    @property
    def key_count(self) -> int:
        return len(self._api_keys)


# --------------------------------------------------
# GLOBAL SINGLETON ACCESS
# --------------------------------------------------
_rotator: APIKeyRotator | None = None


def get_api_key_rotator() -> APIKeyRotator:
    global _rotator
    if _rotator is None:
        _rotator = APIKeyRotator()
    return _rotator


def get_next_google_api_key() -> str:
    return get_api_key_rotator().get_next_key()
