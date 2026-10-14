import type { ReactNode } from "react"

import {
  ArrowLeftRight,
  ClipboardList,
  GraduationCap,
  IdCard,
  LayoutDashboard,
  ListTree,
  Monitor,
  Moon,
  RefreshCw,
  Sun,
} from "lucide-react"
import { useIsFetching } from "@tanstack/react-query"
import { cn } from "cn"

import { SessionPill } from "@/components/session-pill"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useRefresh } from "@/hooks/refresh"
import { useTheme, type Theme } from "@/lib/theme"
import { href, type HashRoute } from "@/lib/router"

const NAV_ITEMS = [
  { path: "/", label: "Resumen", icon: LayoutDashboard },
  { path: "/calificaciones", label: "Calificaciones", icon: GraduationCap },
  { path: "/matricula", label: "Matrícula", icon: ClipboardList },
  { path: "/programa", label: "Programa", icon: ListTree },
  { path: "/equivalencias", label: "Equivalencias", icon: ArrowLeftRight },
  { path: "/contacto", label: "Contacto", icon: IdCard },
] as const

function isActive(route: HashRoute, path: string): boolean {
  if (path === "/") return route.path === "/"
  return route.path === path || route.path.startsWith(`${path}/`)
}

function BrandMark() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className="size-7 shrink-0">
      <rect width="32" height="32" rx="7" className="fill-primary" />
      <g className="stroke-primary-foreground" fill="none" strokeWidth="2.6" strokeLinecap="round">
        <path d="M9 22.5h14" opacity=".55" />
        <path d="M9 17.5h14" opacity=".8" />
        <path d="M9 12.5h8.5" />
      </g>
    </svg>
  )
}

function Brand() {
  return (
    <a
      href={href("/")}
      className="flex items-baseline gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring/60"
      aria-label="SIRA, ir al resumen"
    >
      <BrandMark />
      <span className="font-display text-lg leading-none font-bold tracking-tight">SIRA</span>
      <span className="text-xs text-muted-foreground">panel académico</span>
    </a>
  )
}

function RefreshButton() {
  const { refresh } = useRefresh()
  const fetching = useIsFetching() > 0

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      aria-label="Actualizar datos"
      title="Actualizar datos (consulta SIRA de nuevo)"
      onClick={refresh}
      disabled={fetching}
    >
      <RefreshCw aria-hidden="true" className={cn("size-4", fetching && "animate-spin")} />
    </Button>
  )
}

function ThemeMenu() {
  const { theme, resolved, setTheme } = useTheme()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="ghost" size="icon-sm" aria-label="Cambiar tema">
          {resolved === "dark" ? (
            <Moon aria-hidden="true" className="size-4" />
          ) : (
            <Sun aria-hidden="true" className="size-4" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {(
          [
            ["light", "Claro", Sun],
            ["dark", "Oscuro", Moon],
            ["system", "Sistema", Monitor],
          ] as const
        ).map(([value, label, Icon]) => (
          <DropdownMenuItem
            key={value}
            onSelect={() => setTheme(value as Theme)}
            className={cn(theme === value && "font-medium text-primary")}
          >
            <Icon aria-hidden="true" className="size-4" />
            {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function NavLinks({ route, horizontal = false }: { route: HashRoute; horizontal?: boolean }) {
  return (
    <nav aria-label="Secciones" className={horizontal ? "-mx-4 px-4" : undefined}>
      <ul
        className={cn(
          "flex gap-1",
          horizontal ? "flex-row overflow-x-auto pb-1" : "flex-col",
        )}
      >
        {NAV_ITEMS.map((item) => {
          const active = isActive(route, item.path)
          const Icon = item.icon
          return (
            <li key={item.path} className={horizontal ? "shrink-0" : undefined}>
              <a
                href={href(item.path)}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/60",
                  horizontal && "border px-3 py-1.5 text-[13px]",
                  active
                    ? "bg-accent font-medium text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                <Icon aria-hidden="true" className="size-4" />
                {item.label}
              </a>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

export function AppShell({ route, children }: { route: HashRoute; children: ReactNode }) {
  return (
    <div className="min-h-dvh">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        Saltar al contenido
      </a>

      {/* Desktop rail */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r px-4 py-6 lg:flex">
        <Brand />
        <div className="mt-8 flex-1">
          <NavLinks route={route} />
        </div>
        <div className="flex flex-col gap-3 border-t pt-4">
          <SessionPill className="px-1" />
          <div className="flex items-center gap-1">
            <RefreshButton />
            <ThemeMenu />
          </div>
        </div>
      </aside>

      <div className="lg:pl-60">
        {/* Mobile top bar */}
        <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur lg:hidden">
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <Brand />
            <div className="flex items-center gap-1">
              <RefreshButton />
              <ThemeMenu />
            </div>
          </div>
          <div className="px-4 pb-2">
            <NavLinks route={route} horizontal />
          </div>
        </header>

        <main id="contenido" className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:px-10 lg:py-12">
          {children}
        </main>
      </div>
    </div>
  )
}
