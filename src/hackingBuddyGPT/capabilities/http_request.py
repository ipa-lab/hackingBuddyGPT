import os
import base64
from dataclasses import dataclass
from typing import Literal, override

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
        else:
            self._client = requests.Session()
            if "CLIENT_HTTP_PROXY" in os.environ or "CLIENT_HTTPS_PROXY" in os.environ:
                import urllib3

                urllib3.disable_warnings()
                self._client.verify = False
                if "CLIENT_HTTP_PROXY" in os.environ:
                    self._client.proxies["http"] = os.environ["CLIENT_HTTP_PROXY"]
                if "CLIENT_HTTPS_PROXY" in os.environ:
                    self._client.proxies["https"] = os.environ["CLIENT_HTTPS_PROXY"]

    @override
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

    @override
    async def __call__(
        self,
        method: Literal["GET", "HEAD", "POST", "PUT", "DELETE", "OPTION", "PATCH"],
        path: str,
        query: str | None = None,
        body: str | None = None,
        body_is_base64: bool | None = False,
        headers: dict[str, str] | None = None,
        hide_binary_response: bool | None = True,
    ) -> str:
        ## TODO: make async by using aiohttp

        if body is not None and body_is_base64:
            body = base64.b64decode(body).decode()
        if self.host[-1] != "/" and not path.startswith("/"):
            path = "/" + path
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

        try:
            response_text = resp.content.decode("utf-8")
        except UnicodeDecodeError:
            if hide_binary_response:
                response_text = f"<binary data hidden, {len(resp.content)} bytes, call with hide_binary_response=False to see the binary data>"
            else:
                response_text = resp.text

        # turn the response into "plain text format" for responding to the prompt
        return f"HTTP/1.1 {resp.status_code} {resp.reason}\r\n{response_headers}\r\n\r\n{response_text}"
