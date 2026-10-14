import type { ReactNode } from "react"

import { IdCard } from "lucide-react"

import { CopyButton } from "@/components/copy-button"
import { ErrorState } from "@/components/error-state"
import { PageHeader } from "@/components/page-header"
import { Skeleton } from "@/components/ui/skeleton"
import { useContact } from "@/hooks/use-sira"
import { useRefresh } from "@/hooks/refresh"
import { formatDate } from "@/lib/format"

interface Field {
  label: string
  value: ReactNode
  copy?: string
}

export function ContactPage() {
  const { refresh } = useRefresh()
  const contact = useContact()

  if (contact.error) return <ErrorState error={contact.error} onRetry={refresh} />

  if (contact.isPending) {
    return (
      <div className="space-y-8" aria-busy="true" aria-label="Cargando contacto…">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
    )
  }

  const data = contact.data

  const telLink = (value: string) => (
    <a href={`tel:${value.replace(/\s+/g, "")}`} className="text-foreground hover:underline">
      {value}
    </a>
  )

  const mailLink = (value: string) => (
    <a href={`mailto:${value}`} className="break-all text-foreground hover:underline">
      {value}
    </a>
  )

  const fields: Field[] = []
  const documento = [data.tipo_documento, data.numero_documento].filter(Boolean).join(" ")
  if (documento) fields.push({ label: "Documento", value: documento, copy: data.numero_documento ?? undefined })
  if (data.expedido_en) fields.push({ label: "Expedido en", value: data.expedido_en })
  if (data.fecha_nacimiento) fields.push({ label: "Fecha de nacimiento", value: formatDate(data.fecha_nacimiento) })
  if (data.sexo) fields.push({ label: "Sexo", value: data.sexo })
  if (data.estado_civil) fields.push({ label: "Estado civil", value: data.estado_civil })
  if (data.estrato) fields.push({ label: "Estrato", value: data.estrato })
  if (data.direccion) fields.push({ label: "Dirección", value: data.direccion, copy: data.direccion })
  if (data.email_institucional)
    fields.push({ label: "Correo institucional", value: mailLink(data.email_institucional), copy: data.email_institucional })
  if (data.email_alterno)
    fields.push({ label: "Correo alterno", value: mailLink(data.email_alterno), copy: data.email_alterno })
  if (data.telefono_celular)
    fields.push({ label: "Celular", value: telLink(data.telefono_celular), copy: data.telefono_celular })
  if (data.telefono_residencia)
    fields.push({ label: "Teléfono de residencia", value: telLink(data.telefono_residencia), copy: data.telefono_residencia })
  if (data.telefono_oficina)
    fields.push({ label: "Teléfono de oficina", value: telLink(data.telefono_oficina), copy: data.telefono_oficina })
  if (data.codigo_persona)
    fields.push({ label: "Código de persona (SIRA)", value: data.codigo_persona, copy: data.codigo_persona })

  return (
    <div className="space-y-8">
      <PageHeader title="Contacto" description="Datos personales y de contacto registrados en SIRA (solo lectura)." />

      {fields.length === 0 ? (
        <p className="text-sm text-muted-foreground">SIRA no reporta datos de contacto.</p>
      ) : (
        <dl className="divide-y rounded-xl border">
          {fields.map((field) => (
            <div key={field.label} className="flex items-center justify-between gap-3 px-4 py-3.5 sm:px-5">
              <dt className="shrink-0 text-sm text-muted-foreground">{field.label}</dt>
              <dd className="flex min-w-0 items-center gap-1 text-right text-sm">
                <span className="min-w-0 truncate">{field.value}</span>
                {field.copy ? <CopyButton value={field.copy} label={field.label.toLowerCase()} /> : null}
              </dd>
            </div>
          ))}
        </dl>
      )}

      <p className="flex items-start gap-2 text-xs text-muted-foreground">
        <IdCard aria-hidden="true" className="mt-0.5 size-3.5 shrink-0" />
        Para corregir estos datos, usa SIRA o acude a la Oficina de Registro Académico y Admisiones.
      </p>
    </div>
  )
}
