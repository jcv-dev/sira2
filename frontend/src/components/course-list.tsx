import type { Course } from "@/lib/api"

import { EstadoBadge } from "@/components/estado-badge"
import { GradeChip } from "@/components/grade-chip"

interface CourseListProps {
  cursos: Course[]
  ariaLabel: string
}

/** Compact course rows for narrow columns (name + meta left, grade right). */
export function CourseList({ cursos, ariaLabel }: CourseListProps) {
  return (
    <ul aria-label={ariaLabel} className="divide-y">
      {cursos.map((curso) => (
        <li
          key={`${curso.codigo}-${curso.grupo ?? ""}-${curso.fecha_cancelacion ?? ""}`}
          className="flex min-w-0 items-center gap-3 py-2.5"
        >
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm" title={curso.nombre}>
              {curso.nombre}
            </p>
            <p className="mt-0.5 flex items-center gap-2.5 text-xs text-muted-foreground">
              <span translate="no">{curso.codigo}</span>
              {curso.creditos != null ? <span>{curso.creditos} créditos</span> : null}
              <EstadoBadge curso={curso} />
            </p>
          </div>
          <GradeChip nota={curso.nota} notaRaw={curso.nota_raw} />
        </li>
      ))}
    </ul>
  )
}
