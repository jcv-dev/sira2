"""Pure HTML -> model parsers for the legacy SIRA pages.

Every function here takes a decoded HTML string and returns plain pydantic
models / dataclasses. No network access, so they are easy to unit test with
saved fixtures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from .models import (
    CarpetaRef,
    ContactInfo,
    Course,
    Enrollment,
    Equivalences,
    PeriodOption,
    PeriodResult,
    PersonHeader,
    PrerequisiteItem,
    ProgramRef,
    StudentProfile,
)

_WS = re.compile(r"\s+")
_COURSE_CODE = re.compile(r"^\d[\w\-]{2,9}$")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_FLOAT = re.compile(r"^-?\d+(?:[.,]\d+)?$")
_AVISO = re.compile(r"AVISO\s*(\d+)\s*[:,]?\s*(.{0,200})", re.S)

SESSION_LOST_MARKER = "la sesión ha sido detenida"
LOGIN_FORM_MARKER = 'name="usu_login_aut"'
SIRA_ERROR_MARKER = "Lo sentimos, ha ocurrido un error"
EQUIV_NONE_MARKER = "NO tiene ningún proceso de Equivalencias"


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def text_of(el: Tag | None) -> str:
    if el is None:
        return ""
    return _WS.sub(" ", el.get_text(" ", strip=True)).strip()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = _WS.sub(" ", value).strip()
    return value or None


def _labeled_values(
    text: str, labels: list[str], stops: list[str] | None = None
) -> dict[str, str | None]:
    """Extract `Label: value` pairs, where value runs until the next label.

    `stops` optionally truncates each value at the first occurrence of any
    marker (used to drop trailing form markup that bleeds into the text).
    """
    normalized = _WS.sub(" ", text)
    patterns = [(label, re.compile(r"\s*".join(map(re.escape, label.split())))) for label in labels]
    hits: list[tuple[int, int, str]] = []
    for label, pattern in patterns:
        m = pattern.search(normalized)
        if m:
            hits.append((m.start(), m.end(), label))
    hits.sort()
    result: dict[str, str | None] = {label: None for label in labels}
    for i, (_, end, label) in enumerate(hits):
        next_start = hits[i + 1][0] if i + 1 < len(hits) else len(normalized)
        chunk = normalized[end:next_start]
        if stops:
            cuts = [chunk.find(s) for s in stops]
            cuts = [c for c in cuts if c != -1]
            if cuts:
                chunk = chunk[: min(cuts)]
        result[label] = _clean(chunk)
    return result


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if _FLOAT.match(value.replace(",", ".")):
        return float(value.replace(",", "."))
    return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    m = re.search(r"\d+", value)
    return int(m.group(0)) if m else None


def _selected_option(soup: BeautifulSoup, name: str) -> tuple[str | None, str | None]:
    """Return (value, text) of the last selected option with a non-empty value."""
    select = soup.find("select", attrs={"name": name})
    if not select:
        return None, None
    chosen = None
    for option in select.find_all("option"):
        if option.has_attr("selected") and (option.get("value") or "").strip():
            chosen = option
    if chosen is None:  # fall back to first non-empty option
        for option in select.find_all("option"):
            if (option.get("value") or "").strip():
                chosen = option
                break
    if chosen is None:
        return None, None
    return _clean(chosen.get("value")), _clean(text_of(chosen))


# ---------------------------------------------------------------------------
# Error / session markers
# ---------------------------------------------------------------------------


def is_login_page(html: str) -> bool:
    return LOGIN_FORM_MARKER in html


def session_expired(html: str) -> bool:
    return SESSION_LOST_MARKER in html


def sira_error_message(html: str) -> str | None:
    """Return the SIRA error text if the page carries an error alert."""
    if SIRA_ERROR_MARKER in html:
        m = _AVISO.search(html)
        if m:
            return f"AVISO {m.group(1)}: {_clean(re.sub(r"<[^>]+>", " ", m.group(2))) or SIRA_ERROR_MARKER}"
        return SIRA_ERROR_MARKER
    return None


# ---------------------------------------------------------------------------
# Shared blocks
# ---------------------------------------------------------------------------


def parse_header(html: str) -> PersonHeader:
    """Extract the user box shown in the header of authenticated pages."""
    soup = make_soup(html)
    username = None
    span = soup.find("span", title=re.compile(r"Usuario:"))
    if span:
        m = re.search(r"Usuario:\s*([^>]+?)\s*>>>", span.get("title", ""))
        if m:
            username = m.group(1).strip()

    full_name = institutional = alternate = None
    box = soup.find(id="infoPersonaHeader")
    if box:
        pairs: list[str] = [text_of(s) for s in box.find_all("span")]
        pairs = [p for p in pairs if p]
        for i in range(0, len(pairs) - 1, 2):
            label, value = pairs[i].lower(), pairs[i + 1]
            if "nombres usuario" in label:
                full_name = value
            elif "institucional" in label:
                institutional = value
            elif "alterno" in label:
                alternate = value
    return PersonHeader(
        username=username,
        full_name=full_name,
        institutional_email=institutional,
        alternate_email=alternate,
    )


def _parse_program_ref(raw: str | None) -> ProgramRef | None:
    """'3743-00-DIU-INGENIERÍA DE SISTEMAS' -> ProgramRef"""
    if not raw:
        return None
    parts = raw.split("-", 3)
    if len(parts) < 4:
        return ProgramRef(codigo=parts[0].strip(), nombre=raw.strip(), display=raw.strip())
    return ProgramRef(
        codigo=parts[0].strip(),
        sede=parts[1].strip() or None,
        jornada=parts[2].strip() or None,
        nombre=parts[3].strip(),
        display=raw.strip(),
    )


@dataclass
class HistorialPage:
    profile: StudentProfile
    hia_fields: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Page parsers
# ---------------------------------------------------------------------------


def parse_historial(html: str) -> HistorialPage:
    """`accion=Consultar Historial`: student header + list of academic folders."""
    soup = make_soup(html)

    td = None
    for candidate in soup.find_all("td"):
        if "Estudiante :" in text_of(candidate) and "Documento:" in text_of(candidate):
            td = candidate
            break
    values: dict[str, str | None] = {}
    if td is not None:
        values = _labeled_values(
            text_of(td),
            [
                "Estudiante :",
                "Documento:",
                "Programa Académico :",
                "Email Institucional:",
                "Tipo de Ingreso:",
                "Resolución del estudiante:",
                "Tipo de Currículo:",
            ],
            stops=["Seleccione el Historial"],
        )

    codigo = nombre = documento = None
    estudiante = values.get("Estudiante :")
    if estudiante and "--" in estudiante:
        codigo, _, nombre = estudiante.partition("--")
        codigo, nombre = codigo.strip(), nombre.strip()

    carpetas: list[CarpetaRef] = []
    for inp in soup.find_all("input", attrs={"name": "DetalleCarpeta"}):
        value = (inp.get("value") or "").strip()
        parent_td = inp.find_parent("td")
        label = text_of(parent_td)
        if value and label:
            carpetas.append(CarpetaRef(detalle=value, label=label))

    hia_fields: dict[str, str] = {}
    for inp in soup.find_all("input"):
        name = inp.get("name") or ""
        if name.startswith("hia_"):
            hia_fields[name] = (inp.get("value") or "").strip()
    # carry the module flag too
    for inp in soup.find_all("input", attrs={"name": "modulo"}):
        hia_fields.setdefault("modulo", (inp.get("value") or "").strip())

    profile = StudentProfile(
        codigo_estudiante=codigo,
        nombre=nombre,
        documento=values.get("Documento:"),
        programa=_parse_program_ref(values.get("Programa Académico :")),
        email_institucional=values.get("Email Institucional:"),
        tipo_ingreso=values.get("Tipo de Ingreso:"),
        resolucion=values.get("Resolución del estudiante:"),
        tipo_curriculo=values.get("Tipo de Currículo:"),
        carpetas=carpetas,
        header=parse_header(html),
    )
    return HistorialPage(profile=profile, hia_fields=hia_fields)


@dataclass
class HistoriaDetallePage:
    tipo_carpetas: list[str] = field(default_factory=list)
    periodos: list[PeriodOption] = field(default_factory=list)
    hia_fields: dict[str, str] = field(default_factory=dict)


def parse_historia_detalle(html: str) -> HistoriaDetallePage:
    """`accion=Consultar Estudiante`: available presentation types and periods."""
    soup = make_soup(html)

    tipo_carpetas: list[str] = []
    for inp in soup.find_all("input", attrs={"name": "TipoCarpeta"}):
        value = (inp.get("value") or "").strip()
        if value and value not in tipo_carpetas:
            tipo_carpetas.append(value)

    periodos: list[PeriodOption] = []
    for inp in soup.find_all("input", attrs={"name": "DetalleCarpeta"}):
        value = (inp.get("value") or "").strip()
        parts = value.split("|")
        if len(parts) >= 2 and parts[0].isdigit():
            label = text_of(inp.find_parent("td"))
            periodos.append(
                PeriodOption(codigo=parts[0], fecha=_clean(parts[1]), label=label or parts[0])
            )

    hia_fields: dict[str, str] = {}
    for inp in soup.find_all("input"):
        name = inp.get("name") or ""
        if name.startswith("hia_"):
            hia_fields[name] = (inp.get("value") or "").strip()

    return HistoriaDetallePage(tipo_carpetas=tipo_carpetas, periodos=periodos, hia_fields=hia_fields)


def _looks_like_course_row(tds: list[Tag]) -> bool:
    if len(tds) < 10:
        return False
    first = text_of(tds[0])
    if not first or first.upper() == "CÓDIGO":
        return False
    if "Total" in first or "Total Asignaturas" in text_of(tds[-1]):
        return False
    return bool(_COURSE_CODE.match(first))


def _is_cancellation(cell_text: str, title: str | None) -> bool:
    blob = f"{cell_text} {title or ''}".upper()
    return "CANCELACI" in blob


def _build_course(
    codigo: str,
    grupo: str | None,
    nombre: str,
    *,
    sede: str | None = None,
    tipologia: str | None = None,
    funcionalidad: str | None = None,
    componente: str | None = None,
    creditos: str | None = None,
    calificacion: str | None = None,
    habilitacion: str | None = None,
    cancel_text: str | None = None,
    cancel_title: str | None = None,
) -> Course:
    nota = _parse_float(calificacion)
    nota_raw = None if nota is not None else _clean(calificacion)
    estado: str | None
    fecha_cancelacion = None

    if _is_cancellation(cancel_text or "", cancel_title):
        estado = "CANCELADA"
        m = _DATE.search(cancel_text or "") or _DATE.search(cancel_title or "")
        fecha_cancelacion = m.group(0) if m else None
    elif nota is not None:
        estado = "APROBADA" if nota >= 3.0 else "REPROBADA"
    elif nota_raw:
        estado = None  # non-numeric grade (e.g. homologation) -> let the caller decide
    else:
        estado = "EN_CURSO"

    return Course(
        codigo=codigo,
        grupo=grupo,
        sede=sede,
        nombre=nombre,
        tipologia=tipologia,
        funcionalidad=funcionalidad,
        componente=componente,
        creditos=_parse_int(creditos),
        nota=nota,
        nota_raw=nota_raw,
        habilitacion=habilitacion,
        estado=estado,
        fecha_cancelacion=fecha_cancelacion,
    )


def _apply_summary_pairs(period: PeriodResult, tds: list[Tag]) -> None:
    for i in range(len(tds) - 1):
        label = text_of(tds[i])
        if not label.endswith(":"):
            continue
        value = text_of(tds[i + 1])
        if not value:
            continue
        plain = label.rstrip(":").strip()
        low = plain.lower()
        if low.startswith("créditos matriculados"):
            period.creditos_matriculados = _parse_int(value)
        elif "aprobados" in low and "acumulados" not in low and not low.startswith("%"):
            period.creditos_aprobados = _parse_int(value)
        elif low.startswith("promedio semestral"):
            period.promedio = _parse_float(value)
        else:
            period.otros[plain] = value


def parse_carpeta(html: str, periods: list[PeriodOption] | None = None) -> tuple[list[PeriodResult], float | None]:
    """`accion=Generar Carpeta`: full academic record.

    Returns (periods, overall average). Also works for single-period pages.
    """
    soup = make_soup(html)
    name_to_code = {p.label: p.codigo for p in (periods or [])}

    results: list[PeriodResult] = []

    for header_td in soup.find_all("td"):
        header_text = text_of(header_td)
        if not (
            header_text.startswith("PERIODO:")
            and len(header_text) < 120
            and header_td.find("table") is None
        ):
            continue
        table = header_td.find_parent("table")
        if table is None:
            continue

        name = header_text.split("PERIODO:", 1)[1].strip()
        current = PeriodResult(
            codigo=name_to_code.get(name) or (name_to_code.get(name.upper()) if name else None),
            nombre=name,
        )
        results.append(current)

        for el in table.find_all(["tr", "td"]):
            if el.find_parent("table") is not table:
                continue  # belongs to a nested table (handled below via its <tr>)
            if el.name == "td":
                tr_ancestor = el.find_parent("tr")
                if tr_ancestor is not None and tr_ancestor.find_parent("table") is table:
                    continue  # covered by its <tr>
                cell_text = text_of(el)
                if "Fecha Matricula:" in cell_text:
                    m = re.search(r"Fecha Matricula:\s*([0-9][0-9\-: ]*)", cell_text)
                    if m:
                        current.fecha_matricula = _clean(m.group(1))
                continue

            # el is a <tr> belonging to this period table
            tds = el.find_all("td", recursive=False)
            if not tds:
                continue
            row_text = text_of(el)
            if not row_text or row_text.strip().startswith("PERIODO:"):
                continue

            if el.find("table") is not None:
                # the "Resumen de Finalización por periodo" box is a nested table
                if "Matriculados" in row_text or "Promedio Semestral" in row_text:
                    for nested_row in el.find_all("tr"):
                        _apply_summary_pairs(
                            current, nested_row.find_all("td", recursive=False)
                        )
                continue

            if "Fecha Matricula:" in row_text:
                m = re.search(r"Fecha Matricula:\s*([0-9][0-9\-: ]*)", row_text)
                if m:
                    current.fecha_matricula = _clean(m.group(1))
                continue

            if _looks_like_course_row(tds):
                cells = [text_of(td) for td in tds]
                titles = [td.get("title") for td in tds]

                codigo = cells[0]
                grupo = cells[1] if len(cells) > 1 else None
                sede = cells[2] if len(cells) > 2 else None
                nombre = cells[3] if len(cells) > 3 else ""
                tipologia = cells[4] if len(cells) > 4 else None
                funcionalidad = cells[5] if len(cells) > 5 else None
                componente = cells[6] if len(cells) > 6 else None
                creditos = cells[7] if len(cells) > 7 else None
                calificacion = cells[8] if len(cells) > 8 else None
                habilitacion = cells[9] if len(cells) > 9 else None
                cancel_text = cells[10] if len(cells) > 10 else None
                cancel_title = titles[10] if len(titles) > 10 else (titles[0] if titles else None)
                current.cursos.append(
                    _build_course(
                        codigo,
                        _clean(grupo),
                        nombre or codigo,
                        sede=_clean(sede),
                        tipologia=_clean(tipologia),
                        funcionalidad=_clean(funcionalidad),
                        componente=_clean(componente),
                        creditos=creditos,
                        calificacion=calificacion,
                        habilitacion=_clean(habilitacion),
                        cancel_text=cancel_text,
                        cancel_title=cancel_title,
                    )
                )
                continue

            # summary row: label/value pairs
            _apply_summary_pairs(current, tds)

    promedio_total = None
    for td in soup.find_all("td"):
        if "Promedio Total Acumulado" in text_of(td):
            m = re.search(r"([\d]+[.,][\d]+)", text_of(td))
            promedio_total = _parse_float(m.group(1)) if m else None
            break

    return results, promedio_total


def parse_tabulado(html: str) -> Enrollment:
    """`accion=Generar Tabulado`: current enrollment report."""
    soup = make_soup(html)
    full_text = text_of(soup)
    values = _labeled_values(
        full_text,
        [
            "Nombre:",
            "Código:",
            "Documento:",
            "Resolución:",
            "Programa:",
            "Sede:",
            "Jornada:",
            "Periodo Académico:",
            "Categoría Estudiante:",
            "Fecha de Matrícula:",
        ],
        stops=["Listado de Prerrequisitos", "Listado de Asignaturas", "VERIFIQUE"],
    )
    # The labels above bleed into following text; trim the obvious tails.
    periodo = values.get("Periodo Académico:")
    if periodo:
        periodo = periodo.split("Categoría")[0].strip()

    cursos: list[Course] = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if not _looks_like_course_row(tds):
            continue
        cells = [text_of(td) for td in tds]
        titles = [td.get("title") for td in tds]
        cursos.append(
            _build_course(
                cells[0],
                _clean(cells[1] if len(cells) > 1 else None),
                cells[3] if len(cells) > 3 else cells[0],
                sede=_clean(cells[2] if len(cells) > 2 else None),
                tipologia=_clean(cells[5] if len(cells) > 5 else None),
                funcionalidad=_clean(cells[6] if len(cells) > 6 else None),
                creditos=cells[7] if len(cells) > 7 else None,
                calificacion=cells[8] if len(cells) > 8 else None,
                habilitacion=_clean(cells[9] if len(cells) > 9 else None),
                cancel_text=cells[10] if len(cells) > 10 else None,
                cancel_title=titles[10] if len(titles) > 10 else None,
            )
        )

    totals = _labeled_values(
        full_text,
        [
            "Total Asignaturas Matriculadas:",
            "Total Asignaturas Canceladas:",
            "Total Créditos Matriculados:",
        ],
    )

    return Enrollment(
        nombre=values.get("Nombre:"),
        codigo=values.get("Código:"),
        documento=values.get("Documento:"),
        resolucion=values.get("Resolución:"),
        programa=values.get("Programa:"),
        sede=values.get("Sede:"),
        jornada=values.get("Jornada:"),
        periodo=periodo,
        categoria=values.get("Categoría Estudiante:"),
        fecha_matricula=values.get("Fecha de Matrícula:"),
        cursos=cursos,
        total_asignaturas_matriculadas=_parse_int(totals.get("Total Asignaturas Matriculadas:")),
        total_asignaturas_canceladas=_parse_int(totals.get("Total Asignaturas Canceladas:")),
        total_creditos_matriculados=_parse_int(totals.get("Total Créditos Matriculados:")),
    )


def parse_contacto(html: str) -> ContactInfo:
    """`desplegarFmInformacionDeContacto`: personal/contact form values."""
    soup = make_soup(html)

    inputs: dict[str, str] = {}
    for inp in soup.find_all("input"):
        name = inp.get("name") or ""
        if not name:
            continue
        value = (inp.get("value") or "").strip()
        if value and name not in inputs:
            inputs[name] = value

    def combo(label_code: str) -> str | None:
        """Extract the display part of a 'code -> NAME' companion input."""
        raw = inputs.get(f"wincombo{label_code}")
        if not raw:
            return None
        if "->" in raw:
            return _clean(raw.split("->", 1)[1])
        return _clean(raw)

    tipo_doc_value, tipo_doc_text = _selected_option(soup, "per_doc_ide_tid_codigo")
    _, sexo_text = _selected_option(soup, "per_sex_codigo")
    _, ecv_text = _selected_option(soup, "per_ecv_codigo")

    used = {
        "per_codigo",
        "per_nombre",
        "per_apellido",
        "per_doc_ide_numero",
        "per_nacer_fecha",
        "per_reside_direccion",
        "per_reside_telefono",
        "per_telefono_celular",
        "per_telefono_oficina",
        "per_email",
        "per_email_institucional",
        "per_estrato",
    }
    extras = {
        k: v
        for k, v in inputs.items()
        if k.startswith("per_") and k not in used and not k.startswith("wincombo")
    }

    return ContactInfo(
        codigo_persona=_clean(inputs.get("per_codigo")),
        nombre=_clean(inputs.get("per_nombre")),
        apellido=_clean(inputs.get("per_apellido")),
        tipo_documento=tipo_doc_text or tipo_doc_value,
        numero_documento=_clean(inputs.get("per_doc_ide_numero")),
        expedido_en=combo("per_doc_ide_expedido_ciu_codigo"),
        fecha_nacimiento=_clean(inputs.get("per_nacer_fecha")),
        sexo=sexo_text,
        estado_civil=ecv_text,
        estrato=combo("per_estrato") or _clean(inputs.get("per_estrato")),
        direccion=_clean(inputs.get("per_reside_direccion")),
        telefono_residencia=_clean(inputs.get("per_reside_telefono")),
        telefono_celular=_clean(inputs.get("per_telefono_celular")),
        telefono_oficina=_clean(inputs.get("per_telefono_oficina")),
        email_institucional=_clean(inputs.get("per_email_institucional")),
        email_alterno=_clean(inputs.get("per_email")),
        extras=extras,
    )


def parse_resolucion(html: str) -> list[PrerequisiteItem]:
    """`accion=ListadoPrerrequisitos`: program course / prerequisite list."""
    soup = make_soup(html)
    items: list[PrerequisiteItem] = []

    def blankish(value: str) -> str | None:
        value = _clean(value)
        if not value or value in {"&nbsp;", "\xa0"}:
            return None
        return value

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 9:
            continue
        cells = [blankish(text_of(td)) for td in tds]
        if not cells[0] or not cells[0].isdigit():
            continue
        if "Nombre Asignatura" in (cells[3] or ""):
            continue
        items.append(
            PrerequisiteItem(
                numero=_parse_int(cells[0]),
                semestre=cells[1],
                codigo=cells[2],
                asignatura=cells[3],
                tipo_asignatura=cells[4],
                creditos=_parse_int(cells[5]),
                prerequisito_codigo=cells[6],
                prerequisito_nombre=cells[7],
                prerequisito_tipo=cells[8],
            )
        )
    return items


def parse_equivalencias(html: str) -> Equivalences:
    """`accion=Consultar Equivalencias`: best-effort generic table parsing."""
    if EQUIV_NONE_MARKER in html:
        return Equivalences(has_process=False, entries=[])

    soup = make_soup(html)
    entries: list[dict[str, str]] = []
    for table in soup.find_all("table"):
        if table.find("table") is not None:
            continue  # only innermost tables; ancestors repeat the same rows
        rows = table.find_all("tr")
        header: list[str] | None = None
        for tr in rows:
            cells = [text_of(c) for c in tr.find_all(["th", "td"], recursive=False)]
            cells = [c for c in cells if c]
            if not cells:
                continue
            if header is None:
                if len(cells) >= 2:
                    header = cells
                continue
            if len(cells) == len(header) and any(cells):
                entries.append(dict(zip(header, cells)))

    return Equivalences(has_process=bool(entries), entries=entries)


def parse_equivalences_from_carpeta(html: str) -> list[dict[str, str]]:
    """The EQUIVALENCIAS block that appears at the end of the academic record."""
    soup = make_soup(html)
    entries: list[dict[str, str]] = []
    for table in soup.find_all("table"):
        if table.find("table") is not None:
            continue
        header: list[str] | None = None
        for tr in table.find_all("tr"):
            cells = [text_of(c) for c in tr.find_all(["td", "th"], recursive=False)]
            if not cells:
                continue
            if header is None:
                if (
                    len(cells) == 6
                    and cells[0].strip().upper() == "CODIGO"
                    and cells[5].strip().upper() == "CRED"
                ):
                    header = [c.strip().lower() for c in cells]
                continue
            if len(cells) == 6 and any(cells):
                entries.append(dict(zip(header, cells)))
    return entries


def extract_resolution_code(resolucion: str | None) -> str | None:
    """'(698) 047 de 2020' -> '698'"""
    if not resolucion:
        return None
    m = re.search(r"\((\d+)\)", resolucion)
    return m.group(1) if m else None


def short_student_code(code: str | None) -> str | None:
    """'202259459' -> '2259459' (SIRA uses both forms in different forms)."""
    if code and len(code) == 9 and code.startswith("20"):
        return code[2:]
    return code
