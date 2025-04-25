import base64
from dataclasses import dataclass
from typing import Dict, Literal, Optional

import requests

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
        description = (
            f"Sends a request to the host {self.host} using the python requests library and returns the response. The schema and host are fixed and do not need to be provided.\n"
            f"Make sure that you send a Content-Type header if you are sending a body."
        )
        if self.use_cookie_jar:
            description += "\nThe cookie jar is used for storing cookies between requests."
        else:
            description += (
                "\nCookies are not automatically stored, and need to be provided as header manually every time."
            )
        if self.follow_redirects:
            description += "\nRedirects are followed."
        else:
            description += "\nRedirects are not followed."
        return description

    def __call__(
        self,
        method: Literal["GET", "HEAD", "POST", "PUT", "DELETE", "OPTION", "PATCH"],
        path: str,
        query: Optional[str] = None,
        body: Optional[str] = None,
        body_is_base64: Optional[bool] = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        if body is not None and body_is_base64:
            body = base64.b64decode(body).decode()
        if self.host[-1] != "/":
            path = "/" + path
        resp = self._client.request(
            method,
            self.host + path,
            params=query,
            data=body,
            headers=headers,
            allow_redirects=self.follow_redirects,
        )
        try:
            resp = self._client.request(
                method,
                self.host + path,
                params=query,
                data=body,
                headers=headers,
                allow_redirects=self.follow_redirects,
            )
        except requests.exceptions.RequestException as e:
            url = self.host + ("" if path.startswith("/") else "/") + path + (f"?{query}" if query else "")
            return f"Could not request '{url}': {e}"

        response_headers = "\r\n".join(f"{k}: {v}" for k, v in resp.headers.items())

        # turn the response into "plain text format" for responding to the prompt
        return f"HTTP/1.1 {resp.status_code} {resp.reason}\r\n{response_headers}\r\n\r\n{resp.text}"
