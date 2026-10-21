"""Thin client for the PRAHARI FastAPI backend."""
import requests

from bot import config


class PrahariError(RuntimeError):
    """Raised when the PRAHARI backend is unreachable or returns an error."""


class PrahariClient:
    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = (base_url or config.PRAHARI_URL).rstrip("/")
        self.timeout = timeout or config.HTTP_TIMEOUT

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            resp = requests.request(method, url, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise PrahariError(f"PRAHARI request to {path} failed: {exc}") from exc

    def health(self) -> dict:
        return self._request("GET", "/health")

    def metrics(self) -> dict:
        return self._request("GET", "/metrics")

    def score(self, window: dict) -> dict:
        return self._request("POST", "/score", json=window)

    def scenario(self) -> dict:
        return self._request("GET", "/scenario")
