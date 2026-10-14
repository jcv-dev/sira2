import { useSession } from "@/hooks/use-sira"
import { titleCaseName } from "@/lib/format"
import { cn } from "cn"

/** Small status dot + label describing the SIRA connection. */
export function SessionPill({ className }: { className?: string }) {
  const { data, isPending, isError } = useSession()

  if (isPending) {
    return (
      <span className={cn("inline-flex items-center gap-2 text-xs text-muted-foreground", className)}>
        <span className="size-2 animate-pulse rounded-full bg-muted-foreground/40" aria-hidden="true" />
        Verificando sesión…
      </span>
    )
  }

  if (isError || !data) {
    return (
      <span className={cn("inline-flex items-center gap-2 text-xs text-muted-foreground", className)}>
        <span className="size-2 rounded-full bg-destructive" aria-hidden="true" />
        API sin conexión
      </span>
    )
  }

  if (data.authenticated) {
    return (
      <span className={cn("inline-flex items-center gap-2 text-xs text-muted-foreground", className)}>
        <span className="size-2 rounded-full bg-chart-1" aria-hidden="true" />
        <span className="max-w-44 truncate" title={data.student_name ?? data.username ?? undefined}>
          {titleCaseName(data.student_name) || data.username}
        </span>
      </span>
    )
  }

  if (data.credentials_configured) {
    return (
      <span
        className={cn("inline-flex items-center gap-2 text-xs text-muted-foreground", className)}
        title="La API iniciará sesión en SIRA con la primera consulta."
      >
        <span className="size-2 rounded-full bg-spark" aria-hidden="true" />
        Sesión al consultar
      </span>
    )
  }

  return (
    <span
      className={cn("inline-flex items-center gap-2 text-xs text-muted-foreground", className)}
      title="Configura SIRA_USERNAME y SIRA_PASSWORD en backend/.env"
    >
      <span className="size-2 rounded-full bg-destructive" aria-hidden="true" />
      Sin credenciales
    </span>
  )
}
