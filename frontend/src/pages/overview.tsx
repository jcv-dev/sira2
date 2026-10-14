import { BookOpen, ClipboardList } from "lucide-react"

import { PageHeader } from "@/components/page-header"
import { PeriodSpine } from "@/components/period-spine"
import { CourseList } from "@/components/course-list"
import { EmptyState } from "@/components/empty-state"
import { ErrorState } from "@/components/error-state"
import { Stat } from "@/components/stat"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { useEnrollment, useEquivalences, useGrades, useMe, useProgram } from "@/hooks/use-sira"
import { useRefresh } from "@/hooks/refresh"
import { formatAverage, formatDate, formatInt, formatPercent, titleCaseName } from "@/lib/format"
import { computeStudyProgress } from "@/lib/progress"
import { href } from "@/lib/router"

function OverviewSkeleton() {
  return (
    <div className="space-y-10" aria-busy="true" aria-label="Cargando resumen…">
      <div className="space-y-3">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="flex items-start gap-10">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="flex w-20 flex-col items-center gap-2">
            <Skeleton className="h-6 w-12" />
            <Skeleton className="size-2.5 rounded-full" />
            <Skeleton className="h-3 w-14" />
          </div>
        ))}
      </div>
      <div className="grid gap-8 lg:grid-cols-2">
        <Skeleton className="h-56 rounded-xl" />
        <Skeleton className="h-56 rounded-xl" />
      </div>
    </div>
  )
}

export function OverviewPage() {
  const { refresh } = useRefresh()
  const me = useMe()
  const grades = useGrades()
  const enrollment = useEnrollment()
  const program = useProgram()
  const equivalences = useEquivalences()

  const error = me.error ?? grades.error ?? enrollment.error ?? program.error ?? equivalences.error
  if (error) return <ErrorState error={error} onRetry={refresh} />
  if (
    me.isPending ||
    grades.isPending ||
    enrollment.isPending ||
    program.isPending ||
    equivalences.isPending
  ) {
    return <OverviewSkeleton />
  }

  const profile = me.data
  const gradeData = grades.data
  const enrollmentData = enrollment.data
  const programData = program.data
  const equivalenceData = equivalences.data
  if (!profile || !gradeData || !enrollmentData || !programData || !equivalenceData) {
    return <OverviewSkeleton />
  }

  const periods = gradeData.periodos
  const finished = periods.filter((period) => period.promedio != null)
  const lastFinished = finished[finished.length - 1]

  const progress = computeStudyProgress(
    programData.prerequisitos,
    periods,
    equivalenceData.entries,
  )

  const enrollmentCredits = enrollmentData.total_creditos_matriculados

  return (
    <div className="space-y-12">
      <PageHeader
        title={titleCaseName(profile.nombre) || "Resumen"}
        description={
          <>
            {profile.programa?.display ?? "Programa"} · Código {profile.codigo_estudiante ?? "—"} ·{" "}
            {profile.resolucion ?? "Sin resolución"}
          </>
        }
      />

      <section aria-label="Promedio por periodo académico">
        <p className="mb-3 text-sm lg:hidden">
          <span className="font-display text-lg font-semibold text-primary">
            {formatAverage(gradeData.promedio_total)}
          </span>{" "}
          <span className="text-muted-foreground">promedio acumulado</span>
        </p>
        <PeriodSpine periods={periods} promedioTotal={gradeData.promedio_total} />
        <p className="mt-2 text-xs text-muted-foreground">
          Promedio de cada periodo. Selecciona un punto para ver sus asignaturas.
        </p>
      </section>

      <div className="grid gap-10 lg:grid-cols-2">
        <section aria-labelledby="matricula-title" className="min-w-0">
          <div className="mb-4 flex items-baseline justify-between gap-3 border-b pb-3">
            <h2 id="matricula-title" className="font-display text-lg font-semibold">
              Matrícula actual
            </h2>
            <a
              href={href("/matricula")}
              className="rounded-sm text-sm text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:outline-none"
            >
              Ver matrícula
            </a>
          </div>
          {enrollmentData.periodo ? (
            <p className="mb-3 text-sm text-muted-foreground">
              {enrollmentData.periodo}
              {enrollmentData.fecha_matricula ? ` · matriculado el ${formatDate(enrollmentData.fecha_matricula)}` : ""}
            </p>
          ) : null}
          {enrollmentData.cursos.length > 0 ? (
            <>
              <CourseList
                cursos={enrollmentData.cursos}
                ariaLabel="Asignaturas matriculadas en el periodo actual"
              />
              <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-3 border-t pt-4">
                <Stat label="Asignaturas" value={enrollmentData.total_asignaturas_matriculadas ?? "—"} />
                <Stat
                  label="Canceladas"
                  value={enrollmentData.total_asignaturas_canceladas ?? 0}
                  hint={enrollmentData.total_asignaturas_canceladas ? undefined : "ninguna hasta ahora"}
                />
                <Stat label="Créditos" value={enrollmentCredits ?? "—"} />
              </dl>
            </>
          ) : (
            <EmptyState
              icon={ClipboardList}
              title="Sin matrícula para el periodo actual"
              hint="Cuando SIRA registre tu matrícula, aparecerá aquí."
            />
          )}
        </section>

        <section aria-labelledby="ultimo-title" className="min-w-0">
          <div className="mb-4 flex items-baseline justify-between gap-3 border-b pb-3">
            <h2 id="ultimo-title" className="font-display text-lg font-semibold">
              Último periodo cursado
            </h2>
            <a
              href={href("/calificaciones")}
              className="rounded-sm text-sm text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:outline-none"
            >
              Ver calificaciones
            </a>
          </div>
          {lastFinished ? (
            <>
              <p className="mb-3 flex items-baseline gap-2 text-sm text-muted-foreground">
                {lastFinished.nombre}
                <span className="font-display text-base font-semibold text-foreground">
                  {formatAverage(lastFinished.promedio)}
                </span>
                <span className="text-xs">promedio</span>
              </p>
              <CourseList
                cursos={lastFinished.cursos}
                ariaLabel={`Asignaturas de ${lastFinished.nombre}`}
              />
            </>
          ) : (
            <EmptyState
              icon={BookOpen}
              title="Aún no hay periodos con notas"
              hint="Cuando se registren calificaciones en SIRA, aparecerán aquí."
            />
          )}
        </section>
      </div>

      <section aria-labelledby="avance-title" className="rounded-xl border p-5 sm:p-6">
        <h2 id="avance-title" className="font-display text-lg font-semibold">
          Avance del pénsum
        </h2>
        {progress.ratio != null ? (
          <>
            <div className="mt-4 flex items-baseline justify-between gap-4">
              <p className="text-sm">
                <span className="font-display text-2xl font-semibold">
                  {formatInt(progress.satisfiedCredits)}
                </span>{" "}
                <span className="text-muted-foreground">
                  de {formatInt(progress.planCredits)} créditos del plan
                </span>
              </p>
              <p className="text-sm font-medium text-muted-foreground">
                {formatPercent(progress.ratio)}
              </p>
            </div>
            <Progress
              value={progress.ratio * 100}
              className="mt-3 h-2"
              aria-label={`${formatPercent(progress.ratio)} de los créditos del plan completados`}
            />
            <p className="mt-3 text-xs text-muted-foreground">
              {formatInt(progress.satisfiedCourses)} de {formatInt(progress.planCourses)} asignaturas
              {progress.equivalenceCourses > 0
                ? `, ${formatInt(progress.equivalenceCourses)} reconocidas por equivalencia`
                : ""}
              .
              {progress.inProgressCredits > 0
                ? ` ${formatInt(progress.inProgressCredits)} créditos en curso.`
                : ""}
            </p>
          </>
        ) : (
          <p className="mt-2 text-sm text-muted-foreground">
            No hay datos suficientes para calcular el avance todavía.
          </p>
        )}
      </section>
    </div>
  )
}
