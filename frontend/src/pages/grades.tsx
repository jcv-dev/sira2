import { GraduationCap } from "lucide-react"
import { cn } from "cn"

import { CourseTable } from "@/components/course-table"
import { EmptyState } from "@/components/empty-state"
import { ErrorState } from "@/components/error-state"
import { PageHeader } from "@/components/page-header"
import { Skeleton } from "@/components/ui/skeleton"
import { useGrades } from "@/hooks/use-sira"
import { useRefresh } from "@/hooks/refresh"
import type { PeriodResult } from "@/lib/api"
import { formatAverage, formatDate, formatDelta, shortPeriodLabel } from "@/lib/format"
import { href, prefersReducedMotion, type HashRoute } from "@/lib/router"
import { useEffect } from "react"

function GradesSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Cargando calificaciones…">
      <Skeleton className="h-9 w-64" />
      <div className="flex gap-2">
        {[0, 1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-7 w-16 rounded-full" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}

function PeriodSection({
  period,
  previous,
}: {
  period: PeriodResult
  previous: PeriodResult | undefined
}) {
  const delta =
    period.promedio != null && previous?.promedio != null
      ? formatDelta(period.promedio, previous.promedio)
      : null
  const deltaPositive =
    period.promedio != null && previous?.promedio != null && period.promedio >= previous.promedio

  return (
    <section id={`periodo-${period.codigo ?? period.nombre}`}>
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 border-b pb-3">
        <div className="min-w-0">
          <h2 className="font-display text-xl font-semibold">
            {shortPeriodLabel(period)}{" "}
            <span className="text-sm font-normal text-muted-foreground">{period.nombre}</span>
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {period.fecha_matricula ? `Matriculado el ${formatDate(period.fecha_matricula)} · ` : ""}
            {period.cursos.length} asignaturas
            {period.promedio == null && period.cursos.length > 0 ? " · periodo en curso" : ""}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground">Promedio</p>
          <p className="font-display text-2xl leading-tight font-semibold">
            {formatAverage(period.promedio)}
          </p>
          {delta != null ? (
            <p className={cn("text-xs", deltaPositive ? "text-chart-1" : "text-destructive")}>
              {delta} vs periodo anterior
            </p>
          ) : null}
        </div>
      </header>

      <div className="mt-4">
        {period.cursos.length > 0 ? (
          <CourseTable cursos={period.cursos} ariaLabel={`Asignaturas de ${period.nombre}`} />
        ) : (
          <EmptyState
            icon={GraduationCap}
            title="Sin asignaturas registradas en este periodo"
            hint="SIRA no reporta cursos para este periodo."
          />
        )}
      </div>

      {period.cursos.length > 0 ? (
        <footer className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
          <span>
            Créditos matriculados: <span className="font-medium text-foreground">{period.creditos_matriculados ?? "—"}</span>
          </span>
          <span>
            Aprobados: <span className="font-medium text-foreground">{period.creditos_aprobados ?? "—"}</span>
          </span>
          {period.otros["% Créd. Aprobados"] ? (
            <span>
              Avance: <span className="font-medium text-foreground">{period.otros["% Créd. Aprobados"]}</span>
            </span>
          ) : null}
        </footer>
      ) : null}
    </section>
  )
}

export function GradesPage({ route }: { route: HashRoute }) {
  const { refresh } = useRefresh()
  const grades = useGrades()
  const selectedPeriod = route.params.get("periodo")

  useEffect(() => {
    if (!selectedPeriod || !grades.data) return
    const target = document.getElementById(`periodo-${selectedPeriod}`)
    target?.scrollIntoView({
      behavior: prefersReducedMotion() ? "auto" : "smooth",
      block: "start",
    })
  }, [selectedPeriod, grades.data])

  if (grades.error) return <ErrorState error={grades.error} onRetry={refresh} />
  if (grades.isPending) return <GradesSkeleton />

  const periods = grades.data.periodos
  const average = grades.data.promedio_total

  return (
    <div className="space-y-10">
      <PageHeader
        title="Calificaciones"
        description={
          <>
            {periods.length} periodos registrados
            {average != null ? ` · promedio acumulado ${formatAverage(average)}` : ""}
          </>
        }
      />

      {periods.length === 0 ? (
        <EmptyState
          icon={GraduationCap}
          title="Todavía no hay calificaciones"
          hint="SIRA aún no reporta periodos académicos para este programa."
        />
      ) : (
        <>
          <nav aria-label="Ir a un periodo">
            <ul className="flex flex-wrap gap-2">
              <li>
                <a
                  href={href("/calificaciones")}
                  className={cn(
                    "inline-flex rounded-full border px-3 py-1 text-[13px] transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
                    !selectedPeriod
                      ? "border-foreground bg-foreground text-background"
                      : "border-border text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                  )}
                >
                  Todos
                </a>
              </li>
              {periods.map((period) => {
                const active = selectedPeriod === period.codigo
                return (
                  <li key={period.codigo ?? period.nombre}>
                    <a
                      href={href("/calificaciones", { periodo: period.codigo ?? undefined })}
                      aria-current={active ? "true" : undefined}
                      className={cn(
                        "inline-flex rounded-full border px-3 py-1 text-[13px] transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
                        active
                          ? "border-foreground bg-foreground text-background"
                          : "border-border text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                      )}
                    >
                      {shortPeriodLabel(period)}
                    </a>
                  </li>
                )
              })}
            </ul>
          </nav>

          <div className="space-y-12">
            {periods.map((period) => {
              const previousFinished = periods
                .slice(0, periods.indexOf(period))
                .reverse()
                .find((candidate) => candidate.promedio != null)
              return (
                <PeriodSection
                  key={period.codigo ?? period.nombre}
                  period={period}
                  previous={previousFinished}
                />
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
