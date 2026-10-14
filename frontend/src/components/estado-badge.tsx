import type { Course } from "@/lib/api"
import { formatDate } from "@/lib/format"

/** Only exceptional states get a badge; a graded course speaks through its chip. */
export function EstadoBadge({ curso }: { curso: Course }) {
  if (curso.estado === "CANCELADA") {
    return (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs text-muted-foreground">
        Cancelada
        {curso.fecha_cancelacion ? ` (${formatDate(curso.fecha_cancelacion)})` : ""}
      </span>
    )
  }

  if (curso.estado === "EN_CURSO") {
    return (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs text-muted-foreground">
        <span className="size-1.5 rounded-full bg-spark" aria-hidden="true" />
        En curso
      </span>
    )
  }

  return null
}
