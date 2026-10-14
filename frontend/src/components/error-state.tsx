import { TriangleAlert } from "lucide-react"

import { ApiError } from "@/lib/api"
import { Button } from "@/components/ui/button"

function describeError(error: unknown): { title: string; detail: string } {
  if (error instanceof ApiError) {
    if (error.status === 0) {
      return {
        title: "No se pudo conectar con la API",
        detail:
          "Verifica que el backend esté corriendo: uv run uvicorn app.main:app --port 8000 (dentro de backend/).",
      }
    }
    if (error.status === 401) {
      return {
        title: "La API no tiene credenciales",
        detail:
          "Agrega SIRA_USERNAME y SIRA_PASSWORD en backend/.env y reinicia el servidor, o usa POST /session/login.",
      }
    }
    if (error.status === 502) {
      return {
        title: "SIRA no respondió como se esperaba",
        detail: error.message,
      }
    }
    return { title: "La consulta falló", detail: error.message }
  }

  return {
    title: "Error inesperado",
    detail: error instanceof Error ? error.message : "Intenta de nuevo en un momento.",
  }
}

interface ErrorStateProps {
  error: unknown
  onRetry?: () => void
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  const { title, detail } = describeError(error)

  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-xl border border-destructive/25 bg-destructive/5 p-4"
    >
      <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-destructive" />
      <div className="min-w-0">
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
      </div>
      {onRetry ? (
        <Button variant="outline" size="sm" className="ml-auto shrink-0" onClick={onRetry}>
          Reintentar
        </Button>
      ) : null}
    </div>
  )
}
