import nextra from "nextra";

const isProduction = process.env.NODE_ENV === "production";

const withNextra = nextra({
  latex: true,
  search: {
    codeblocks: false,
  },
  contentDirBasePath: "/",
  defaultShowCopyCode: true,
  // 在开发环境自动为链接添加语言前缀，生产环境禁用（避免与静态导出冲突）
  unstable_shouldAddLocaleToLinks: !isProduction,
});

const repo = "Qwen-Agent";
const basePath = isProduction ? `/${repo}` : "";

const nextConfig = {
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  // Nextra 需要 i18n 配置来知道支持的语言
  i18n: {
    locales: ["en"],
    defaultLocale: "en",
  },
};

// 仅在生产构建时启用静态导出和 basePath
if (isProduction) {
  nextConfig.output = "export";
  nextConfig.basePath = basePath;
  nextConfig.assetPrefix = basePath;
  // 生产环境下移除 i18n（与 output: export 不兼容）
  delete nextConfig.i18n;
}

export default withNextra(nextConfig);
