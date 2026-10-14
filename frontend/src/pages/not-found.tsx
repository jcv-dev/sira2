import { Compass } from "lucide-react"

import { EmptyState } from "@/components/empty-state"
import { href } from "@/lib/router"

export function NotFoundPage() {
  return (
    <div className="space-y-6">
      <EmptyState icon={Compass} title="Esta página no existe" hint="La dirección no corresponde a ninguna sección del panel." />
      <p className="text-center">
        <a
          href={href("/")}
          className="rounded-sm text-sm text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:outline-none"
        >
          Volver al resumen
        </a>
      </p>
    </div>
  )
}
