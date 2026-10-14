import { ClipboardList } from "lucide-react"

import { CourseTable } from "@/components/course-table"
import { EmptyState } from "@/components/empty-state"
import { ErrorState } from "@/components/error-state"
import { PageHeader } from "@/components/page-header"
import { Stat } from "@/components/stat"
import { Skeleton } from "@/components/ui/skeleton"
import { useEnrollment } from "@/hooks/use-sira"
import { useRefresh } from "@/hooks/refresh"
import { formatDate } from "@/lib/format"

export function EnrollmentPage() {
  const { refresh } = useRefresh()
  const enrollment = useEnrollment()

  if (enrollment.error) return <ErrorState error={enrollment.error} onRetry={refresh} />

  if (enrollment.isPending) {
    return (
      <div className="space-y-8" aria-busy="true" aria-label="Cargando matrícula…">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-40 rounded-xl" />
      </div>
    )
  }

  const data = enrollment.data

  return (
    <div className="space-y-8">
      <PageHeader
        title="Matrícula"
        description={
          <>
            {data.periodo ?? "Periodo actual"}
            {data.fecha_matricula ? ` · matriculado el ${formatDate(data.fecha_matricula)}` : ""}
            {data.categoria ? ` · categoría ${data.categoria}` : ""}
          </>
        }
      />

      {data.cursos.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No hay asignaturas matriculadas en el periodo actual"
          hint="Cuando SIRA registre tu matrícula, el tabulado aparecerá aquí."
        />
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-6 border-y py-5 sm:grid-cols-3">
            <Stat label="Asignaturas matriculadas" value={data.total_asignaturas_matriculadas ?? "—"} />
            <Stat
              label="Asignaturas canceladas"
              value={data.total_asignaturas_canceladas ?? 0}
              hint={data.total_asignaturas_canceladas ? "según el tabulado" : "ninguna hasta ahora"}
            />
            <Stat label="Créditos matriculados" value={data.total_creditos_matriculados ?? "—"} />
          </dl>

          <section aria-label="Asignaturas del tabulado">
            <CourseTable cursos={data.cursos} ariaLabel="Asignaturas matriculadas en el periodo actual" />
          </section>

          <p className="text-xs text-muted-foreground">
            Tabulado provisional de matrícula académica, igual que en SIRA. Si acabas de hacer un cambio,
            usa «Actualizar datos».
          </p>
        </>
      )}
    </div>
  )
}
