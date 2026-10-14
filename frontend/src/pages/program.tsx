import { useEffect, useMemo, useState } from "react"

import { ListTree, Search } from "lucide-react"

import { EmptyState } from "@/components/empty-state"
import { ErrorState } from "@/components/error-state"
import { PageHeader } from "@/components/page-header"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { useProgram } from "@/hooks/use-sira"
import { useRefresh } from "@/hooks/refresh"
import type { PrerequisiteItem } from "@/lib/api"
import { formatInt } from "@/lib/format"
import type { HashRoute } from "@/lib/router"

function ProgramSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Cargando programa…">
      <Skeleton className="h-9 w-64" />
      <Skeleton className="h-10 w-full max-w-sm" />
      <Skeleton className="h-72 rounded-xl" />
    </div>
  )
}

function PrerequisiteCell({ item }: { item: PrerequisiteItem }) {
  if (!item.prerequisito_codigo) {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <span className="block min-w-0">
      <span className="block font-medium whitespace-nowrap">{item.prerequisito_codigo}</span>
      <span className="block max-w-56 truncate text-xs text-muted-foreground" title={item.prerequisito_nombre ?? undefined}>
        {item.prerequisito_nombre ?? "Prerrequisito"}
      </span>
    </span>
  )
}

export function ProgramPage({ route }: { route: HashRoute }) {
  const { refresh } = useRefresh()
  const program = useProgram()
  const [query, setQuery] = useState(() => route.params.get("q") ?? "")

  // Keep the filter deep-linkable without re-rendering through the hash router.
  useEffect(() => {
    const next = query.trim()
      ? `#/programa?q=${encodeURIComponent(query.trim())}`
      : "#/programa"
    window.history.replaceState(null, "", next)
  }, [query])

  const items = useMemo(() => program.data?.prerequisitos ?? [], [program.data])

  const filtered = useMemo(() => {
    const q = query.trim().toLocaleLowerCase("es-CO")
    if (!q) return items
    return items.filter(
      (item) =>
        (item.codigo ?? "").toLocaleLowerCase("es-CO").includes(q) ||
        (item.asignatura ?? "").toLocaleLowerCase("es-CO").includes(q),
    )
  }, [items, query])

  const groups = useMemo(() => {
    const map = new Map<string, PrerequisiteItem[]>()
    for (const item of filtered) {
      const key = item.semestre ? item.semestre.padStart(2, "0") : "—"
      const list = map.get(key) ?? []
      list.push(item)
      map.set(key, list)
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0], "es", { numeric: true }))
  }, [filtered])

  if (program.error) return <ErrorState error={program.error} onRetry={refresh} />
  if (program.isPending) return <ProgramSkeleton />

  const data = program.data
  const planCredits = items.reduce((sum, item) => sum + (item.creditos ?? 0), 0)

  return (
    <div className="space-y-8">
      <PageHeader
        title="Programa"
        description={
          <>
            {data.programa?.display ?? "Plan de estudios"} · {items.length} asignaturas ·{" "}
            {formatInt(planCredits)} créditos · {data.resolucion ?? "sin resolución"}
          </>
        }
      />

      <div>
        <label htmlFor="buscar-asignatura" className="sr-only">
          Buscar asignatura
        </label>
        <div className="relative max-w-sm">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            id="buscar-asignatura"
            name="q"
            type="search"
            inputMode="search"
            autoComplete="off"
            spellCheck={false}
            placeholder="Buscar por código o asignatura…"
            className="pl-9"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <p aria-live="polite" className="mt-2 text-xs text-muted-foreground">
          {query.trim()
            ? `${filtered.length} ${filtered.length === 1 ? "resultado" : "resultados"} para “${query.trim()}”.`
            : "Plan de estudios de tu resolución, con prerrequisitos."}
        </p>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={ListTree}
          title="Sin resultados"
          hint="Revisa el código o el nombre de la asignatura."
        />
      ) : (
        <div className="space-y-10">
          {groups.map(([semester, semesterItems]) => (
            <section key={semester} aria-label={`Semestre ${semester}`}>
              <h2 className="mb-3 font-display text-base font-semibold">
                {semester === "—" ? "Sin semestre definido" : `Semestre ${semester}`}
              </h2>
              <div className="overflow-x-auto rounded-xl border">
                <Table className="min-w-[640px]" aria-label={`Asignaturas del semestre ${semester}`}>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="w-[96px]">Código</TableHead>
                      <TableHead>Asignatura</TableHead>
                      <TableHead className="w-[72px] text-right">Créditos</TableHead>
                      <TableHead className="w-[90px]">Tipo</TableHead>
                      <TableHead className="w-[220px]">Prerrequisito</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {semesterItems.map((item) => (
                      <TableRow key={`${item.codigo}-${item.numero}`}>
                        <TableCell className="py-2.5 font-medium whitespace-nowrap">{item.codigo}</TableCell>
                        <TableCell className="min-w-0 py-2.5">
                          <span className="block truncate" title={item.asignatura ?? undefined}>
                            {item.asignatura}
                          </span>
                        </TableCell>
                        <TableCell className="py-2.5 text-right tabular-nums">
                          {item.creditos ?? "—"}
                        </TableCell>
                        <TableCell className="py-2.5">
                          {item.tipo_asignatura ? (
                            <Badge variant="outline" className="font-normal text-muted-foreground">
                              {item.tipo_asignatura}
                            </Badge>
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell className="py-2.5">
                          <PrerequisiteCell item={item} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
