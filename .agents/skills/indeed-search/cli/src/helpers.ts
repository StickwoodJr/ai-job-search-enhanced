import { spawn } from "child_process"
import { resolve } from "path"
import { existsSync } from "fs"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

export interface JobCard {
  id: string
  title: string
  company: string | null
  location: string | null
  date: string | null
  url: string
  direct_url?: string | null
  salary?: {
    min: number | null
    max: number | null
    currency: string | null
    interval: string | null
  }
  is_remote?: boolean
  description_snippet?: string | null
}

export interface JobDetail extends JobCard {
  description: string | null
}

export interface SearchResponse {
  meta: {
    count: number
    query: string
    location: string
    country?: string
  }
  results: JobCard[]
  error?: string
  code?: string
}

function findPythonInterpreter(): string {
  // Try virtual environment relative to workspace root
  const venvPath = resolve(process.cwd(), "mcp-servers/indeed-mcp/.venv/bin/python")
  if (existsSync(venvPath)) {
    return venvPath
  }
  // Try traversing up if run from cli directory
  const altVenvPath = resolve(process.cwd(), "../../../../mcp-servers/indeed-mcp/.venv/bin/python")
  if (existsSync(altVenvPath)) {
    return altVenvPath
  }
  return "python3"
}

function findServerScript(): string {
  const serverPath = resolve(process.cwd(), "mcp-servers/indeed-mcp/server.py")
  if (existsSync(serverPath)) {
    return serverPath
  }
  const altServerPath = resolve(process.cwd(), "../../../../mcp-servers/indeed-mcp/server.py")
  if (existsSync(altServerPath)) {
    return altServerPath
  }
  return serverPath
}

export async function executeBackend(command: "search" | "detail", args: string[]): Promise<any> {
  const pythonBin = findPythonInterpreter()
  const scriptPath = findServerScript()

  return new Promise((resolvePromise, rejectPromise) => {
    const proc = spawn(pythonBin, [scriptPath, command, ...args])

    let stdout = ""
    let stderr = ""

    proc.stdout.on("data", (chunk) => {
      stdout += chunk.toString()
    })

    proc.stderr.on("data", (chunk) => {
      stderr += chunk.toString()
    })

    proc.on("close", (code) => {
      if (code !== 0 && !stdout.trim()) {
        rejectPromise(new Error(stderr.trim() || `Backend process exited with code ${code}`))
        return
      }

      try {
        const parsed = JSON.parse(stdout.trim())
        resolvePromise(parsed)
      } catch (err) {
        rejectPromise(new Error(`Failed to parse backend output: ${stdout || stderr}`))
      }
    })

    proc.on("error", (err) => {
      rejectPromise(err)
    })
  })
}

export function formatTable(results: JobCard[]): string {
  if (results.length === 0) return "No listings found."

  const pad = (str: string, len: number) => {
    const s = str.length > len ? str.slice(0, len - 3) + "..." : str
    return s.padEnd(len)
  }

  const header = `${pad("ID", 20)}  ${pad("TITLE", 32)}  ${pad("COMPANY", 24)}  ${pad("LOCATION", 22)}  ${pad("DATE", 12)}`
  const sep = "-".repeat(header.length)
  const rows = results.map((r) => {
    const id = r.id || ""
    const title = r.title || ""
    const company = r.company || "N/A"
    const location = r.location || "N/A"
    const date = r.date || "N/A"
    return `${pad(id, 20)}  ${pad(title, 32)}  ${pad(company, 24)}  ${pad(location, 22)}  ${pad(date, 12)}`
  })

  return [header, sep, ...rows].join("\n")
}

export function formatPlain(detail: JobDetail): string {
  const lines: string[] = [
    `Title:       ${detail.title}`,
    `Company:     ${detail.company || "N/A"}`,
    `Location:    ${detail.location || "N/A"}`,
    `Date Posted: ${detail.date || "N/A"}`,
    `URL:         ${detail.url}`,
  ]

  if (detail.salary && (detail.salary.min || detail.salary.max)) {
    const min = detail.salary.min ? `$${detail.salary.min}` : ""
    const max = detail.salary.max ? `$${detail.salary.max}` : ""
    const range = min && max ? `${min} - ${max}` : min || max
    const interval = detail.salary.interval ? ` / ${detail.salary.interval}` : ""
    lines.push(`Salary:      ${range}${interval}`)
  }

  if (detail.is_remote) {
    lines.push(`Workplace:   Remote`)
  }

  lines.push("", "--- Description ---", "", detail.description || "No description provided.")
  return lines.join("\n")
}
