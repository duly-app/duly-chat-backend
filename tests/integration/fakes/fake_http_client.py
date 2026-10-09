from typing import Any

from src.adapters.api.duly_api import HTTPClient, HTTPResponse


class FakeResponse(HTTPResponse):
    """A response that always succeeded, carrying a canned payload."""

    _payload: Any

    def __init__(self, payload: Any):
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> Any:
        return self._payload


class FakeHTTPClient(HTTPClient):
    """Records the requests made to it and answers from a canned payload.

    Stands in for requests.Session so the adapter's wire behaviour — the URL,
    the body, the headers — can be asserted without a server.
    """

    _payload: Any
    _collection_payload: Any
    calls: list[dict[str, Any]]

    def __init__(self, payload: Any = None, collection_payload: Any = None):
        self._payload = payload
        self._collection_payload = collection_payload
        self.calls: list[dict[str, Any]] = []

    @property
    def last_call(self) -> dict[str, Any]:
        assert self.calls, "No request was made"

        return self.calls[-1]

    def get(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self._record("get", url, self._collection_payload, **kwargs)

    def post(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self._record("post", url, self._payload, **kwargs)

    def put(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self._record("put", url, self._payload, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self._record("delete", url, None, **kwargs)

    def _record(self, verb: str, url: str, payload: Any, **kwargs: Any) -> HTTPResponse:
        self.calls.append({"verb": verb, "url": url, **kwargs})

        return FakeResponse(payload)
