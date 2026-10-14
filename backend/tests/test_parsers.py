"""Offline parser tests using sanitized fixtures of real SIRA pages."""

from pathlib import Path

from app import parsers

FIXTURES = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# header / detection
# ---------------------------------------------------------------------------


def test_parse_header_from_home():
    header = parsers.parse_header(read("home.html"))
    assert header.username == "202399999-3743"
    assert header.full_name == "GOMEZ PEREZ ANA MARIA"
    assert header.institutional_email == "ana.gomez.perez@correounivalle.edu.co"
    assert header.alternate_email == "ana.gomez@example.com"


def test_login_page_detection():
    assert parsers.is_login_page(read("login_page.html"))
    assert not parsers.is_login_page(read("home.html"))


def test_short_student_code():
    assert parsers.short_student_code("202259459") == "2259459"
    assert parsers.short_student_code("12345") == "12345"
    assert parsers.short_student_code(None) is None


def test_extract_resolution_code():
    assert parsers.extract_resolution_code("(698) 047 de 2020") == "698"
    assert parsers.extract_resolution_code(None) is None


# ---------------------------------------------------------------------------
# historial (student profile + folders)
# ---------------------------------------------------------------------------


def test_parse_historial():
    page = parsers.parse_historial(read("historial.html"))
    profile = page.profile

    assert profile.codigo_estudiante == "202399999"
    assert profile.nombre == "GOMEZ PEREZ ANA MARIA"
    assert profile.documento == "C.C. 99999999"
    assert profile.programa is not None
    assert profile.programa.codigo == "3743"
    assert profile.programa.sede == "00"
    assert profile.programa.jornada == "DIU"
    assert "INGENIERÍA DE SISTEMAS" in profile.programa.nombre
    assert profile.email_institucional == "ana.gomez.perez@correounivalle.edu.co"
    assert profile.tipo_ingreso == "TRASLADO"
    assert profile.resolucion == "(698) 047 de 2020"
    # must not bleed into the form markup that follows
    assert profile.tipo_curriculo == "RF -> REFORMA CURRICULAR"

    assert [c.detalle for c in profile.carpetas] == ["3743|06|DIU|698", "3743|00|DIU|698"]
    assert page.hia_fields["hia_pra_codigo"] == "3743"
    assert page.hia_fields["hia_rep_codigo"] == "698"


def test_parse_historia_detalle():
    page = parsers.parse_historia_detalle(read("historia_detalle.html"))
    assert page.tipo_carpetas == ["BASICA", "COMPLETA"]
    assert len(page.periodos) == 5
    first = page.periodos[0]
    assert first.codigo == "202408041"
    assert first.fecha == "2024-07-30"
    assert first.label == "AGOSTO/2024 - DICIEMBRE/2024"


# ---------------------------------------------------------------------------
# carpeta (full academic record)
# ---------------------------------------------------------------------------


def _carpeta():
    detail = parsers.parse_historia_detalle(read("historia_detalle.html"))
    return parsers.parse_carpeta(read("carpeta.html"), detail.periodos)


def test_parse_carpeta_structure():
    periods, average = _carpeta()
    assert average == 4.41
    assert len(periods) == 5
    first = periods[0]
    assert first.codigo == "202408041"
    assert first.nombre == "AGOSTO/2024 - DICIEMBRE/2024"
    assert first.fecha_matricula == "2024-07-30 00:00:00"
    assert first.creditos_matriculados == 17
    assert first.creditos_aprobados == 17
    assert first.promedio == 4.78
    assert len(first.cursos) == 5


def test_parse_carpeta_course_details():
    periods, _ = _carpeta()
    course = next(c for c in periods[0].cursos if c.codigo == "750018C")
    assert course.nombre == "PROYECTO INTEGRADOR I"
    assert course.grupo == "01"
    assert course.sede == "00"
    assert course.creditos == 4
    assert course.nota == 4.9
    assert course.estado == "APROBADA"
    assert course.componente == "CTE"


def test_parse_carpeta_regressions():
    """Guards against cumulative-vs-period totals and duplicated wrapper periods."""
    periods, _ = _carpeta()
    # period 2 must report 17 period credits, not the 34 cumulative ones
    assert periods[1].creditos_aprobados == 17
    assert periods[1].otros["Num. Créd. Aprobados Acumulados"] == "34"
    # a cancelled course inside period 3
    cancelled = next(c for c in periods[2].cursos if c.codigo == "730078C")
    assert cancelled.estado == "CANCELADA"
    assert cancelled.fecha_cancelacion == "2025-09-10"
    # a still in-progress course in the current period
    current = periods[-1]
    assert current.codigo == "202608041"
    assert current.promedio is None
    in_progress = next(c for c in current.cursos if c.codigo == "750039C")
    assert in_progress.estado == "EN_CURSO"
    assert in_progress.nota is None


# ---------------------------------------------------------------------------
# tabulado (current enrollment)
# ---------------------------------------------------------------------------


def test_parse_tabulado():
    enrollment = parsers.parse_tabulado(read("tabulado.html"))
    assert enrollment.nombre == "GOMEZ PEREZ ANA MARIA"
    assert enrollment.codigo == "2999999"
    assert enrollment.documento == "C.C. 99999999"
    assert enrollment.resolucion == "047"
    assert enrollment.programa == "(3743) INGENIERÍA DE SISTEMAS"
    assert enrollment.sede == "(00) CALI"
    assert enrollment.periodo == "AGOSTO/2026 - DICIEMBRE/2026"
    assert enrollment.categoria == "REGULAR"
    assert enrollment.fecha_matricula == "2026-07-29 00:00:00"

    assert [c.codigo for c in enrollment.cursos] == ["204172C", "750039C", "750126M"]
    cancelled = enrollment.cursos[0]
    assert cancelled.estado == "CANCELADA"
    assert cancelled.fecha_cancelacion == "2026-08-13"

    assert enrollment.total_asignaturas_matriculadas == 2
    assert enrollment.total_asignaturas_canceladas == 1
    assert enrollment.total_creditos_matriculados == 9


# ---------------------------------------------------------------------------
# contacto
# ---------------------------------------------------------------------------


def test_parse_contacto():
    contact = parsers.parse_contacto(read("contacto.html"))
    assert contact.nombre == "ANA MARIA"
    assert contact.apellido == "GOMEZ PEREZ"
    assert contact.tipo_documento == "CÉDULA DE CIUDADANÍA"
    assert contact.numero_documento == "99999999"
    assert contact.expedido_en == "CALI"
    assert contact.fecha_nacimiento == "2001-01-15"
    assert contact.sexo == "MASCULINO"
    assert contact.estado_civil == "UNION LIBRE"
    assert contact.estrato == "TRES"
    assert contact.direccion == "CALLE 1 # 2-3"
    assert contact.telefono_residencia == "3001112233"
    assert contact.telefono_celular == "3004445566"
    assert contact.email_institucional == "ana.gomez.perez@correounivalle.edu.co"
    assert contact.email_alterno == "ana.gomez@example.com"


# ---------------------------------------------------------------------------
# resolucion (prerequisites) & equivalences
# ---------------------------------------------------------------------------


def test_parse_resolucion():
    items = parsers.parse_resolucion(read("resolucion.html"))
    assert len(items) == 44
    first = items[0]
    assert first.codigo == "111023C"
    assert first.asignatura == "MATEMÁTICAS BÁSICAS"
    assert first.creditos == 3
    assert first.prerequisito_codigo is None

    with_prereq = next(i for i in items if i.codigo == "111021C")
    assert with_prereq.prerequisito_codigo == "111023C"
    assert with_prereq.prerequisito_nombre == "MATEMÁTICAS BÁSICAS"
    assert with_prereq.prerequisito_tipo == "PA"


def test_parse_equivalencias_standalone():
    result = parsers.parse_equivalencias(read("equivalencias.html"))
    assert result.has_process is False
    assert result.entries == []


def test_parse_equivalences_from_carpeta():
    entries = parsers.parse_equivalences_from_carpeta(read("carpeta.html"))
    assert len(entries) == 30
    assert entries[0] == {
        "codigo": "404002C",
        "asignatura": "DEPORTE Y SALUD",
        "cal": "4.2",
        "fund": "EC",
        "comp": "SIN",
        "cred": "2",
    }


def test_sira_error_message():
    error_html = "<script>alert(' AVISO 61, Lo sentimos, ha ocurrido un error durante la ejecución de la operación.');</script>"
    message = parsers.sira_error_message(error_html)
    assert message is not None and "AVISO 61" in message
    assert parsers.sira_error_message(read("home.html")) is None
