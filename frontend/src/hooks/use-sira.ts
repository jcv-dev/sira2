import { useQuery, type UseQueryOptions } from "@tanstack/react-query"

import { api, type Enrollment, type StudentProfile } from "@/lib/api"
import { useRefresh } from "@/hooks/refresh"

function useBaseOptions() {
  return {
    staleTime: 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  }
}

export function useSession() {
  const options = useBaseOptions()
  return useQuery({
    ...options,
    queryKey: ["session"],
    queryFn: () => api.getSession(),
    refetchInterval: 45_000,
    staleTime: 30_000,
  })
}

type DataOptions<T> = Omit<UseQueryOptions<T, Error, T>, "queryKey" | "queryFn"> & {
  refresh?: boolean
}

function useSiraQuery<T>(key: string, fetcher: (refresh: boolean) => Promise<T>, extra?: DataOptions<T>) {
  const { bust } = useRefresh()
  const options = useBaseOptions()
  return useQuery<T>({
    ...options,
    ...extra,
    queryKey: [key, ...(extra?.refresh ? ["explicit"] : []), bust],
    queryFn: () => fetcher(bust > 0 || Boolean(extra?.refresh)),
  })
}

export function useMe() {
  return useSiraQuery<StudentProfile>("me", api.getMe)
}

export function useContact() {
  return useSiraQuery("contact", api.getContact)
}

export function useProgram() {
  return useSiraQuery("program", api.getProgram)
}

export function useGrades() {
  return useSiraQuery("grades", api.getGrades)
}

export function usePeriods() {
  return useSiraQuery("periods", api.getPeriods)
}

export function usePeriod(codigo: string | undefined) {
  const { bust } = useRefresh()
  const options = useBaseOptions()
  return useQuery({
    ...options,
    queryKey: ["period", codigo, bust],
    queryFn: () => api.getPeriod(codigo ?? "", bust > 0),
    enabled: Boolean(codigo),
  })
}

export function useEnrollment() {
  return useSiraQuery<Enrollment>("enrollment", api.getEnrollment)
}

export function useEquivalences() {
  return useSiraQuery("equivalences", api.getEquivalences)
}
