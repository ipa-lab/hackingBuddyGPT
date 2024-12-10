import base64
from dataclasses import dataclass, field
from typing import Callable, Dict, Literal, Optional, Set

import requests

from . import Capability


@dataclass
class SubmitHTTPMethod(Capability):
    http_methods_format: str
    valid_http_methods: Set[str]
    _client = requests.Session()
    host: str
    follow_redirects: bool = False
    success_function: Callable[[], None] = None

    submitted_valid_http_methods: Set[str] = field(default_factory=set, init=False)

    def describe(self) -> str:
        return f"Submits a HTTP methods, which is the goal of all activities. The HTTP methods format is {self.http_methods_format}. If you find a flag following the that format, that you have not yet submitted, then the most important first step is to submit it, ignoring all other possibilities of further action"

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
        if len(self.submitted_valid_http_methods) == len(self.valid_http_methods):
            if self.success_function is not None:
                self.success_function()
            else:
                return "All methods submitted, congratulations"
        # turn the response into "plain text format" for responding to the prompt
        return f"HTTP/1.1 {resp.status_code} {resp.reason}\r\n{headers}\r\n\r\n{resp.text}"
