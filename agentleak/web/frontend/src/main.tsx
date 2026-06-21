import React from "react"
import ReactDOM from "react-dom/client"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import "@fontsource-variable/hanken-grotesk"
import "@fontsource/jetbrains-mono/400.css"
import "@fontsource/jetbrains-mono/500.css"
import "@fontsource/jetbrains-mono/600.css"
import "./index.css"
import { TooltipProvider } from "./components/ui/tooltip"
import { Toaster } from "./components/ui/sonner"
import { AppShell } from "./layout/AppShell"
import { Dashboard } from "./pages/Dashboard"
import { Playground } from "./pages/Playground"
import { ProjectDetail } from "./pages/ProjectDetail"
import { Projects } from "./pages/Projects"
import { RunView } from "./pages/RunView"
import { Scenarios } from "./pages/Scenarios"
import { Settings } from "./pages/Settings"

// Apply the saved theme before first paint (default: dark / black).
const savedTheme = localStorage.getItem("agentleak-theme")
document.documentElement.classList.toggle("dark", savedTheme ? savedTheme === "dark" : true)

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <TooltipProvider delayDuration={200}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<Dashboard />} />
            <Route path="projects" element={<Projects />} />
            <Route path="projects/:id" element={<ProjectDetail />} />
            <Route path="runs/:id" element={<RunView />} />
            <Route path="playground" element={<Playground />} />
            <Route path="scenarios" element={<Scenarios />} />
            <Route path="settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster />
    </TooltipProvider>
  </React.StrictMode>
)
