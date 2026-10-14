import { ArrowLeftRight } from "lucide-react"

import { EmptyState } from "@/components/empty-state"
import { ErrorState } from "@/components/error-state"
import { GradeChip } from "@/components/grade-chip"
import { PageHeader } from "@/components/page-header"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useEquivalences } from "@/hooks/use-sira"
import { useRefresh } from "@/hooks/refresh"

function parseGrade(raw: string | undefined): number | null {
  if (!raw) return null
  const value = Number.parseFloat(raw.replace(",", "."))
  return Number.isNaN(value) ? null : value
}

export function EquivalencesPage() {
  const { refresh } = useRefresh()
  const equivalences = useEquivalences()

  if (equivalences.error) return <ErrorState error={equivalences.error} onRetry={refresh} />

  if (equivalences.isPending) {
    return (
      <div className="space-y-8" aria-busy="true" aria-label="Cargando equivalencias…">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    )
  }

  const entries = equivalences.data.entries

  return (
    <div className="space-y-8">
      <PageHeader
        title="Equivalencias"
        description={
          entries.length > 0
            ? `${entries.length} asignaturas reconocidas por equivalencia u homologación en tu historia académica.`
            : "Asignaturas reconocidas por equivalencia u homologación en tu historia académica."
        }
      />

      {entries.length === 0 ? (
        <EmptyState
          icon={ArrowLeftRight}
          title="No hay equivalencias registradas"
          hint="SIRA no reporta procesos de equivalencia para tu programa."
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border">
          <Table className="min-w-[600px]" aria-label="Asignaturas reconocidas por equivalencia">
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-[88px]">Código</TableHead>
                <TableHead>Asignatura</TableHead>
                <TableHead className="w-[64px] text-right">Nota</TableHead>
                <TableHead className="w-[64px]">Fund.</TableHead>
                <TableHead className="w-[64px]">Comp.</TableHead>
                <TableHead className="w-[64px] text-right">Créd.</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((entry, index) => {
                const grade = parseGrade(entry.cal)
                return (
                  <TableRow key={`${entry.codigo ?? index}-${index}`}>
                    <TableCell className="py-2.5 font-medium whitespace-nowrap">{entry.codigo}</TableCell>
                    <TableCell className="min-w-0 py-2.5">
                      <span className="block truncate" title={entry.asignatura}>
                        {entry.asignatura}
                      </span>
                    </TableCell>
                    <TableCell className="py-2.5 text-right">
                      {grade != null ? (
                        <GradeChip nota={grade} />
                      ) : (
                        <span className="text-sm text-muted-foreground">{entry.cal ?? "—"}</span>
                      )}
                    </TableCell>
                    <TableCell className="py-2.5 text-sm text-muted-foreground" title="Código interno de SIRA">
                      {entry.fund ?? "—"}
                    </TableCell>
                    <TableCell className="py-2.5 text-sm text-muted-foreground" title="Código interno de SIRA">
                      {entry.comp ?? "—"}
                    </TableCell>
                    <TableCell className="py-2.5 text-right tabular-nums">{entry.cred ?? "—"}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
