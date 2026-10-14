import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react"
import { useQueryClient } from "@tanstack/react-query"

interface RefreshContextValue {
  /** Increases on every manual refresh; participates in query keys and bypasses server cache. */
  bust: number
  refreshing: boolean
  refresh: () => void
}

const RefreshContext = createContext<RefreshContextValue>({
  bust: 0,
  refreshing: false,
  refresh: () => undefined,
})

export function RefreshProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [bust, setBust] = useState(0)

  const refresh = useCallback(() => {
    setBust((value) => value + 1)
    void queryClient.invalidateQueries()
  }, [queryClient])

  const value = useMemo(
    () => ({ bust, refreshing: false, refresh }),
    [bust, refresh],
  )

  return <RefreshContext.Provider value={value}>{children}</RefreshContext.Provider>
}

export function useRefresh() {
  return useContext(RefreshContext)
}
