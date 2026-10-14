/** Locale-aware formatting helpers. All display formatting goes through Intl. */

import type { PeriodResult } from "@/lib/api"

const gradeFmt = new Intl.NumberFormat("es-CO", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

const averageFmt = new Intl.NumberFormat("es-CO", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const intFmt = new Intl.NumberFormat("es-CO")

export const formatGrade = (value: number) => gradeFmt.format(value)
export const formatAverage = (value: number | null) => (value == null ? "—" : averageFmt.format(value))
export const formatInt = (value: number) => intFmt.format(value)

/** SIRA sends "2024-07-30 00:00:00" (no timezone); parse as local time. */
export function parseSiraDate(raw: string | null | undefined): Date | null {
  if (!raw) return null
  const date = new Date(raw.replace(" ", "T"))
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(raw: string | null | undefined): string {
  const date = parseSiraDate(raw)
  if (!date) return "—"
  return new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", year: "numeric" }).format(date)
}

const fullDateFmt = new Intl.DateTimeFormat("es-CO", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
})

export function formatFullDate(date: Date): string {
  return fullDateFmt.format(date)
}

/** "VALENCIA RIVAS JUAN CAMILO" -> "Valencia Rivas Juan Camilo" (display only). */
export function titleCaseName(raw: string | null | undefined): string {
  if (!raw) return ""
  return raw
    .toLocaleLowerCase("es-CO")
    .replace(/\p{L}+/gu, (word) => word.charAt(0).toLocaleUpperCase("es-CO") + word.slice(1))
}

export type GradeBand = "top" | "high" | "pass" | "fail"

export function gradeBand(value: number): GradeBand {
  if (value >= 4.5) return "top"
  if (value >= 4) return "high"
  if (value >= 3) return "pass"
  return "fail"
}

/** "2024-2" style short label derived from the enrollment date; falls back to the full name. */
export function shortPeriodLabel(period: Pick<PeriodResult, "codigo" | "nombre" | "fecha_matricula">): string {
  const date = parseSiraDate(period.fecha_matricula)
  const year = date?.getFullYear() ?? (period.codigo ? Number(period.codigo.slice(0, 4)) : null)

  let semester: 1 | 2 | null = null
  if (date) {
    semester = date.getMonth() >= 6 ? 2 : 1
  } else if (/AGOSTO|SEPTIEMBRE|OCTUBRE/i.test(period.nombre)) {
    semester = 2
  } else if (/FEBRERO|MARZO|ABRIL/i.test(period.nombre)) {
    semester = 1
  }

  if (year && semester && Number.isFinite(year)) return `${year}-${semester}`
  return period.nombre
}

export function formatDelta(current: number | null, previous: number | null): string | null {
  if (current == null || previous == null) return null
  const diff = current - previous
  const sign = diff > 0 ? "+" : diff < 0 ? "−" : ""
  return `${sign}${averageFmt.format(Math.abs(diff))}`
}

export function formatPercent(ratio: number): string {
  return new Intl.NumberFormat("es-CO", { style: "percent", maximumFractionDigits: 0 }).format(ratio)
}
