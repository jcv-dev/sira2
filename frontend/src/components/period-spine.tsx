import type { CSSProperties } from "react"

import { cn } from "cn"

import type { PeriodResult } from "@/lib/api"
import { formatAverage, shortPeriodLabel } from "@/lib/format"
import { href } from "@/lib/router"

interface PeriodSpineProps {
  periods: PeriodResult[]
  promedioTotal: number | null
}

function Dot({ current }: { current: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "size-2.5 shrink-0 rounded-full border transition-colors",
        current
          ? "border-spark bg-spark ring-4 ring-spark/15"
          : "border-border bg-card group-hover:border-foreground/40",
      )}
    />
  )
}

/**
 * The one memorable element: the semester spine. Each node links to its grades,
 * the line draws itself once on load, and the accumulated average closes it.
 */
export function PeriodSpine({ periods, promedioTotal }: PeriodSpineProps) {
  if (periods.length === 0) return null
  const currentCode = periods[periods.length - 1]?.codigo ?? null

  return (
    <div className="overflow-x-auto pb-2">
      <ol className="flex min-w-max items-start">
        {periods.map((period, index) => {
          const isCurrent = period.codigo != null && period.codigo === currentCode
          return (
            <li
              key={period.codigo ?? period.nombre}
              className="spine-node w-24"
              style={{ "--i": index } as CSSProperties}
            >
              <a
                href={href("/calificaciones", { periodo: period.codigo ?? undefined })}
                className="group flex w-full flex-col items-center gap-2 rounded-md pt-0.5 pb-1 outline-none focus-visible:ring-2 focus-visible:ring-ring/60"
                title={`${period.nombre}${isCurrent ? " (periodo en curso)" : ""}`}
              >
                <span
                  className={cn(
                    "font-display text-xl font-semibold tracking-tight transition-colors",
                    period.promedio == null && "text-muted-foreground",
                  )}
                >
                  {formatAverage(period.promedio)}
                </span>
                <span className="flex w-full items-center" aria-hidden="true">
                  <span
                    className={cn(
                      "spine-track h-px flex-1",
                      index === 0 ? "bg-transparent" : "bg-border",
                    )}
                    style={{ "--i": index } as CSSProperties}
                  />
                  <Dot current={isCurrent} />
                  <span
                    className="spine-track h-px flex-1 bg-border"
                    style={{ "--i": index } as CSSProperties}
                  />
                </span>
                <span
                  className={cn(
                    "text-xs whitespace-nowrap transition-colors group-hover:text-foreground",
                    isCurrent ? "font-medium text-foreground" : "text-muted-foreground",
                  )}
                >
                  {shortPeriodLabel(period)}
                </span>
              </a>
            </li>
          )
        })}
        <li
          className="spine-node w-28"
          style={{ "--i": periods.length } as CSSProperties}
        >
          <div className="flex w-full flex-col items-center gap-2 pt-0.5 pb-1">
            <span className="font-display text-xl font-semibold tracking-tight text-primary">
              {formatAverage(promedioTotal)}
            </span>
            <span className="flex w-full items-center" aria-hidden="true">
              <span
                className="spine-track h-px flex-1 bg-border"
                style={{ "--i": periods.length } as CSSProperties}
              />
              <span className="size-2.5 shrink-0 rounded-full bg-primary" />
              <span className="h-px flex-1 bg-transparent" />
            </span>
            <span className="text-xs font-medium whitespace-nowrap">Acumulado</span>
          </div>
        </li>
      </ol>
    </div>
  )
}
