import { useEffect, useMemo, useState } from "react"

export interface HashRoute {
  path: string
  params: URLSearchParams
}

function readHash(): string {
  return window.location.hash.replace(/^#/, "") || "/"
}

/** Minimal hash router: keeps every view state deep-linkable without extra deps. */
export function useHashRoute(): HashRoute {
  const [hash, setHash] = useState(readHash)

  useEffect(() => {
    const onChange = () => setHash(readHash())
    window.addEventListener("hashchange", onChange)
    return () => window.removeEventListener("hashchange", onChange)
  }, [])

  return useMemo(() => {
    const [path, query = ""] = hash.split("?")
    return { path: path || "/", params: new URLSearchParams(query) }
  }, [hash])
}

/** Build an href for the hash router. */
export function href(path: string, params?: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") search.set(key, value)
    }
  }
  const query = search.toString()
  return `#${path}${query ? `?${query}` : ""}`
}

export function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
}
