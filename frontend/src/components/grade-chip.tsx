import { cn } from "cn"

import { formatGrade, gradeBand } from "@/lib/format"

interface GradeChipProps {
  nota: number | null
  notaRaw?: string | null
  className?: string
}

/** The grade scale is the app's colour language: one chip, four performance bands. */
export function GradeChip({ nota, notaRaw, className }: GradeChipProps) {
  if (nota == null) {
    if (notaRaw) {
      return (
        <span
          className={cn("chip-grade", className)}
          data-band="raw"
          title="Calificación no numérica registrada en SIRA"
        >
          {notaRaw}
        </span>
      )
    }
    return (
      <span className={cn("text-sm text-muted-foreground", className)} title="Sin calificación">
        —
      </span>
    )
  }

  return (
    <span className={cn("chip-grade", className)} data-band={gradeBand(nota)}>
      {formatGrade(nota)}
    </span>
  )
}
