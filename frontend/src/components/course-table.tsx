import type { Course } from "@/lib/api"

import { EstadoBadge } from "@/components/estado-badge"
import { GradeChip } from "@/components/grade-chip"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface CourseTableProps {
  cursos: Course[]
  /** Extra muted text under the course name (e.g. group or component). */
  density?: "comfortable" | "compact"
  ariaLabel: string
}

export function CourseTable({ cursos, density = "comfortable", ariaLabel }: CourseTableProps) {
  const cellPadding = density === "compact" ? "py-2" : "py-2.5"

  return (
    <div className="overflow-x-auto">
      <Table className="min-w-[540px]" aria-label={ariaLabel}>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[92px]">Código</TableHead>
            <TableHead>Asignatura</TableHead>
            <TableHead className="w-[72px] text-right">Créditos</TableHead>
            <TableHead className="w-[76px] text-right">Nota</TableHead>
            <TableHead className="w-[150px]">Estado</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {cursos.map((curso) => (
            <TableRow key={`${curso.codigo}-${curso.grupo ?? ""}-${curso.fecha_cancelacion ?? ""}`}>
              <TableCell className={`${cellPadding} font-medium whitespace-nowrap`} translate="no">
                {curso.codigo}
              </TableCell>
              <TableCell className={`${cellPadding} min-w-0`}>
                <span className="block truncate" title={curso.nombre}>
                  {curso.nombre}
                </span>
              </TableCell>
              <TableCell className={`${cellPadding} text-right tabular-nums`}>
                {curso.creditos ?? "—"}
              </TableCell>
              <TableCell className={`${cellPadding} text-right`}>
                <GradeChip nota={curso.nota} notaRaw={curso.nota_raw} />
              </TableCell>
              <TableCell className={cellPadding}>
                <EstadoBadge curso={curso} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
