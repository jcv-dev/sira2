import { useEffect, type ReactNode } from "react"

import { AppShell } from "@/components/app-shell"
import { ContactPage } from "@/pages/contact"
import { EnrollmentPage } from "@/pages/enrollment"
import { EquivalencesPage } from "@/pages/equivalences"
import { GradesPage } from "@/pages/grades"
import { NotFoundPage } from "@/pages/not-found"
import { OverviewPage } from "@/pages/overview"
import { ProgramPage } from "@/pages/program"
import { useHashRoute } from "@/lib/router"

export default function App() {
  const route = useHashRoute()

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" })
  }, [route.path])

  let content: ReactNode
  switch (route.path) {
    case "/":
      content = <OverviewPage />
      break
    case "/calificaciones":
      content = <GradesPage route={route} />
      break
    case "/matricula":
      content = <EnrollmentPage />
      break
    case "/programa":
      content = <ProgramPage route={route} />
      break
    case "/equivalencias":
      content = <EquivalencesPage />
      break
    case "/contacto":
      content = <ContactPage />
      break
    default:
      content = <NotFoundPage />
  }

  return <AppShell route={route}>{content}</AppShell>
}
