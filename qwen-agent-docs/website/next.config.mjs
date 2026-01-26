import nextra from "nextra";

const withNextra = nextra({
  latex: true,
  search: {
    codeblocks: false,
  },
  contentDirBasePath: "/",
  defaultShowCopyCode: true,
  // 自动为侧边栏和导航链接添加语言前缀
  unstable_shouldAddLocaleToLinks: true,
});

const isProduction = process.env.NODE_ENV === "production";
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
  // App Router 不使用 next.config 的 i18n，通过文件夹结构和路由来处理
};

// 仅在生产构建时启用静态导出和 basePath
if (isProduction) {
  nextConfig.output = "export";
  nextConfig.basePath = basePath;
  nextConfig.assetPrefix = basePath;
}

export default withNextra(nextConfig);