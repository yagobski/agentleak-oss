import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"
import { Button } from "@/components/ui/button"

export function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("agentleak-theme")
    return saved ? saved === "dark" : true
  })
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
    localStorage.setItem("agentleak-theme", dark ? "dark" : "light")
  }, [dark])
  return (
    <Button variant="ghost" size="icon" onClick={() => setDark((d) => !d)} aria-label="Toggle theme">
      {dark ? <Moon className="size-4" /> : <Sun className="size-4" />}
    </Button>
  )
}
