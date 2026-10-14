/** Typed client for the read-only SIRA API (backend/FastAPI). */

const API_BASE: string = import.meta.env.VITE_API_URL ?? "/api"

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export interface SessionInfo {
  authenticated: boolean
  username: string | null
  student_name: string | null
  credentials_configured: boolean
  message: string | null
}

export interface PersonHeader {
  username: string | null
  full_name: string | null
  institutional_email: string | null
  alternate_email: string | null
}

export interface ProgramRef {
  codigo: string
  sede: string | null
  jornada: string | null
  nombre: string
  display: string
}

export interface CarpetaRef {
  detalle: string
  label: string
}

export interface StudentProfile {
  codigo_estudiante: string | null
  nombre: string | null
  documento: string | null
  programa: ProgramRef | null
  email_institucional: string | null
  tipo_ingreso: string | null
  resolucion: string | null
  tipo_curriculo: string | null
  carpetas: CarpetaRef[]
  header: PersonHeader | null
}

export type CourseStatus = "APROBADA" | "REPROBADA" | "EN_CURSO" | "CANCELADA" | null

export interface Course {
  codigo: string
  grupo: string | null
  nombre: string
  tipologia: string | null
  funcionalidad: string | null
  componente: string | null
  sede: string | null
  creditos: number | null
  nota: number | null
  nota_raw: string | null
  habilitacion: string | null
  estado: CourseStatus
  fecha_cancelacion: string | null
}

export interface PeriodResult {
  codigo: string | null
  nombre: string
  fecha_matricula: string | null
  cursos: Course[]
  creditos_matriculados: number | null
  creditos_aprobados: number | null
  promedio: number | null
  otros: Record<string, string>
}

export interface Grades {
  estudiante: StudentProfile
  promedio_total: number | null
  periodos: PeriodResult[]
}

export interface PeriodOption {
  codigo: string
  fecha: string | null
  label: string
}

export interface Enrollment {
  nombre: string | null
  codigo: string | null
  documento: string | null
  resolucion: string | null
  programa: string | null
  sede: string | null
  jornada: string | null
  periodo: string | null
  categoria: string | null
  fecha_matricula: string | null
  cursos: Course[]
  total_asignaturas_matriculadas: number | null
  total_asignaturas_canceladas: number | null
  total_creditos_matriculados: number | null
}

export interface ContactInfo {
  codigo_persona: string | null
  nombre: string | null
  apellido: string | null
  tipo_documento: string | null
  numero_documento: string | null
  expedido_en: string | null
  fecha_nacimiento: string | null
  sexo: string | null
  estado_civil: string | null
  estrato: string | null
  direccion: string | null
  telefono_residencia: string | null
  telefono_celular: string | null
  telefono_oficina: string | null
  email_institucional: string | null
  email_alterno: string | null
  extras: Record<string, string>
}

export interface PrerequisiteItem {
  numero: number | null
  semestre: string | null
  codigo: string | null
  asignatura: string | null
  tipo_asignatura: string | null
  creditos: number | null
  prerequisito_codigo: string | null
  prerequisito_nombre: string | null
  prerequisito_tipo: string | null
}

export interface ProgramDetail {
  programa: ProgramRef | null
  resolucion: string | null
  periodos: PeriodOption[]
  prerequisitos: PrerequisiteItem[]
}

export interface Equivalences {
  has_process: boolean
  entries: Record<string, string>[]
}

type Params = Record<string, string | boolean | undefined>

async function request<T>(path: string, params?: Params): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value))
    }
  }

  let response: Response
  try {
    response = await fetch(url, { headers: { Accept: "application/json" } })
  } catch {
    throw new ApiError(0, "No se pudo conectar con la API.")
  }

  if (!response.ok) {
    let detail = `La API respondió con error ${response.status}.`
    try {
      const body: unknown = await response.json()
      if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
        detail = body.detail
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(response.status, detail)
  }

  return (await response.json()) as T
}

export const api = {
  getSession: () => request<SessionInfo>("/session"),
  login: () => request<SessionInfo>("/session/login", undefined),
  logout: () => request<SessionInfo>("/session/logout", undefined),
  getMe: (refresh = false) => request<StudentProfile>("/me", { refresh }),
  getContact: (refresh = false) => request<ContactInfo>("/me/contact", { refresh }),
  getProgram: (refresh = false) => request<ProgramDetail>("/program", { refresh }),
  getGrades: (refresh = false) => request<Grades>("/grades", { refresh }),
  getPeriods: (refresh = false) => request<PeriodResult[]>("/grades/periods", { refresh }),
  getPeriod: (codigo: string, refresh = false) =>
    request<PeriodResult>(`/grades/periods/${codigo}`, { refresh }),
  getEnrollment: (refresh = false) => request<Enrollment>("/enrollment", { refresh }),
  getEquivalences: (refresh = false) => request<Equivalences>("/equivalences", { refresh }),
}
