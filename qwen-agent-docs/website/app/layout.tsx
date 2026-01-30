/* eslint-env node */

import type { Metadata } from "next";
import { Head } from "nextra/components";
import type { FC, ReactNode } from "react";
import "nextra-theme-docs/style.css";
import { FontLoader } from "../src/components/font-loader";

const SITE_NAME = "Qwen Agent";
const DEFAULT_TITLE = "Qwen Agent: AI Agent Framework Documentation";
const DESCRIPTION =
  "Documentation for Qwen Agent: an open-source AI agent framework. Learn installation, agent usage, tool integration, LLM configuration, and best practices.";

const KEYWORDS = [
  "Qwen Agent",
  "Qwen",
  "AI agent",
  "AI agent framework",
  "documentation",
  "open source",
  "Next.js",
  "Nextra",
  "LLM",
  "Large Language Model",
  "tool integration",
  "Alibaba",
  "阿里巴巴",
  "通义千问",
  "千问",
  "大模型",
];

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

export const metadata: Metadata = {
  applicationName: SITE_NAME,
  title: {
    default: DEFAULT_TITLE,
    template: `%s | ${SITE_NAME}`,
  },
  description: DESCRIPTION,
  keywords: KEYWORDS,
  metadataBase: new URL(getSiteUrl()),
  alternates: {
    canonical: "/",
    languages: {
      en: "/en/",
      zh: "/zh/",
    },
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: DEFAULT_TITLE,
    description: DESCRIPTION,
    url: "/",
  },
  twitter: {
    site: "@qwenLLM",
    card: "summary",
    title: DEFAULT_TITLE,
    description: DESCRIPTION,
  },
  appleWebApp: {
    title: "Qwen Agent",
  },
  icons: {
    icon: [{ url: "/favicon.png", type: "image/png" }],
    shortcut: ["/favicon.png"],
    apple: [{ url: "/favicon.png", type: "image/png" }],
  },
  manifest: "/site.webmanifest",
  other: {
    "msapplication-TileColor": "#fff",
  },
};

type LayoutProps = Readonly<{
  children: ReactNode;
}>;

const RootLayout: FC<LayoutProps> = ({ children }) => {
  return (
    <html lang='en' suppressHydrationWarning>
      <Head
        // backgroundColor={{
        //   dark: "rgb(15,23,42)",
        //   light: "rgb(254, 252, 232)",
        // }}
        color={{
          hue: { dark: 248, light: 248 },
          saturation: { dark: 74, light: 74 },
        }}
      />
      <body>
        <FontLoader />
        {children}
      </body>
    </html>
  );
};

export default RootLayout;
