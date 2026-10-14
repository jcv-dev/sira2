import type { Course, PeriodResult, PrerequisiteItem } from "@/lib/api"

export interface StudyProgress {
  planCourses: number
  planCredits: number
  satisfiedCourses: number
  satisfiedCredits: number
  /** Plan courses satisfied through an equivalence (not through a registered period). */
  equivalenceCourses: number
  inProgressCredits: number
  ratio: number | null
}

function normalizeName(name: string | null | undefined): string {
  return (name ?? "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("es-CO")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
}

function nameTokens(name: string | null | undefined): string[] {
  return normalizeName(name).split(" ").filter(Boolean)
}

/**
 * A course counts as completed when it has a numeric pass, or a recognised
 * non-numeric grade (SIRA uses "E.X" / "A.P" for exam-based approvals).
 */
function isRecognized(course: Course): boolean {
  if (course.estado === "CANCELADA") return false
  if (course.estado === "APROBADA") return true
  return Boolean(course.nota_raw)
}

/**
 * Progress through the plan of studies, counting both courses passed in registered
 * periods and courses recognised by equivalence.
 *
 * Equivalences are matched to plan courses by code first. Curriculum changes keep
 * the course name but change the code (e.g. equivalence "111048M ÁLGEBRA LINEAL"
 * vs plan "111038C ÁLGEBRA LINEAL"), so a normalized-name match is the fallback;
 * containment of names is a last resort for renamed courses ("INTRODUCCIÓN A LA
 * INGENIERÍA" vs "INTRODUCCIÓN A LA INGENIERÍA - SISTEMAS").
 */
export function computeStudyProgress(
  planItems: PrerequisiteItem[],
  periods: PeriodResult[],
  equivalenceEntries: Record<string, string>[],
): StudyProgress {
  const plan = planItems.filter(
    (item): item is PrerequisiteItem & { codigo: string } => Boolean(item.codigo),
  )
  const planCredits = plan.reduce((sum, item) => sum + (item.creditos ?? 0), 0)

  const satisfied = new Set<string>()

  // 1. Courses passed in the registered periods.
  for (const period of periods) {
    for (const course of period.cursos) {
      if (isRecognized(course)) satisfied.add(course.codigo)
    }
  }

  // 2. Equivalences mapped onto the plan.
  const planByCode = new Set(plan.map((item) => item.codigo))
  const planByNormalizedName = new Map<string, string[]>()
  for (const item of plan) {
    const key = normalizeName(item.asignatura)
    planByNormalizedName.set(key, [...(planByNormalizedName.get(key) ?? []), item.codigo])
  }

  const fromEquivalences = new Set<string>()
  const mark = (codigo: string) => {
    if (!satisfied.has(codigo)) fromEquivalences.add(codigo)
    satisfied.add(codigo)
  }

  for (const entry of equivalenceEntries) {
    const code = entry.codigo
    if (!code) continue

    if (planByCode.has(code)) {
      mark(code)
      continue
    }

    const exact = planByNormalizedName.get(normalizeName(entry.asignatura))
    if (exact && exact.length === 1) {
      mark(exact[0])
      continue
    }

    const tokens = nameTokens(entry.asignatura)
    if (tokens.length < 3) continue
    const candidates = plan.filter((item) => {
      const planTokens = new Set(nameTokens(item.asignatura))
      const covered = tokens.every((token) => planTokens.has(token))
      const extra = [...planTokens].filter((token) => !tokens.includes(token))
      return covered && extra.every((token) => !/\d/.test(token))
    })
    if (candidates.length === 1) mark(candidates[0].codigo)
  }

  const satisfiedPlan = plan.filter((item) => satisfied.has(item.codigo))
  const satisfiedCredits = satisfiedPlan.reduce((sum, item) => sum + (item.creditos ?? 0), 0)

  const current = periods[periods.length - 1]
  const inProgressCredits = current
    ? current.cursos
        .filter((course) => course.estado === "EN_CURSO")
        .reduce((sum, course) => sum + (course.creditos ?? 0), 0)
    : 0

  return {
    planCourses: plan.length,
    planCredits,
    satisfiedCourses: satisfiedPlan.length,
    satisfiedCredits,
    equivalenceCourses: fromEquivalences.size,
    inProgressCredits,
    ratio: planCredits > 0 ? Math.min(satisfiedCredits / planCredits, 1) : null,
  }
}
