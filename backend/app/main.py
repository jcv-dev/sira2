"""FastAPI application exposing SIRA data as clean JSON (read-only)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import __version__, parsers
from .client import SiraAuthError, SiraClient, SiraError, SiraOperationError, SiraSessionExpired
from .config import Settings, get_settings
from .models import (
    ContactInfo,
    Enrollment,
    Equivalences,
    Grades,
    PeriodOption,
    PeriodResult,
    PrerequisiteItem,
    ProgramDetail,
    SessionInfo,
    StudentProfile,
)

logger = logging.getLogger("sira.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.sira = SiraClient(settings)
    logger.info("SIRA API lista. base_url=%s", settings.base_url)
    try:
        yield
    finally:
        await app.state.sira.close()


app = FastAPI(
    title="SIRA API",
    version=__version__,
    description=(
        "Read-only JSON API on top of SIRA (Universidad del Valle academic registry). "
        "It logs in with your own credentials, scrapes only read pages and never submits "
        "any modification. All data is cached briefly to avoid hammering the production server."
    ),
    lifespan=lifespan,
)

# The React frontend proxies through Vite in dev; this covers direct access too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

bearer = HTTPBearer(auto_error=False)


async def require_token(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
    settings: Settings = Depends(get_settings),
) -> None:
    """Optional bearer-token protection (only enforced when SIRA_API_TOKEN is set)."""
    if not settings.api_token:
        return
    if credentials is None or credentials.credentials != settings.api_token:
        raise HTTPException(status_code=401, detail="Token inválido o ausente.")


def get_client(request: Request) -> SiraClient:
    return request.app.state.sira


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


@app.exception_handler(SiraAuthError)
async def _auth_error(_: Request, exc: SiraAuthError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(SiraSessionExpired)
async def _session_error(_: Request, exc: SiraSessionExpired) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(SiraOperationError)
async def _operation_error(_: Request, exc: SiraOperationError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(SiraError)
async def _sira_error(_: Request, exc: SiraError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "name": "SIRA API",
        "version": __version__,
        "docs": "/docs",
        "endpoints": [
            "GET  /session",
            "POST /session/login",
            "POST /session/logout",
            "GET  /me",
            "GET  /me/contact",
            "GET  /program",
            "GET  /grades",
            "GET  /grades/periods",
            "GET  /grades/periods/{codigo}",
            "GET  /enrollment",
            "GET  /equivalences",
        ],
        "note": "Solo lectura. La API nunca envía acciones que modifiquen datos en SIRA.",
    }


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str | None = None
    password: str | None = None


@app.get("/session", response_model=SessionInfo, tags=["session"])
async def session_status(client: SiraClient = Depends(get_client)) -> SessionInfo:
    """Current session state. Does not trigger a login by itself."""
    if not client.is_logged_in:
        return SessionInfo(
            authenticated=False,
            username=client.username,
            credentials_configured=client.credentials_configured,
            message=(
                "Sin sesión activa. Se iniciará automáticamente en la primera consulta."
                if client.credentials_configured
                else "Sin credenciales. Configura SIRA_USERNAME/SIRA_PASSWORD o usa POST /session/login."
            ),
        )
    header = await client.get_header(refresh=False)
    return SessionInfo(
        authenticated=True,
        username=client.username,
        student_name=header.full_name,
        credentials_configured=client.credentials_configured,
    )


@app.post(
    "/session/login",
    response_model=SessionInfo,
    tags=["session"],
    dependencies=[Depends(require_token)],
)
async def session_login(
    payload: LoginRequest | None = Body(default=None),
    client: SiraClient = Depends(get_client),
) -> SessionInfo:
    """Explicitly log in (optionally overriding the configured credentials)."""
    if payload:
        client.update_credentials(payload.username, payload.password)
    await client.login()
    header = await client.get_header(refresh=True)
    return SessionInfo(
        authenticated=True,
        username=client.username,
        student_name=header.full_name,
        credentials_configured=client.credentials_configured,
    )


@app.post(
    "/session/logout",
    response_model=SessionInfo,
    tags=["session"],
    dependencies=[Depends(require_token)],
)
async def session_logout(client: SiraClient = Depends(get_client)) -> SessionInfo:
    await client.logout()
    return SessionInfo(authenticated=False, credentials_configured=client.credentials_configured)


# ---------------------------------------------------------------------------
# Student data (read-only)
# ---------------------------------------------------------------------------

RefreshQuery = Query(False, description="Ignorar la caché y volver a consultar SIRA (usar con moderación).")
CarpetaQuery = Query(
    None,
    description='Carpeta académica a usar, p.ej. "3743|00|DIU|698". Por defecto la del programa actual.',
)


@app.get(
    "/me",
    response_model=StudentProfile,
    tags=["student"],
    dependencies=[Depends(require_token)],
)
async def get_me(
    refresh: bool = RefreshQuery,
    client: SiraClient = Depends(get_client),
) -> StudentProfile:
    """Student identity, program and available academic folders."""
    historial = await client.get_historial(refresh=refresh)
    return historial.profile


@app.get(
    "/me/contact",
    response_model=ContactInfo,
    tags=["student"],
    dependencies=[Depends(require_token)],
)
async def get_contact(
    refresh: bool = RefreshQuery,
    client: SiraClient = Depends(get_client),
) -> ContactInfo:
    """Contact / personal information registered in SIRA."""
    return await client.get_contacto(refresh=refresh)


@app.get(
    "/program",
    response_model=ProgramDetail,
    tags=["student"],
    dependencies=[Depends(require_token)],
)
async def get_program(
    refresh: bool = RefreshQuery,
    carpeta: str | None = CarpetaQuery,
    client: SiraClient = Depends(get_client),
) -> ProgramDetail:
    """Program, resolution, academic periods and the prerequisite list."""
    historial = await client.get_historial(refresh=refresh)
    periods = await client.get_period_options(carpeta=carpeta, refresh=refresh)
    prereqs: list[PrerequisiteItem] = await client.get_resolucion(refresh=refresh)
    return ProgramDetail(
        programa=historial.profile.programa,
        resolucion=historial.profile.resolucion,
        periodos=periods,
        prerequisitos=prereqs,
    )


@app.get(
    "/grades",
    response_model=Grades,
    tags=["academics"],
    dependencies=[Depends(require_token)],
)
async def get_grades(
    refresh: bool = RefreshQuery,
    carpeta: str | None = CarpetaQuery,
    client: SiraClient = Depends(get_client),
) -> Grades:
    """Full academic record: every period with courses, grades and averages."""
    profile, average, periods = await client.get_grades(refresh=refresh, carpeta=carpeta)
    return Grades(estudiante=profile, promedio_total=average, periodos=periods)


@app.get(
    "/grades/periods",
    response_model=list[PeriodResult],
    tags=["academics"],
    dependencies=[Depends(require_token)],
)
async def get_grades_periods(
    refresh: bool = RefreshQuery,
    carpeta: str | None = CarpetaQuery,
    client: SiraClient = Depends(get_client),
) -> list[PeriodResult]:
    """Index of academic periods (course list omitted)."""
    _, _, periods = await client.get_grades(refresh=refresh, carpeta=carpeta)
    return [p.model_copy(update={"cursos": []}) for p in periods]


@app.get(
    "/grades/periods/{codigo}",
    response_model=PeriodResult,
    tags=["academics"],
    dependencies=[Depends(require_token)],
)
async def get_grades_period(
    codigo: str,
    refresh: bool = RefreshQuery,
    client: SiraClient = Depends(get_client),
) -> PeriodResult:
    """One academic period by its SIRA code (e.g. 202408041)."""
    period = await client.get_period(codigo, refresh=refresh)
    if period is None:
        raise HTTPException(status_code=404, detail=f"Periodo '{codigo}' no encontrado.")
    return period


@app.get(
    "/enrollment",
    response_model=Enrollment,
    tags=["academics"],
    dependencies=[Depends(require_token)],
)
async def get_enrollment(
    refresh: bool = RefreshQuery,
    client: SiraClient = Depends(get_client),
) -> Enrollment:
    """Current enrollment report ("tabulado")."""
    return await client.get_tabulado(refresh=refresh)


@app.get(
    "/equivalences",
    response_model=Equivalences,
    tags=["academics"],
    dependencies=[Depends(require_token)],
)
async def get_equivalences(
    refresh: bool = RefreshQuery,
    client: SiraClient = Depends(get_client),
) -> Equivalences:
    """Equivalence processes registered for the student."""
    return await client.get_equivalencias(refresh=refresh)


# Small compatibility helper used by tests / debugging.
__all__ = ["app", "parsers"]
