"""Pydantic models describing the (read-only) data exposed by the SIRA API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SessionInfo(BaseModel):
    authenticated: bool
    username: str | None = Field(default=None, description="Login used against SIRA")
    student_name: str | None = None
    credentials_configured: bool = False
    message: str | None = None


class PersonHeader(BaseModel):
    """Data shown in the header of any page once logged in."""

    username: str | None = Field(default=None, description="e.g. 202259459-3743")
    full_name: str | None = None
    institutional_email: str | None = None
    alternate_email: str | None = None


class ProgramRef(BaseModel):
    codigo: str
    sede: str | None = None
    jornada: str | None = None
    nombre: str
    display: str


class CarpetaRef(BaseModel):
    """An academic folder (curriculum version) available for the student."""

    detalle: str = Field(description='Raw form value, e.g. "3743|00|DIU|698"')
    label: str = Field(description='Human label, e.g. "3743-00-DIU-INGENIERÍA DE SISTEMAS"')


class StudentProfile(BaseModel):
    """Basic student / program info (mirrors the header of the grade report)."""

    codigo_estudiante: str | None = None
    nombre: str | None = None
    documento: str | None = None
    programa: ProgramRef | None = None
    email_institucional: str | None = None
    tipo_ingreso: str | None = None
    resolucion: str | None = None
    tipo_curriculo: str | None = None
    carpetas: list[CarpetaRef] = Field(default_factory=list)
    header: PersonHeader | None = None


class Course(BaseModel):
    """A course row as it appears on grade/enrollment reports."""

    codigo: str
    grupo: str | None = None
    nombre: str
    tipologia: str | None = Field(default=None, description="TM column, raw SIRA code")
    funcionalidad: str | None = Field(default=None, description="FUN column, raw SIRA code")
    componente: str | None = Field(default=None, description="COM column, raw SIRA code")
    sede: str | None = None
    creditos: int | None = None
    nota: float | None = None
    nota_raw: str | None = Field(default=None, description="Raw grade text when not numeric")
    habilitacion: str | None = Field(default=None, description="HAB column, raw SIRA code")
    estado: str | None = Field(
        default=None,
        description="APROBADA | REPROBADA | EN_CURSO | CANCELADA | HOMOLOGADA (best effort, derived)",
    )
    fecha_cancelacion: str | None = None


class PeriodResult(BaseModel):
    """One academic period inside the grade report."""

    codigo: str | None = Field(default=None, description="e.g. 202408041 (when known)")
    nombre: str = Field(description='e.g. "AGOSTO/2024 - DICIEMBRE/2024"')
    fecha_matricula: str | None = None
    cursos: list[Course] = Field(default_factory=list)
    creditos_matriculados: int | None = None
    creditos_aprobados: int | None = None
    promedio: float | None = None
    otros: dict[str, str] = Field(default_factory=dict)


class Grades(BaseModel):
    """Full academic record ("carpeta académica")."""

    estudiante: StudentProfile
    promedio_total: float | None = None
    periodos: list[PeriodResult] = Field(default_factory=list)


class PeriodOption(BaseModel):
    codigo: str = Field(description="e.g. 202408041")
    fecha: str | None = Field(default=None, description="e.g. 2024-07-30")
    label: str = Field(description='e.g. "AGOSTO/2024 - DICIEMBRE/2024"')


class Enrollment(BaseModel):
    """Current enrollment report ("tabulado")."""

    nombre: str | None = None
    codigo: str | None = None
    documento: str | None = None
    resolucion: str | None = None
    programa: str | None = None
    sede: str | None = None
    jornada: str | None = None
    periodo: str | None = None
    categoria: str | None = None
    fecha_matricula: str | None = None
    cursos: list[Course] = Field(default_factory=list)
    total_asignaturas_matriculadas: int | None = None
    total_asignaturas_canceladas: int | None = None
    total_creditos_matriculados: int | None = None


class ContactInfo(BaseModel):
    """Contact / personal information form values."""

    codigo_persona: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    tipo_documento: str | None = None
    numero_documento: str | None = None
    expedido_en: str | None = None
    fecha_nacimiento: str | None = None
    sexo: str | None = None
    estado_civil: str | None = None
    estrato: str | None = None
    direccion: str | None = None
    telefono_residencia: str | None = None
    telefono_celular: str | None = None
    telefono_oficina: str | None = None
    email_institucional: str | None = None
    email_alterno: str | None = None
    extras: dict[str, str] = Field(default_factory=dict)


class PrerequisiteItem(BaseModel):
    numero: int | None = None
    semestre: str | None = None
    codigo: str | None = None
    asignatura: str | None = None
    tipo_asignatura: str | None = None
    creditos: int | None = None
    prerequisito_codigo: str | None = None
    prerequisito_nombre: str | None = None
    prerequisito_tipo: str | None = None


class ProgramDetail(BaseModel):
    """Program info + prerequisite list for the student's resolution."""

    programa: ProgramRef | None = None
    resolucion: str | None = None
    periodos: list[PeriodOption] = Field(default_factory=list)
    prerequisitos: list[PrerequisiteItem] = Field(default_factory=list)


class Equivalences(BaseModel):
    has_process: bool
    entries: list[dict[str, str]] = Field(default_factory=list)
