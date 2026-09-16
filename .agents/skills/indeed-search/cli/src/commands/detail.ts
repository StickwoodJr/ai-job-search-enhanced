import { executeBackend, formatPlain, writeError, type JobDetail } from "../helpers.ts"

export interface DetailOpts {
  target: string
  format?: "json" | "plain"
  country?: string
}

export async function runDetail(opts: DetailOpts): Promise<number> {
  try {
    const res: JobDetail = await executeBackend("detail", [opts.target])

    if ((res as any).error) {
      writeError((res as any).error, (res as any).code || "DETAIL_FAILED")
      return 1
    }

    if (opts.format === "plain") {
      process.stdout.write(formatPlain(res) + "\n")
    } else {
      process.stdout.write(JSON.stringify(res, null, 2) + "\n")
    }
    return 0
  } catch (err: any) {
    writeError(err.message || String(err), "EXECUTION_ERROR")
    return 1
  }
}
