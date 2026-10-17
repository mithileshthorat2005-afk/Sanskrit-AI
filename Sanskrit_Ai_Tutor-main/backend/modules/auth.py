"""
Authentication module for SanskritaAI
Simple user authentication for prototype
"""

import json
import os
import base64
import hashlib
import hmac
import re
import secrets
import time
from datetime import datetime

# bcrypt is a hard dependency: the previous fallback stored passwords as
# `hashed_<plaintext>`, which is trivially reversible and defeats the point of
# hashing entirely. Failing fast at import time is safer than silently
# downgrading every new user to an insecure hash.
try:
    import bcrypt
except ImportError as exc:  # pragma: no cover - exercised only without bcrypt
    raise ImportError(
        "The 'bcrypt' package is required. Install it with "
        "`pip install bcrypt` before running the server."
    ) from exc

from modules.jwt_auth import create_access_token, verify_access_token, revoke_access_token, token_is_revoked

# Prefix used by the legacy, non-cryptographic storage format. Accounts still
# carrying it are re-hashed with bcrypt on their next successful login
# (see `migrate_legacy_password`).
LEGACY_PASSWORD_PREFIX = "hashed_"

# ── Password strength policy ────────────────────────────────────────────────
# Lowercase is compulsory; length is a floor. Uppercase, digits and special
# characters are recommended rather than mandatory (they are surfaced to the
# user as an optional checklist), so "Password1!" and "sanskrit-tutor" are both
# acceptable while "0000" or "abcdefgh" are rejected outright.
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRED_MESSAGE = (
    f"Password too weak: it must be at least {PASSWORD_MIN_LENGTH} characters "
    "long and contain a lowercase letter. Adding an uppercase letter, a number "
    "or a special character (e.g. ! ? - _) is strongly recommended."
)


def password_policy_error(password):
    """Return a human-readable reason `password` is too weak, else None.

    This is the single source of truth for the policy; the signup form mirrors
    it client-side, but the server is what actually enforces it.
    """
    if not isinstance(password, str) or not password:
        return "Password cannot be empty."
    problems = []
    if len(password) < PASSWORD_MIN_LENGTH:
        problems.append(f"at least {PASSWORD_MIN_LENGTH} characters (currently {len(password)})")
    if not re.search(r"[a-z]", password):
        problems.append("at least one lowercase letter")
    if problems:
        return "Password too weak: it needs " + " and ".join(problems) + "."
    return None


# ── Username policy ──────────────────────────────────────────────────────────
# `users.json` is a flat JSON object keyed by username, so an unusable key is a
# real hazard, not a cosmetic one: an empty or whitespace-only name cannot be
# typed back reliably to log in, a control character (e.g. a newline) corrupts
# the way the file renders and any log line that echoes it, and an unbounded
# name inflates every subsequent save. The signup form performs NO client-side
# username validation, so this is the only place it is enforced.
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50

# The roles the application actually distinguishes. `role` arrives straight from
# the request body, so without this allowlist any caller could store an arbitrary
# value ("superadmin", a 4 KB string, an object) that nothing else expects.
VALID_ROLES = ("student", "teacher", "admin")


def username_policy_error(username):
    """Return a human-readable reason `username` is unacceptable, else None.

    Validation runs against the raw value rather than a silently stripped copy:
    accepting "  new  " and storing "new" would create an account the person
    cannot then log back into with the same keystrokes, so padding is rejected
    with an explicit message instead.
    """
    if not isinstance(username, str) or not username:
        return "Username cannot be empty."
    if username != username.strip():
        return "Username cannot start or end with whitespace."
    if len(username) < USERNAME_MIN_LENGTH:
        return (
            f"Username must be at least {USERNAME_MIN_LENGTH} characters "
            f"(currently {len(username)})."
        )
    if len(username) > USERNAME_MAX_LENGTH:
        return (
            f"Username must be at most {USERNAME_MAX_LENGTH} characters "
            f"(currently {len(username)})."
        )
    if any(ch.isspace() for ch in username):
        return "Username cannot contain spaces or other whitespace inside it."
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in username):
        return "Username cannot contain control characters."
    return None


def role_policy_error(role):
    """Return a human-readable reason `role` is not a supported role, else None."""
    if not isinstance(role, str) or role not in VALID_ROLES:
        return f"Role must be one of: {', '.join(VALID_ROLES)}."
    return None


def password_strength(password):
    """Coarse strength label used by the signup UI hint (weak / fair / strong)."""
    if not isinstance(password, str) or not password:
        return "empty"
    if password_policy_error(password):
        return "weak"
    classes = 1  # lowercase already proven
    if re.search(r"[A-Z]", password):
        classes += 1
    if re.search(r"\d", password):
        classes += 1
    if re.search(r"[^A-Za-z0-9]", password):
        classes += 1
    if len(password) >= 12 and classes == 4:
        return "strong"
    if classes >= 3:
        return "strong"
    if classes == 2:
        return "fair"
    return "weak"


class Authenticator:
    def __init__(self, users_file='data/users.json'):
        self.users_file = users_file
        self.users = self.load_users()
        self._users_mtime = self._file_mtime()

    def _file_mtime(self):
        """Modification time of the user store, or None if unreadable."""
        try:
            return os.path.getmtime(self.users_file)
        except OSError:
            return None

    def _read_users_file(self):
        """Read the user store without load_users()'s default-creation side effects.

        Returns a dict, or None when the file is missing/empty/corrupt so the
        caller can keep whatever it already has instead of wiping it.
        """
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if not content:
                return None
            data = json.loads(content)
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def reload_users_if_changed(self):
        """Re-read the user store when it changed on disk.

        users.json is a plain file shared by every running server process, but
        the in-memory copy used to be read exactly once, at import time. Any
        account created afterwards by *another* process was therefore invisible
        here: login() looked in a stale dict and reported "Invalid username or
        password" for a perfectly valid user. Worse, the next save() from this
        process wrote its stale view straight over the file and deleted that
        newer account. Re-checking mtime on every auth call keeps the two in
        sync; callers must invoke this *before* mutating self.users.
        """
        mtime = self._file_mtime()
        if mtime is None or mtime == self._users_mtime:
            return self.users
        users = self._read_users_file()
        if users is not None:
            self.users = users
        self._users_mtime = mtime
        return self.users
    
    def load_users(self):
        """Load users from JSON file with better error handling"""
        try:
            # Check if file exists
            if os.path.exists(self.users_file):
                # Check if file is empty
                if os.path.getsize(self.users_file) == 0:
                    print("Users file is empty. Creating default users.")
                    return self.create_default_users()
                
                # Try to load JSON
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        users = json.loads(content)
                        print("Loaded user records from file")
                        return users
                    else:
                        print("Users file is empty. Creating default users.")
                        return self.create_default_users()
            else:
                print("Users file not found. Creating default users.")
                return self.create_default_users()
                
        except json.JSONDecodeError as e:
            print("Error parsing users JSON")
            print("Creating default users...")
            return self.create_default_users()
        except Exception as e:
            print("Unexpected error loading users")
            return self.create_default_users()
    
    def create_default_users(self):
        """Create default users"""
        default_users = {
            "admin": {
                "password": self.hash_password("admin123"),
                "role": "admin",
                "created_at": datetime.now().isoformat(),
                "level": "advanced",
                "completed": 10
            },
            "demo": {
                "password": self.hash_password("demo123"),
                "role": "student",
                "created_at": datetime.now().isoformat(),
                "level": "beginner",
                "completed": 5
            }
        }
        
        # Save default users
        self.save_users(default_users)
        print("✅ Created default users")
        return default_users
    
    def save_users(self, users=None):
        """Save users to JSON file"""
        if users is None:
            users = self.users
        
        try:
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            # Write to a temporary file and swap it in, so a crash mid-write can
            # never leave a half-written (and therefore unreadable) user store
            # behind — that would silently drop every account on next startup.
            tmp_path = f"{self.users_file}.tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.users_file)
            self._users_mtime = self._file_mtime()
            print(f"✅ Users saved to {self.users_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving users: {e}")
            return False
    
    def hash_password(self, password):
        """Hash a password for storing (bcrypt only)."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, stored_password, provided_password):
        """Verify a stored password against one provided by user.
        
        Handles two formats:
        1. Legacy plaintext-equivalent: `hashed_<password>`
        2. Standard bcrypt hash
        """
        if not isinstance(stored_password, str) or not stored_password:
            return False
        
        # Legacy format check
        if stored_password.startswith(LEGACY_PASSWORD_PREFIX):
            # Constant-time comparison to prevent timing attacks
            legacy_candidate = f"{LEGACY_PASSWORD_PREFIX}{provided_password}"
            return hmac.compare_digest(stored_password, legacy_candidate)
        
        # Standard bcrypt check
        try:
            return bcrypt.checkpw(
                provided_password.encode('utf-8'),
                stored_password.encode('utf-8')
            )
        except Exception as e:
            print(f"❌ Error verifying password: {e}")
            return False
    
    def migrate_legacy_password(self, username, provided_password):
        """Upgrade a legacy `hashed_` password to bcrypt on successful login.
        
        Returns True if the migration was performed.
        """
        self.reload_users_if_changed()
        if username not in self.users:
            return False
        
        stored = self.users[username].get('password', '')
        if not stored.startswith(LEGACY_PASSWORD_PREFIX):
            return False
        
        # Re-hash with bcrypt
        self.users[username]['password'] = self.hash_password(provided_password)
        self.save_users()
        print(f"✅ Migrated legacy password for user {username} to bcrypt")
        return True
    
    def login(self, username, password):
        """Authenticate a user"""
        # Pick up accounts created by another process since we last read the file.
        self.reload_users_if_changed()
        # A corrupt store (JSON that parsed to a list/string) used to make every
        # login raise AttributeError -> HTTP 500. Treat it as "no such user".
        if not isinstance(self.users, dict):
            return None

        record = self.users.get(username)
        if not isinstance(record, dict):
            return None

        # `.get` rather than `record['password']`: a hand-edited or partially
        # migrated record with no password key used to raise KeyError and
        # surface as HTTP 500 for what is simply a failed login. An empty stored
        # value fails verification in verify_password(), so this falls through
        # to None and the endpoint reports 401 like any other bad credential.
        stored = record.get('password', '')
        if not self.verify_password(stored, password):
            return None

        # Auto-upgrade legacy hashes
        if isinstance(stored, str) and stored.startswith(LEGACY_PASSWORD_PREFIX):
            self.migrate_legacy_password(username, password)

        token = create_access_token(username)
        return {
            'username': username,
            'role': record.get('role', 'student'),
            'level': record.get('level', 'beginner'),
            'completed': record.get('completed', 0),
            'access_token': token,
            'token_type': 'bearer'
        }

    def signup(self, username, password, role="student"):
        """Create a new user account

        Raises ValueError with a user-facing message when the password is too
        weak, so the endpoint can report that directly instead of a misleading
        "Username already exists".
        """
        # See accounts another process created before deciding this name is free.
        self.reload_users_if_changed()
        if not isinstance(self.users, dict):
            self.users = {}

        # Username and role arrive straight from the request body with no client
        # validation, so both are checked here. They raise ValueError, which the
        # /auth/signup endpoint already maps to HTTP 400 with this exact message.
        problem = username_policy_error(username)
        if problem:
            raise ValueError(problem)

        problem = role_policy_error(role)
        if problem:
            raise ValueError(problem)

        if username in self.users:
            return None

        problem = password_policy_error(password)
        if problem:
            raise ValueError(problem)

        self.users[username] = {
            "password": self.hash_password(password),
            "role": role,
            "created_at": datetime.now().isoformat(),
            "level": "beginner",
            "completed": 0
        }

        if not self.save_users():
            # Roll the in-memory entry back so a failed write cannot be
            # "retried" against a store that never actually changed.
            self.users.pop(username, None)
            raise ValueError("Could not save the new account. Please try again.")
        
        token = create_access_token(username)
        return {
            'username': username,
            'role': role,
            'level': 'beginner',
            'completed': 0,
            'access_token': token,
            'token_type': 'bearer'
        }
    
    # Token verification methods now use the jwt_auth module
    def verify_access_token(self, token):
        return verify_access_token(token)
    
    def revoke_access_token(self, token):
        revoke_access_token(token)
    
    def token_is_revoked(self, token):
        return token_is_revoked(token)
