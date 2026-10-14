import type { ReactNode } from "react"

interface PageHeaderProps {
  title: string
  description?: ReactNode
  children?: ReactNode
}

export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
      <div className="min-w-0">
        <h1 className="text-3xl font-semibold sm:text-[2.125rem] sm:leading-tight">{title}</h1>
        {description ? (
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {children}
    </div>
  )
}
