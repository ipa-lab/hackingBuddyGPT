import base64
from dataclasses import dataclass, field
from typing import Set, Dict, Callable, Literal, Optional
import inspect

import requests
from pydantic import create_model, BaseModel

from . import Capability


@dataclass
class SubmitHTTPMethod(Capability):
    http_methods_format: str
    valid_http_methods: Set[str]
    _client = requests.Session()
    host: str
    follow_redirects: bool = False


    submitted_valid_http_methods: Set[str] = field(default_factory=set, init=False)

    def describe(self) -> str:
        return f"Submits a HTTP methods, which is the goal of all activities. The HTTP methods format is {self.http_methods_format}. If you find a flag following the that format, that you have not yet submitted, then the most important first step is to submit it, ignoring all other possibilities of further action"

    def to_model(self) -> BaseModel:
        """
        Converts the parameters of the `__call__` function of the capability to a pydantic model, that can be used to
        interface with an LLM using eg instructor or the openAI function calling API.
        The model will have the same name as the capability class and will have the same fields as the `__call__`,
        the `__call__` method can then be accessed by calling the `execute` method of the model.
        """
        sig = inspect.signature(self.__call__)
        fields = {param: (param_info.annotation, ...) for param, param_info in sig.parameters.items()}
        model_type = create_model(self.__class__.__name__, __doc__=self.describe(), **fields)

        def execute(model):
            m = model.dict()
            return self(**m)

        model_type.execute = execute

        return model_type

    def __call__(self, method: Literal["GET", "HEAD", "POST", "PUT", "DELETE", "OPTION", "PATCH"],
                 path: str,
                 query: Optional[str] = None,
                 body: Optional[str] = None,
                 body_is_base64: Optional[bool] = False,
                 headers: Optional[Dict[str, str]] = None
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

