export interface TechTOJob {
  id: number | string;
  title: string;
  description?: string;
  min_compensation?: string | null;
  max_compensation?: string | null;
  compensation_time_frame?: string | null;
  compensation_currency?: string | null;
  location?: string | null;
  posted_at?: string | null;
  job_details_path?: string | null;
  employer?: {
    name?: string;
    website?: string;
  } | null;
  job_location?: {
    name?: string;
  } | null;
  job_type?: {
    title?: string;
  } | null;
  category?: {
    name?: string;
  } | null;
}

export interface StandardJobResult {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  date: string | null;
  url: string;
  salary: string | null;
  employmentType: string | null;
}

export async function fetchWithBackoff(url: string, retries = 3): Promise<string> {
  const headers = {
    "User-Agent": "Mozilla/5.0 (compatible; techto-cli/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
  };

  for (let i = 0; i < retries; i++) {
    try {
      const resp = await fetch(url, { headers });
      if (resp.status === 404) return "";
      if (resp.ok) return await resp.text();
      if (resp.status === 429 || resp.status >= 500) {
        await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000 + Math.random() * 500));
        continue;
      }
      throw new Error(`HTTP Error ${resp.status}`);
    } catch (err) {
      if (i === retries - 1) throw err;
      await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000));
    }
  }
  return "";
}

export function parseJobsFromHtml(html: string): StandardJobResult[] {
  const match = html.match(/window\.jobsList\s*=\s*window\.jobsList\.concat\(\s*(\[\s*\{.*?\}\s*\])\s*\);/s);
  if (!match || !match[1]) return [];

  try {
    const rawJobs: TechTOJob[] = JSON.parse(match[1]);
    return rawJobs.map(j => {
      let salary: string | null = null;
      if (j.min_compensation && j.max_compensation) {
        const curr = (j.compensation_currency || "CAD").toUpperCase();
        const timeframe = j.compensation_time_frame || "annually";
        salary = `$${parseFloat(j.min_compensation).toLocaleString()} - $${parseFloat(j.max_compensation).toLocaleString()} ${curr} ${timeframe}`;
      }

      const company = j.employer?.name || null;
      const location = j.job_location?.name || j.location || null;
      const date = j.posted_at ? j.posted_at.split("T")[0] : null;
      const path = j.job_details_path || `/jobs/${j.id}`;
      const url = path.startsWith("http") ? path : `https://jobs.techto.org${path}`;

      return {
        id: String(j.id),
        title: j.title || "Unknown Title",
        company,
        location,
        date,
        url,
        salary,
        employmentType: j.job_type?.title || null
      };
    });
  } catch {
    return [];
  }
}

export function writeError(message: string, code = "ERROR") {
  console.error(JSON.stringify({ error: message, code }));
  process.exit(1);
}

export function stripHtml(html: string): string {
  return html
    .replace(/<br\s*[\/]?>/gi, "\n")
    .replace(/<\/p>/gi, "\n\n")
    .replace(/<\/li>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .trim();
}
