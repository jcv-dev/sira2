"""Async HTTP client for SIRA (read-only).

Handles login, cookie session, polite request serialization, TTL caching and
automatic re-login when SIRA kills the session (SIRA only allows one active
session per user, so this happens whenever you open the web UI in a browser).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, TypeVar

import httpx

from . import parsers
from .config import Settings
from .models import (
    ContactInfo,
    Enrollment,
    Equivalences,
    PersonHeader,
    PeriodOption,
    PeriodResult,
    PrerequisiteItem,
    StudentProfile,
)

logger = logging.getLogger("sira.client")

T = TypeVar("T")

ACADEMICA_URL = "/paquetes/academica/index.php"
TABULADO_URL = "/paquetes/matricula/index_publico.php"
CONTACTO_URL = "/paquetes/tablaMaestro/persona/index.php"
RESOLUCION_URL = "/paquetes/resolucionporprograma/index.php"
EQUIVALENCIAS_URL = "/paquetes/equivalencias/index_publico.php"
HOME_URL = "/paquetes/inicioestudiante/index.php?accion=Inicio"
LOGOUT_URL = "/paquetes/autenticacion/salir.php"


class SiraError(Exception):
    """Base class for SIRA client errors."""


class SiraAuthError(SiraError):
    """Login failed or credentials missing."""


class SiraSessionExpired(SiraError):
    """SIRA dropped our session and re-login did not help."""


class SiraOperationError(SiraError):
    """SIRA returned its generic error page."""


def short_student_code(code: str | None) -> str | None:
    """Kept for backwards compatibility; see parsers.short_student_code."""
    return parsers.short_student_code(code)


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl = max(1, ttl_seconds)
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        hit = self._data.get(key)
        if hit is None:
            return None
        expires, value = hit
        if expires < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._data[key] = (time.monotonic() + self.ttl, value)

    def clear(self) -> None:
        self._data.clear()


class SiraClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._http = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            headers={
                "User-Agent": settings.user_agent,
                "Accept-Language": "es-CO,es;q=0.9",
            },
            follow_redirects=True,
        )
        self._request_lock = asyncio.Lock()  # serialize upstream requests (be polite)
        self._login_lock = asyncio.Lock()
        self._cache = TTLCache(settings.cache_ttl_seconds)
        self._logged_in = False
        self._username: str | None = settings.username or None
        self._password: str | None = settings.password or None

    # -- infrastructure -----------------------------------------------------

    async def close(self) -> None:
        await self._http.aclose()

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    @property
    def username(self) -> str | None:
        return self._username

    @property
    def credentials_configured(self) -> bool:
        return bool(self._username and self._password)

    @property
    def student_code(self) -> str | None:
        """Short student code derived from the login (e.g. 2259459)."""
        if not self._username:
            return None
        return self._username.split("-", 1)[0].strip() or None

    @property
    def program_code(self) -> str | None:
        """Program code derived from the login (e.g. 3743)."""
        if not self._username or "-" not in self._username:
            return None
        return self._username.split("-", 1)[1].strip() or None

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        async with self._request_lock:
            try:
                return await self._http.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                raise SiraError(f"Timeout hablando con SIRA: {exc}") from exc
            except httpx.HTTPError as exc:
                raise SiraError(f"Error de red hablando con SIRA: {exc}") from exc

    @staticmethod
    def _html(response: httpx.Response) -> str:
        # Every SIRA page is ISO-8859-1; decode explicitly so we never guess.
        return response.content.decode("iso-8859-1", errors="replace")

    async def _cached(self, key: str, refresh: bool, factory: Callable[[], Any]) -> Any:
        if not refresh:
            hit = self._cache.get(key)
            if hit is not None:
                return hit
        value = await factory()
        self._cache.set(key, value)
        return value

    # -- auth ---------------------------------------------------------------

    async def login(self, username: str | None = None, password: str | None = None) -> None:
        username = (username or self._username or "").strip()
        password = password or self._password or ""
        if not username or not password:
            raise SiraAuthError(
                "No hay credenciales configuradas. Define SIRA_USERNAME/SIRA_PASSWORD "
                "o haz POST /session/login con {username, password}."
            )
        async with self._login_lock:
            await self._request("GET", "/")  # seed a fresh PHPSESSID
            response = await self._request(
                "POST",
                "/",
                data={
                    "usu_login_aut": username,
                    "usu_password_aut": password,
                    "redirect": "",
                    "boton": "Ingresar al Sistema",
                },
                follow_redirects=False,
            )
            if response.status_code not in (301, 302, 303, 307, 308):
                html = self._html(response)
                alert = ""
                m = parsers._AVISO.search(html)
                if m:
                    alert = parsers._clean(m.group(2)) or ""
                self._logged_in = False
                raise SiraAuthError(f"Login rechazado por SIRA. {alert}".strip())
            self._username = username
            self._password = password
            self._logged_in = True
            self._cache.clear()
            logger.info("Sesión SIRA iniciada como %s", username)

    async def logout(self) -> None:
        if self._logged_in:
            try:
                await self._request("GET", LOGOUT_URL)
            finally:
                self._logged_in = False
                self._cache.clear()
                logger.info("Sesión SIRA finalizada")

    async def ensure_login(self, force: bool = False) -> None:
        if self._logged_in and not force:
            return
        if not (self._username or self.settings.username):
            raise SiraAuthError(
                "No autenticado. Configura SIRA_USERNAME/SIRA_PASSWORD o llama POST /session/login."
            )
        await self.login()

    def update_credentials(self, username: str | None = None, password: str | None = None) -> None:
        if username:
            self._username = username.strip()
        if password:
            self._password = password

    # -- low level fetch ----------------------------------------------------

    async def _fetch_page(self, method: str, url: str, data: dict[str, Any] | None = None) -> str:
        await self.ensure_login()
        for attempt in (1, 2):
            response = await self._request(method, url, data=data)
            html = self._html(response)

            if parsers.session_expired(html):
                self._logged_in = False
                self._cache.clear()
                if attempt == 1:
                    logger.info("Sesión SIRA caída; reautenticando…")
                    await self.ensure_login(force=True)
                    continue
                raise SiraSessionExpired("SIRA cerró la sesión repetidamente.")

            if parsers.is_login_page(html):
                self._logged_in = False
                if attempt == 1:
                    logger.info("SIRA pidió login de nuevo; reautenticando…")
                    await self.ensure_login(force=True)
                    continue
                raise SiraSessionExpired("SIRA sigue pidiendo credenciales.")

            error = parsers.sira_error_message(html)
            if error:
                self._logged_in = False  # SIRA kills the session on app errors
                raise SiraOperationError(f"SIRA respondió con error: {error}")

            return html
        raise SiraSessionExpired("No fue posible reutilizar la sesión.")  # pragma: no cover

    # -- read-only data -----------------------------------------------------

    async def get_home(self, refresh: bool = False) -> str:
        return await self._cached("home", refresh, lambda: self._fetch_page("GET", HOME_URL))

    async def get_header(self, refresh: bool = False) -> PersonHeader:
        async def factory() -> PersonHeader:
            return parsers.parse_header(await self.get_home(refresh=refresh))

        return await self._cached("header", refresh, factory)

    async def get_historial(self, refresh: bool = False) -> parsers.HistorialPage:
        async def factory() -> parsers.HistorialPage:
            code = self.student_code
            if not code:
                raise SiraAuthError("No se pudo derivar el código de estudiante del usuario.")
            html = await self._fetch_page(
                "POST",
                ACADEMICA_URL,
                {"accion": "Consultar Historial", "codigo_estudiante": code, "modulo": "Academica"},
            )
            return parsers.parse_historial(html)

        return await self._cached("historial", refresh, factory)

    def _choose_carpeta(self, page: parsers.HistorialPage) -> str | None:
        profile = page.profile
        program = profile.programa
        resolution = parsers.extract_resolution_code(profile.resolucion)
        if program:
            exact = f"{program.codigo}|{program.sede}|{program.jornada}|{resolution}"
            for carpeta in profile.carpetas:
                if carpeta.detalle == exact:
                    return carpeta.detalle
            prefix = f"{program.codigo}|{program.sede}|{program.jornada}|"
            for carpeta in profile.carpetas:
                if carpeta.detalle.startswith(prefix):
                    return carpeta.detalle
        return profile.carpetas[0].detalle if profile.carpetas else None

    async def get_historia_detalle(
        self, carpeta: str | None = None, refresh: bool = False
    ) -> parsers.HistoriaDetallePage:
        async def factory() -> parsers.HistoriaDetallePage:
            historial = await self.get_historial(refresh=refresh)
            detalle = carpeta or self._choose_carpeta(historial)
            if not detalle:
                raise SiraOperationError("El estudiante no tiene carpetas académicas disponibles.")
            data = {
                **historial.hia_fields,
                "Ventana": "",
                "versionImprimible": "",
                "modulo": "Academica",
                "accion": "Consultar Estudiante",
                "DetalleCarpeta": detalle,
            }
            html = await self._fetch_page("POST", ACADEMICA_URL, data)
            return parsers.parse_historia_detalle(html)

        return await self._cached(f"historia_detalle:{carpeta or 'default'}", refresh, factory)

    async def _carpeta_html(
        self, detalle: str = "COMPLETA", carpeta: str | None = None, refresh: bool = False
    ) -> str:
        async def factory() -> str:
            historial = await self.get_historial(refresh=refresh)
            data = {
                **historial.hia_fields,
                "Ventana": "",
                "versionImprimible": "",
                "modulo": "Academica",
                "accion": "Generar Carpeta",
                "TipoCarpeta": "COMPLETA",
                "DetalleCarpeta": detalle,
            }
            return await self._fetch_page("POST", ACADEMICA_URL, data)

        return await self._cached(f"carpeta_html:{carpeta or 'default'}:{detalle}", refresh, factory)

    async def get_carpeta(
        self, detalle: str = "COMPLETA", carpeta: str | None = None, refresh: bool = False
    ) -> tuple[list[PeriodResult], float | None]:
        """Full (or single-period) academic record."""
        async def factory() -> tuple[list[PeriodResult], float | None]:
            detail_page = await self.get_historia_detalle(carpeta=carpeta, refresh=refresh)
            html = await self._carpeta_html(detalle, carpeta=carpeta, refresh=refresh)
            return parsers.parse_carpeta(html, detail_page.periodos)

        return await self._cached(f"carpeta:{carpeta or 'default'}:{detalle}", refresh, factory)

    async def get_grades(
        self, refresh: bool = False, carpeta: str | None = None
    ) -> tuple[StudentProfile, float | None, list[PeriodResult]]:
        historial = await self.get_historial(refresh=refresh)
        periods, average = await self.get_carpeta("COMPLETA", carpeta=carpeta, refresh=refresh)
        return historial.profile, average, periods

    async def get_period_options(self, carpeta: str | None = None, refresh: bool = False) -> list[PeriodOption]:
        detail_page = await self.get_historia_detalle(carpeta=carpeta, refresh=refresh)
        return detail_page.periodos

    async def get_period(self, code: str, refresh: bool = False) -> PeriodResult | None:
        """Fetch a single period (by its SIRA code, e.g. 202408041)."""
        import re as _re

        if not _re.match(r"^\d{5,12}$", code):
            return None
        options = await self.get_period_options(refresh=refresh)
        option = next((p for p in options if p.codigo == code), None)
        if option is None:
            return None
        raw = f"{option.codigo}|{option.fecha or ''}||"
        periods, _ = await self.get_carpeta(raw, refresh=refresh)
        return periods[0] if periods else None

    async def get_tabulado(self, refresh: bool = False) -> Enrollment:
        async def factory() -> Enrollment:
            code = self.student_code
            program = self.program_code
            if not code or not program:
                raise SiraAuthError("No se pudo derivar código de estudiante / programa del usuario.")
            html = await self._fetch_page(
                "POST",
                TABULADO_URL,
                {"accion": "Generar Tabulado", "est_codigo": code, "pra_codigo": program},
            )
            return parsers.parse_tabulado(html)

        return await self._cached("tabulado", refresh, factory)

    async def get_contacto(self, refresh: bool = False) -> ContactInfo:
        async def factory() -> ContactInfo:
            html = await self._fetch_page(
                "POST", CONTACTO_URL, {"accion": "desplegarFmInformacionDeContacto"}
            )
            return parsers.parse_contacto(html)

        return await self._cached("contacto", refresh, factory)

    async def get_resolucion(self, refresh: bool = False) -> list[PrerequisiteItem]:
        async def factory() -> list[PrerequisiteItem]:
            historial = await self.get_historial(refresh=refresh)
            profile = historial.profile
            full_code = profile.codigo_estudiante or self.student_code
            program = (profile.programa.codigo if profile.programa else None) or self.program_code
            resolution = parsers.extract_resolution_code(profile.resolucion)
            data: dict[str, Any] = {
                "accion": "ListadoPrerrequisitos",
                "est_codigo": full_code,
                "pra_codigo": program,
            }
            if resolution:
                data["rep_codigo"] = resolution
            html = await self._fetch_page("POST", RESOLUCION_URL, data)
            return parsers.parse_resolucion(html)

        return await self._cached("resolucion", refresh, factory)

    async def get_equivalencias(self, refresh: bool = False) -> Equivalences:
        async def factory() -> Equivalences:
            # Preferred source: the EQUIVALENCIAS block at the end of the academic record.
            html = await self._carpeta_html("COMPLETA", refresh=refresh)
            entries = parsers.parse_equivalences_from_carpeta(html)
            if entries:
                return Equivalences(has_process=True, entries=entries)

            # Fallback: the standalone equivalence-process query.
            historial = await self.get_historial(refresh=refresh)
            profile = historial.profile
            program = profile.programa
            if not program or not program.sede or not program.jornada:
                return Equivalences(has_process=False, entries=[])
            resolution = parsers.extract_resolution_code(profile.resolucion)
            full_code = profile.codigo_estudiante or self.student_code
            data = {
                "accion": "Consultar Equivalencias",
                "equ_acepta_equiv_pra_codigo": program.codigo,
                "equ_acepta_equiv_sed_codigo": program.sede,
                "equ_acepta_equiv_jor_codigo": program.jornada,
                "equ_acepta_equiv_rep_codigo": resolution,
                "datos_estudiante": (
                    f"{full_code} -> {profile.nombre}, "
                    f"Prog. {program.codigo}-{program.sede}-{program.jornada}"
                ),
            }
            page = await self._fetch_page("POST", EQUIVALENCIAS_URL, data)
            return parsers.parse_equivalencias(page)

        return await self._cached("equivalencias", refresh, factory)
