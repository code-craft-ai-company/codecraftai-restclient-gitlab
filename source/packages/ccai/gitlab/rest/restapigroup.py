from typing import TYPE_CHECKING

import weakref

if TYPE_CHECKING:
    from ccai.gitlab.rest.restclientbase import RestClientBase


class RestApiGroup:

    def __init__(self, client: "RestClientBase"):
        self._client_ref = weakref.ref(client)
        return
    
    @property
    def client(self) -> "RestClientBase":
        return self._client_ref()