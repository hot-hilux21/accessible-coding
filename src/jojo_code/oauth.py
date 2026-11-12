"""OAuth 2.0 login for the optional cloud account.

This is the login half of cloud sync. It proves who the reader is and
stores the resulting tokens on this machine. Moving files to and from
Google Drive or OneDrive is a separate step that builds on this.

Only the standard library is used so the app keeps its one-dependency
(Flask) shape. Secrets come from the environment, never from config.json.
"""
import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROVIDERS = {
    "google": {
        "name": "Google",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "profile_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
    "microsoft": {
        "name": "Microsoft",
        "client_id_env": "MICROSOFT_CLIENT_ID",
        "client_secret_env": "MICROSOFT_CLIENT_SECRET",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "profile_url": "https://graph.microsoft.com/v1.0/me",
        "scope": "openid email profile User.Read",
    },
}


def _routes():
    from . import routes

    return routes


def auth_file():
    return _routes().CONFIG_DIR / "auth.json"


def client_credentials(provider):
    spec = PROVIDERS.get(provider)
    if spec is None:
        return None, None
    return (
        os.environ.get(spec["client_id_env"], "").strip(),
        os.environ.get(spec["client_secret_env"], "").strip(),
    )


def is_available(provider):
    client_id, client_secret = client_credentials(provider)
    return bool(client_id and client_secret)


def available_providers():
    return [name for name in PROVIDERS if is_available(name)]


def make_pkce():
    verifier = secrets.token_urlsafe(32)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    return verifier, challenge


def make_state():
    return secrets.token_urlsafe(24)


def authorization_url(provider, redirect_uri, state, code_verifier):
    spec = PROVIDERS[provider]
    client_id, _ = client_credentials(provider)
    _, challenge = (code_verifier, None) if False else (None, None)
    # Recompute the challenge from the verifier for callers that only pass it.
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": spec["scope"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    # Microsoft needs a prompt value only when we want consent; keep the
    # default behaviour and let the provider decide.
    return spec["authorize_url"] + "?" + urllib.parse.urlencode(params)


def _post_form(url, data):
    body = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return None, json.loads(raw.decode("utf-8", errors="replace"))
        except (ValueError, json.JSONDecodeError):
            return None, {"error": raw.decode("utf-8", errors="replace")[:200]}
    except Exception as exc:  # pragma: no cover - network failure
        return None, {"error": str(exc)}
    try:
        return json.loads(raw.decode("utf-8")), None
    except (ValueError, json.JSONDecodeError):
        return None, {"error": "invalid_json"}


def exchange_code(provider, code, redirect_uri, code_verifier):
    spec = PROVIDERS[provider]
    client_id, client_secret = client_credentials(provider)
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    return _post_form(spec["token_url"], data)


def _get_json(url, access_token):
    request = urllib.request.Request(url, method="GET")
    request.add_header("Authorization", "Bearer " + access_token)
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8")), None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return None, json.loads(raw.decode("utf-8", errors="replace"))
        except (ValueError, json.JSONDecodeError):
            return None, {"error": raw.decode("utf-8", errors="replace")[:200]}
    except Exception as exc:  # pragma: no cover - network failure
        return None, {"error": str(exc)}


def fetch_profile(provider, access_token):
    spec = PROVIDERS[provider]
    data, error = _get_json(spec["profile_url"], access_token)
    if error is not None:
        return None, error
    if provider == "google":
        return {
            "email": data.get("email", ""),
            "name": data.get("name", "") or data.get("email", ""),
            "subject": data.get("sub", ""),
        }, None
    # Microsoft Graph
    email = data.get("mail") or data.get("userPrincipalName", "")
    return {
        "email": email,
        "name": data.get("displayName", "") or email,
        "subject": data.get("id", ""),
    }, None


def load_account():
    path = auth_file()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            account = json.load(handle)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(account, dict) or "provider" not in account:
        return None
    return account


def save_account(account):
    path = auth_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Tokens are secrets. Restrict the file to the current user where the
    # platform supports it; on Windows this is a best-effort chmod.
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(account, handle, indent=2)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def clear_account():
    path = auth_file()
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def public_account(account=None):
    account = load_account() if account is None else account
    if not account:
        return None
    return {
        "provider": account.get("provider"),
        "provider_name": PROVIDERS.get(account.get("provider"), {}).get("name", ""),
        "email": account.get("email", ""),
        "name": account.get("name", ""),
        "connected_at": account.get("connected_at"),
        "expires_at": account.get("expires_at"),
    }
