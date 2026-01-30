import type { MetadataRoute } from "next";
import fs from "node:fs";
import path from "node:path";

const LOCALES = ["en", "zh"] as const;

function getSiteUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL;
  if (explicit) return explicit.replace(/\/$/, "");

  const ghRepo = process.env.GITHUB_REPOSITORY; // e.g. owner/repo
  if (ghRepo && ghRepo.includes("/")) {
    const [owner, repo] = ghRepo.split("/");
    if (owner && repo) return `https://${owner}.github.io/${repo}`;
  }

  return "https://qwenlm.github.io/Qwen-Agent";
}

function walkDir(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const results: string[] = [];

  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;

    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkDir(full));
      continue;
    }

    if (!entry.isFile()) continue;
    if (!entry.name.toLowerCase().endsWith(".md")) continue;

    results.push(full);
  }

  return results;
}

function toDocPath(locale: string, markdownFile: string): string {
  const localeRoot = path.join(process.cwd(), "content", locale);
  const rel = path
    .relative(localeRoot, markdownFile)
    .replace(/\\/g, "/")
    .replace(/\.md$/i, "");

  // index.md maps to directory root
  if (rel === "index") return `/${locale}/`;
  if (rel.endsWith("/index"))
    return `/${locale}/${rel.slice(0, -"/index".length)}/`;

  return `/${locale}/${rel}/`;
}

function safeExists(p: string): boolean {
  try {
    fs.accessSync(p, fs.constants.R_OK);
    return true;
  } catch {
    return false;
  }
}

export default function sitemap(): MetadataRoute.Sitemap {
  const siteUrl = getSiteUrl();
  const now = new Date();

  const items: MetadataRoute.Sitemap = [
    {
      url: `${siteUrl}/`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1,
    },
  ];

  for (const locale of LOCALES) {
    const localeDir = path.join(process.cwd(), "content", locale);
    if (!safeExists(localeDir)) continue;

    const markdownFiles = walkDir(localeDir);
    for (const f of markdownFiles) {
      const docPath = toDocPath(locale, f);
      items.push({
        url: `${siteUrl}${docPath}`,
        lastModified: now,
        changeFrequency: "weekly",
        priority: docPath === `/${locale}/` ? 0.8 : 0.6,
      });
    }
  }

  // Deduplicate (can happen if content has redundant index files)
  const seen = new Set<string>();
  return items.filter((i) => {
    if (seen.has(i.url)) return false;
    seen.add(i.url);
    return true;
  });
}
