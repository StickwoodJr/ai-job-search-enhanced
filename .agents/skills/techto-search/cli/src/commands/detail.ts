import { fetchWithBackoff, writeError, stripHtml } from "../helpers";

export async function handleDetail(target: string, format = "json") {
  if (!target || target.trim() === "") {
    writeError("Job ID or URL is required for detail lookup.", "INVALID_ARGUMENT");
  }

  let detailUrl = target.trim();
  if (!detailUrl.startsWith("http")) {
    detailUrl = `https://jobs.techto.org/jobs/${detailUrl}`;
  }

  try {
    const html = await fetchWithBackoff(detailUrl);
    if (!html) {
      writeError(`Job posting not found at ${detailUrl}`, "NOT_FOUND");
    }

    const titleMatch = html.match(/<h1[^>]*>(.*?)<\/h1>/s);
    const title = titleMatch ? stripHtml(titleMatch[1]) : "Job Detail";

    const companyMatch = html.match(/<a[^>]*class=\"[^\"]*employer[^\"]*\"[^>]*>(.*?)<\/a>/s) || html.match(/<h2[^>]*>(.*?)<\/h2>/s);
    const company = companyMatch ? stripHtml(companyMatch[1]) : null;

    const descMatch = html.match(/<div[^>]*class=\"[^\"]*(?:job-description|description)[^\"]*\"[^>]*>(.*?)<\/div>/s) ||
                      html.match(/<article[^>]*>(.*?)<\/article>/s);
    const description = descMatch ? stripHtml(descMatch[1]) : stripHtml(html.slice(0, 2000));

    if (format === "plain") {
      console.log(`=== ${title} ===`);
      if (company) console.log(`Company: ${company}`);
      console.log(`URL: ${detailUrl}\n`);
      console.log(description);
    } else {
      console.log(JSON.stringify({
        url: detailUrl,
        title,
        company,
        description
      }, null, 2));
    }
  } catch (err: any) {
    writeError(`Failed to fetch job detail: ${err.message}`, "FETCH_ERROR");
  }
}
