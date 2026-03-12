"""
Vikunja async HTTP client with JWT auth and per-user token minting.

API semantics:
  PUT  /api/v1/projects/{id}/tasks  -> create task (returns 200)
  POST /api/v1/tasks/{id}           -> update task (returns 200)
  GET  /api/v1/projects/{id}/tasks  -> list tasks
  GET  /api/v1/tasks/{id}           -> get single task
  POST /api/v1/login                -> authenticate, returns {"token": "..."}

Per-user auth:
  When VIKUNJA_JWT_SECRET is set, the client can mint JWTs for any Vikunja user
  by username, enabling per-user task ownership. If a user doesn't exist in
  Vikunja yet, they are auto-created via the registration API using the service
  account's admin-level access (or direct DB insert as fallback).
"""
import logging
import time
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Refresh JWT this many seconds before it expires to avoid races.
_REFRESH_MARGIN_SECS = 300

# Cache minted per-user tokens: {username: (token, expiry)}
_user_token_cache: dict[str, tuple[str, float]] = {}


class VikunjaClient:
    """Async httpx client for the Vikunja REST API."""

    def __init__(
        self,
        api_url: str,
        username: str,
        password: str,
        jwt_secret: str | None = None,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._username = username
        self._password = password
        self._jwt_secret = jwt_secret
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._http = httpx.AsyncClient(timeout=30.0)
        # Cache user lookups: {username: {id, default_project_id, ...}}
        self._user_cache: dict[str, dict] = {}
        # Cache project name → ID: {"user:name": project_id}
        self._project_cache: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Auth — service account (password-based login)
    # ------------------------------------------------------------------

    async def _login(self) -> None:
        """Obtain a fresh JWT from Vikunja for the service account."""
        resp = await self._http.post(
            f"{self._api_url}/api/v1/login",
            json={"username": self._username, "password": self._password},
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["token"]
        try:
            import base64, json as _json
            payload_b64 = self._token.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            claims = _json.loads(base64.urlsafe_b64decode(payload_b64))
            self._token_expiry = float(claims.get("exp", time.time() + 3600))
        except Exception:
            self._token_expiry = time.time() + 3600
        logger.info("Vikunja service JWT obtained, expires at %s", self._token_expiry)

    async def _service_auth_headers(self) -> dict[str, str]:
        """Return service account Authorization headers."""
        if self._token is None or time.time() >= self._token_expiry - _REFRESH_MARGIN_SECS:
            await self._login()
        return {"Authorization": f"Bearer {self._token}"}

    # ------------------------------------------------------------------
    # Auth — per-user JWT minting
    # ------------------------------------------------------------------

    def _mint_user_jwt(self, user_id: int, username: str) -> tuple[str, float]:
        """Mint a Vikunja JWT for a specific user using the shared secret."""
        import jwt as pyjwt

        exp = int(time.time()) + 3600
        payload = {
            "id": user_id,
            "username": username,
            "exp": exp,
            "jti": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "type": 1,
        }
        token = pyjwt.encode(payload, self._jwt_secret, algorithm="HS256")
        logger.info("Minted JWT for user=%s (id=%d)", username, user_id)
        return token, float(exp)

    async def _get_user_token(self, username: str) -> str:
        """Get a valid JWT for the given username, minting if needed."""
        if not self._jwt_secret:
            raise RuntimeError("VIKUNJA_JWT_SECRET not configured; cannot mint per-user tokens")

        # Check cache
        if username in _user_token_cache:
            token, expiry = _user_token_cache[username]
            if time.time() < expiry - _REFRESH_MARGIN_SECS:
                return token

        # Look up or create the user
        user_info = await self._resolve_user(username)
        token, expiry = self._mint_user_jwt(user_info["id"], username)
        _user_token_cache[username] = (token, expiry)
        return token

    async def _user_auth_headers(self, username: str) -> dict[str, str]:
        """Return Authorization headers for a specific user."""
        token = await self._get_user_token(username)
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------
    # User resolution — look up or auto-create
    # ------------------------------------------------------------------

    async def _resolve_user(self, username: str) -> dict:
        """Look up a Vikunja user by username; auto-create if not found."""
        if username in self._user_cache:
            return self._user_cache[username]

        # Try to find the user via API using the service account
        headers = await self._service_auth_headers()
        resp = await self._http.get(
            f"{self._api_url}/api/v1/users",
            headers=headers,
            params={"s": username},
        )

        if resp.status_code == 200:
            users = resp.json() or []
            for u in users:
                if u.get("username") == username:
                    user_info = {"id": u["id"], "username": username}
                    # Get default project via the user's own profile (needs their JWT)
                    user_info["default_project_id"] = await self._get_default_project_for_user(
                        u["id"], username
                    )
                    self._user_cache[username] = user_info
                    logger.info("Resolved user %s → id=%d, default_project=%s",
                                username, u["id"], user_info["default_project_id"])
                    return user_info

        # User not found — auto-create
        logger.info("User %s not found in Vikunja, auto-creating...", username)
        return await self._create_user(username)

    async def _get_default_project_for_user(self, user_id: int, username: str) -> int | None:
        """Fetch a user's default_project_id by querying their profile with a minted JWT."""
        token, _ = self._mint_user_jwt(user_id, username)
        headers = {"Authorization": f"Bearer {token}"}
        resp = await self._http.get(f"{self._api_url}/api/v1/user", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("settings", {}).get("default_project_id")
        return None

    async def _create_user(self, username: str) -> dict:
        """Create a new local Vikunja user account.

        Uses the Vikunja registration API (POST /api/v1/register).
        The user gets a random password since they'll auth via OIDC in the web UI
        and via minted JWTs through the MCP server.
        """
        random_password = str(uuid.uuid4()) + "Aa1!"  # Meets complexity requirements
        email = f"{username}@vikunja.local"

        resp = await self._http.post(
            f"{self._api_url}/api/v1/register",
            json={
                "username": username,
                "password": random_password,
                "email": email,
            },
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            user_id = data["id"]
            # Fetch default project via the new user's profile
            default_project = await self._get_default_project_for_user(user_id, username)
            user_info = {
                "id": user_id,
                "username": username,
                "default_project_id": default_project,
            }
            self._user_cache[username] = user_info
            logger.info("Auto-created Vikunja user %s → id=%d, default_project=%s",
                        username, user_id, default_project)
            return user_info

        # Registration might be disabled — log and raise
        logger.error("Failed to create user %s: %d %s", username, resp.status_code, resp.text)
        raise RuntimeError(
            f"Cannot create Vikunja user '{username}': {resp.status_code} {resp.text}. "
            "User must log in via Vikunja web UI first to create their account."
        )

    # ------------------------------------------------------------------
    # HTTP request helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
        retry: bool = True,
        username: str | None = None,
    ) -> Any:
        """Execute an authenticated request; retry once on 401.

        If username is provided and jwt_secret is configured, authenticate
        as that user. Otherwise use the service account.
        """
        if username and self._jwt_secret:
            headers = await self._user_auth_headers(username)
        else:
            headers = await self._service_auth_headers()

        resp = await self._http.request(
            method, f"{self._api_url}{path}", headers=headers, json=json, params=params
        )
        if resp.status_code == 401 and retry:
            # Token rejected — clear cache and retry
            if username and username in _user_token_cache:
                del _user_token_cache[username]
            else:
                self._token = None
                self._token_expiry = 0.0
            return await self._request(
                method, path, json=json, params=params, retry=False, username=username
            )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------

    async def list_tasks(self, project_id: int, *, username: str | None = None) -> list[dict]:
        """Return all tasks for a project."""
        return await self._request(
            "GET", f"/api/v1/projects/{project_id}/tasks", username=username
        )

    async def create_task(
        self,
        project_id: int,
        title: str,
        description: str = "",
        bucket_id: int | None = None,
        priority: int | None = None,
        due_date: str | None = None,
        *,
        username: str | None = None,
    ) -> dict:
        """Create a task inside a project using PUT (Vikunja API convention)."""
        payload: dict[str, Any] = {"title": title, "description": description}
        if bucket_id is not None:
            payload["bucket_id"] = bucket_id
        if priority is not None:
            payload["priority"] = priority
        if due_date is not None:
            payload["due_date"] = due_date
        return await self._request(
            "PUT", f"/api/v1/projects/{project_id}/tasks", json=payload, username=username
        )

    async def update_task(
        self,
        task_id: int,
        title: str | None = None,
        done: bool | None = None,
        description: str | None = None,
        priority: int | None = None,
        due_date: str | None = None,
        *,
        username: str | None = None,
    ) -> dict:
        """Update one or more fields of an existing task using POST."""
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if done is not None:
            payload["done"] = done
        if description is not None:
            payload["description"] = description
        if priority is not None:
            payload["priority"] = priority
        if due_date is not None:
            payload["due_date"] = due_date
        return await self._request(
            "POST", f"/api/v1/tasks/{task_id}", json=payload, username=username
        )

    async def get_task(self, task_id: int, *, username: str | None = None) -> dict:
        """Retrieve a single task by its ID."""
        return await self._request("GET", f"/api/v1/tasks/{task_id}", username=username)

    async def get_user_default_project(self, username: str) -> int | None:
        """Return the default project ID for a user, or None."""
        user_info = await self._resolve_user(username)
        return user_info.get("default_project_id")

    # ------------------------------------------------------------------
    # Project resolution by name (with auto-create)
    # ------------------------------------------------------------------

    async def resolve_project_by_name(
        self, project_name: str, *, username: str | None = None
    ) -> int:
        """Resolve a project name to its ID for the given user.

        If the project doesn't exist, it is created under the user's account.
        Uses a per-user cache to avoid repeated API calls.
        """
        cache_key = f"{username or '_service'}:{project_name.lower()}"
        if cache_key in self._project_cache:
            return self._project_cache[cache_key]

        if username and self._jwt_secret:
            headers = await self._user_auth_headers(username)
        else:
            headers = await self._service_auth_headers()

        # List user's projects and search by title (case-insensitive)
        resp = await self._http.get(
            f"{self._api_url}/api/v1/projects", headers=headers
        )
        if resp.status_code == 200:
            projects = resp.json() or []
            for p in projects:
                if p.get("title", "").lower() == project_name.lower():
                    pid = p["id"]
                    self._project_cache[cache_key] = pid
                    logger.info("Resolved project '%s' → id=%d (user=%s)",
                                project_name, pid, username)
                    return pid

        # Project not found — create it
        logger.info("Project '%s' not found for user=%s, creating...", project_name, username)
        resp = await self._http.put(
            f"{self._api_url}/api/v1/projects",
            headers=headers,
            json={"title": project_name},
        )
        if resp.status_code in (200, 201):
            pid = resp.json()["id"]
            self._project_cache[cache_key] = pid
            logger.info("Created project '%s' → id=%d (user=%s)", project_name, pid, username)
            return pid

        raise RuntimeError(
            f"Failed to create project '{project_name}' for {username}: "
            f"{resp.status_code} {resp.text}"
        )

    async def aclose(self) -> None:
        await self._http.aclose()
