import { useState } from "react"

import { Check, Copy } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"

export function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false)

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      aria-label={`Copiar ${label}`}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value)
          toast.success("Copiado")
          setCopied(true)
          window.setTimeout(() => setCopied(false), 1500)
        } catch {
          toast.error("No se pudo copiar")
        }
      }}
    >
      {copied ? (
        <Check aria-hidden="true" className="size-3.5" />
      ) : (
        <Copy aria-hidden="true" className="size-3.5" />
      )}
    </Button>
  )
}
