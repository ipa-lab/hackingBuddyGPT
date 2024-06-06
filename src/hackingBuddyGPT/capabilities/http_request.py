import base64
from dataclasses import dataclass
import requests
from typing import Literal, Optional, Dict

from . import Capability

@dataclass
class HTTPRequest(Capability):
    host: str
    follow_redirects: bool = False
    use_cookie_jar: bool = True

    _client = requests.Session()

    def __post_init__(self):
        if not self.use_cookie_jar:
            self._client = requests

    def describe(self) -> str:
        return f"Sends a request to the host {self.host} and returns the response."

    def __call__(self,
                 method: Literal["GET", "HEAD", "POST", "PUT", "DELETE", "OPTION", "PATCH"],
                 path: str,
                 query: Optional[str] = None,
                 body: Optional[str] = None,
                 body_is_base64: Optional[bool] = False,
                 headers: Optional[Dict[str, str]] = None,
                 ) -> str:
        if body is not None and body_is_base64:
            body = base64.b64decode(body).decode()

        resp = self._client.request(
            method,
            self.host + path,
            params=query,
            data=body,
            headers=headers,
            allow_redirects=self.follow_redirects,
        )
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            return str(e)

        headers = "\r\n".join(f"{k}: {v}" for k, v in resp.headers.items())

        # turn the response into "plain text format" for responding to the prompt
        return f"HTTP/1.1 {resp.status_code} {resp.reason}\r\n{headers}\r\n\r\n{resp.text}"""
