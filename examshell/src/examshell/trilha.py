"""HTTP client for the optional Trilha app integration."""

from __future__ import annotations

import getpass
from typing import Callable

import requests


class TrilhaAPIError(Exception):
    pass


class AuthenticationError(TrilhaAPIError):
    pass


class NoActivePath(TrilhaAPIError):
    pass


class ActivityNoLongerActive(TrilhaAPIError):
    pass


class TrilhaClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10,
        source: str = "examshell",
        password_prompt: Callable[[str], str] = getpass.getpass,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.source = source
        self.password_prompt = password_prompt
        self.username: str | None = None
        self.identity: int | str | None = None
        self.session = requests.Session()

    def login(self, username: str, password: str) -> int | str:
        self.username = username
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                data={"username": username, "password": password},
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise TrilhaAPIError(f"Não consegui acessar {self.base_url}: {error}") from error
        if response.status_code == 401:
            raise AuthenticationError("Usuário ou senha inválidos.")
        if not response.ok:
            raise self._response_error(response)
        try:
            payload = response.json()
            self.identity = payload["identity"]
        except (ValueError, KeyError, TypeError) as error:
            raise TrilhaAPIError("A resposta do login não contém o campo identity esperado.") from error
        return self.identity

    def _reauthenticate(self) -> None:
        if not self.username:
            raise AuthenticationError("A sessão expirou; faça login novamente.")
        password = self.password_prompt(f"Senha do app para {self.username}: ")
        self.login(self.username, password)

    def _request(self, method: str, path: str, *, data: dict | None = None) -> requests.Response:
        try:
            response = self.session.request(method, f"{self.base_url}{path}", data=data, timeout=self.timeout)
        except requests.RequestException as error:
            raise TrilhaAPIError(f"Falha de comunicação com o app: {error}") from error
        if response.status_code == 401:
            self._reauthenticate()
            try:
                response = self.session.request(method, f"{self.base_url}{path}", data=data, timeout=self.timeout)
            except requests.RequestException as error:
                raise TrilhaAPIError(f"Falha de comunicação com o app: {error}") from error
        if response.status_code == 401:
            raise AuthenticationError("Não foi possível renovar a sessão do app.")
        return response

    def next_step(self) -> dict:
        response = self._request("GET", "/api/path/next")
        if response.status_code == 404:
            raise NoActivePath("Nenhuma trilha ativa.")
        if not response.ok:
            raise self._response_error(response)
        try:
            payload = response.json()
            step = payload["next"]
            if not isinstance(step, dict):
                raise TypeError
            return step
        except (ValueError, KeyError, TypeError) as error:
            raise TrilhaAPIError("A resposta de path/next está fora do formato esperado.") from error

    def complete(self, activity_id: int | str, correct: bool) -> dict:
        response = self._request(
            "POST",
            "/api/activity/complete",
            data={
                "activity_id": str(activity_id),
                "correct": "true" if correct else "false",
                "source": self.source,
            },
        )
        if response.status_code == 404:
            raise ActivityNoLongerActive("A atividade não pertence mais à trilha ativa.")
        if not response.ok:
            raise self._response_error(response)
        try:
            return response.json()
        except ValueError as error:
            raise TrilhaAPIError("A resposta de activity/complete não é um JSON válido.") from error

    @staticmethod
    def _response_error(response: requests.Response) -> TrilhaAPIError:
        detail = response.text.strip()
        if len(detail) > 500:
            detail = detail[:500] + "…"
        return TrilhaAPIError(f"O app respondeu HTTP {response.status_code}" + (f": {detail}" if detail else "."))
