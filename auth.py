"""
auth.py — CloudQuant Authentication Module
-------------------------------------------
Implements a login/logout guard for the Streamlit application.

Secret storage: .streamlit/secrets.toml on the EC2 instance (never committed to git or S3).
Password hashing: bcrypt (cost factor 12).

Key design decisions:
- Fails CLOSED: if secrets are missing or malformed, access is denied.
- All sensitive state lives in st.session_state, which is per-browser-session.
- Brute-force protection: session-level lockout after MAX_ATTEMPTS failures.
- Timing-safe comparison for username via hmac.compare_digest.
"""

import hmac
import time
import bcrypt
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_ATTEMPTS: int = 5          # Failed logins before lockout
LOCKOUT_SECONDS: int = 60      # Lockout duration in seconds


# ---------------------------------------------------------------------------
# Internal helpers — pure Python, no Streamlit dependency (testable)
# ---------------------------------------------------------------------------

def verify_password(plain: str, hashed: str) -> bool:
    """
    Returns True if `plain` matches the bcrypt `hashed` value.
    Both inputs must be non-empty strings.
    Safe against timing attacks via bcrypt's constant-time comparison.
    """
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _load_secret(key: str, subkey: str) -> str:
    """
    Reads a value from st.secrets[key][subkey].
    Calls st.error() + st.stop() (fails closed) if missing or malformed.
    Never returns an empty string.
    """
    try:
        value = st.secrets[key][subkey]
        if not value or not isinstance(value, str):
            raise ValueError("empty or non-string secret")
        return value
    except (KeyError, AttributeError, ValueError):
        st.error(
            "⛔ Authentication is not configured correctly. "
            "Contact the administrator to set up `.streamlit/secrets.toml`."
        )
        st.stop()
        return ""  # unreachable — satisfies type checkers


def _load_password_hash() -> str:
    """Loads and validates the bcrypt hash from secrets. Fails closed."""
    ph = _load_secret("auth", "password_hash")
    # Verify it looks like a bcrypt hash (starts with $2b$ or $2a$)
    if not (ph.startswith("$2b$") or ph.startswith("$2a$")):
        st.error(
            "⛔ Authentication secret is malformed (expected a bcrypt hash). "
            "Re-run the setup script on the EC2 instance."
        )
        st.stop()
    return ph


def _load_username() -> str:
    """Loads the expected username from secrets. Defaults to 'admin' if omitted."""
    try:
        value = st.secrets["auth"]["username"]
        if value and isinstance(value, str):
            return value
    except (KeyError, AttributeError):
        pass
    return "admin"


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _init_session() -> None:
    """Initialises authentication keys in session state if absent."""
    defaults = {
        "authenticated": False,
        "failed_attempts": 0,
        "lockout_until": 0.0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def is_authenticated() -> bool:
    """Returns True only if this browser session has successfully logged in."""
    return bool(st.session_state.get("authenticated", False))


def logout() -> None:
    """
    Clears all authentication state from the current session.
    Call st.rerun() after this to redirect to the login page.
    """
    for key in ("authenticated", "failed_attempts", "lockout_until"):
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Login page renderer
# ---------------------------------------------------------------------------

def render_login_page() -> None:
    """
    Renders the login form and handles credential verification.

    This function ALWAYS ends by calling st.stop() — either because
    the user is still unauthenticated, or to let Streamlit re-render
    after setting session state. Code in app.py after the auth guard
    is never reached for unauthenticated users.
    """
    _init_session()

    # ---- Lockout check ----
    lockout_remaining = st.session_state.lockout_until - time.time()
    if lockout_remaining > 0:
        st.error(
            f"⛔ Too many failed attempts. "
            f"Please wait **{int(lockout_remaining)+1} seconds** before trying again."
        )
        st.stop()

    # ---- Login UI ----
    st.set_page_config(
        page_title="CloudQuant — Login",
        page_icon="🔐",
        layout="centered",
    )

    st.markdown(
        """
        <div style="text-align:center; padding: 2rem 0 1rem 0;">
            <h1>🔐 CloudQuant</h1>
            <p style="color: #6c757d;">FT-III Cloud Computing Demo Project</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username", max_chars=64, autocomplete="username")
        password = st.text_input(
            "Password", type="password", max_chars=256, autocomplete="current-password"
        )
        submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

    if submitted:
        # Input validation
        if not username or not password:
            st.error("Please enter both username and password.")
            st.stop()

        # Load secrets (fails closed if missing/malformed)
        expected_username = _load_username()
        password_hash = _load_password_hash()

        # Verify credentials — constant-time username comparison + bcrypt password check
        username_ok = hmac.compare_digest(username.strip(), expected_username)
        password_ok = verify_password(password, password_hash)

        if username_ok and password_ok:
            # Successful login
            st.session_state.authenticated = True
            st.session_state.failed_attempts = 0
            st.session_state.lockout_until = 0.0
            st.rerun()
        else:
            # Failed login
            st.session_state.failed_attempts += 1
            remaining = MAX_ATTEMPTS - st.session_state.failed_attempts
            if remaining <= 0:
                st.session_state.lockout_until = time.time() + LOCKOUT_SECONDS
                st.error(
                    f"⛔ Too many failed attempts. "
                    f"Locked out for {LOCKOUT_SECONDS} seconds."
                )
            else:
                st.error(
                    f"❌ Invalid username or password. "
                    f"{remaining} attempt(s) remaining before lockout."
                )
            st.stop()

    # Not submitted yet — stop here so the rest of app.py doesn't execute
    st.stop()

