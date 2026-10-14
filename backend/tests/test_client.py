"""Client tests using httpx.MockTransport (no real network access)."""

import asyncio
from pathlib import Path

import httpx
import pytest

from app.client import SiraAuthError, SiraClient, SiraOperationError, SiraSessionExpired
from app.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"


def read_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_text(encoding="utf-8").encode("iso-8859-1")


def make_settings(**overrides) -> Settings:
    base = {
        "base_url": "https://sira.test/sra",
        "username": "2999999-3743",
        "password": "secret",
        "cache_ttl_seconds": 60,
    }
    base.update(overrides)
    return Settings(**base)


def make_client(settings: Settings, handler) -> SiraClient:
    client = SiraClient(settings)
    client._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=settings.base_url,
        headers={"User-Agent": "test"},
        follow_redirects=True,
    )
    return client


LOGIN_LOCATION = "https://sira.test/sra//paquetes/inicioestudiante/index.php?accion=Inicio"
EXPIRED_HTML = (
    "<html><script>alert('AVISO 5');</script>"
    "<body>Estimado Usuario, la sesión ha sido detenida.</body></html>"
)
ERROR_HTML = (
    "<html><script>alert(' AVISO 61, Lo sentimos, ha ocurrido un error "
    "durante la ejecución de la operación.');</script></html>"
)


def test_login_and_historial_flow():
    settings = make_settings()
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == "/sra/":
            if request.method == "GET":
                return httpx.Response(200, content=read_bytes("login_page.html"))
            body = request.content.decode()
            assert "usu_login_aut=2999999-3743" in body
            assert "usu_password_aut=secret" in body
            return httpx.Response(302, headers={"Location": LOGIN_LOCATION})
        if request.url.path == "/sra/paquetes/academica/index.php":
            body = request.content.decode()
            assert "accion=Consultar+Historial" in body
            assert "codigo_estudiante=2999999" in body
            return httpx.Response(200, content=read_bytes("historial.html"))
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    client = make_client(settings, handler)

    async def run():
        try:
            page = await client.get_historial()
            assert page.profile.codigo_estudiante == "202399999"
        finally:
            await client.close()

    asyncio.run(run())
    assert calls == [
        ("GET", "/sra/"),
        ("POST", "/sra/"),
        ("POST", "/sra/paquetes/academica/index.php"),
    ]


def test_login_failure_raises_auth_error():
    settings = make_settings()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, content=read_bytes("login_page.html"))
        # A failed login re-renders the login form instead of redirecting.
        return httpx.Response(200, content=read_bytes("login_page.html"))

    client = make_client(settings, handler)

    async def run():
        try:
            with pytest.raises(SiraAuthError):
                await client.login()
        finally:
            await client.close()

    asyncio.run(run())


def test_missing_credentials_raise_auth_error():
    settings = make_settings(username="", password="")
    handler = lambda request: httpx.Response(500)  # noqa: E731
    client = make_client(settings, handler)

    async def run():
        try:
            with pytest.raises(SiraAuthError):
                await client.get_historial()
        finally:
            await client.close()

    asyncio.run(run())


def test_expired_session_triggers_relogin():
    settings = make_settings()
    state = {"logins": 0, "historials": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sra/":
            if request.method == "GET":
                return httpx.Response(200, content=read_bytes("login_page.html"))
            state["logins"] += 1
            return httpx.Response(302, headers={"Location": LOGIN_LOCATION})
        if request.url.path == "/sra/paquetes/academica/index.php":
            state["historials"] += 1
            if state["historials"] == 1:
                return httpx.Response(200, content=EXPIRED_HTML.encode("iso-8859-1"))
            return httpx.Response(200, content=read_bytes("historial.html"))
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    client = make_client(settings, handler)

    async def run():
        try:
            page = await client.get_historial()
            assert page.profile.codigo_estudiante == "202399999"
        finally:
            await client.close()

    asyncio.run(run())
    assert state == {"logins": 2, "historials": 2}


def test_persistent_session_loss_raises():
    settings = make_settings()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sra/":
            if request.method == "GET":
                return httpx.Response(200, content=read_bytes("login_page.html"))
            return httpx.Response(302, headers={"Location": LOGIN_LOCATION})
        return httpx.Response(200, content=EXPIRED_HTML.encode("iso-8859-1"))

    client = make_client(settings, handler)

    async def run():
        try:
            with pytest.raises(SiraSessionExpired):
                await client.get_historial()
        finally:
            await client.close()

    asyncio.run(run())


def test_sira_error_page_raises_operation_error():
    settings = make_settings()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sra/":
            if request.method == "GET":
                return httpx.Response(200, content=read_bytes("login_page.html"))
            return httpx.Response(302, headers={"Location": LOGIN_LOCATION})
        return httpx.Response(200, content=ERROR_HTML.encode("iso-8859-1"))

    client = make_client(settings, handler)

    async def run():
        try:
            with pytest.raises(SiraOperationError):
                await client.get_historial()
        finally:
            await client.close()

    asyncio.run(run())


def test_cache_avoids_duplicate_requests():
    settings = make_settings()
    state = {"historials": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sra/":
            if request.method == "GET":
                return httpx.Response(200, content=read_bytes("login_page.html"))
            return httpx.Response(302, headers={"Location": LOGIN_LOCATION})
        state["historials"] += 1
        return httpx.Response(200, content=read_bytes("historial.html"))

    client = make_client(settings, handler)

    async def run():
        try:
            await client.get_historial()
            await client.get_historial()  # cached
            await client.get_historial(refresh=True)  # bypasses the cache
        finally:
            await client.close()

    asyncio.run(run())
    assert state["historials"] == 2
