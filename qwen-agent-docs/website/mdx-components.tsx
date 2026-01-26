import React from "react";
import { useMDXComponents as getDocsMDXComponents } from "nextra-theme-docs";
import { Pre, withIcons } from "nextra/components";
import { GitHubIcon } from "nextra/icons";
import type { UseMDXComponents } from "nextra/mdx-components";
import type { ImgHTMLAttributes } from "react";
import { LocaleAnchor } from "./src/components/locale-anchor";
import { Leaderboard } from "./src/components/leaderboard";

// 自定义 img 组件，动态替换路径
const CustomImg = (props: ImgHTMLAttributes<HTMLImageElement>) => {
  const { src, ...rest } = props;
  // 根据环境设置资源前缀
  const isProduction = process.env.NODE_ENV === "production";
  const assetPrefix = isProduction ? "/Qwen-Agent" : "";
  
  // 处理src可能是字符串或对象的情况
  let adjustedSrc = src;
  if (typeof src === 'string') {
    // 将 ../assets/ 替换为带前缀的 /assets/
    adjustedSrc = src.replace(/\.\.\/assets\//, `${assetPrefix}/assets/`);
  } else if (src && typeof src === 'object' && 'src' in src) {
    // 如果src是导入的图片对象（Next.js Image import）
    adjustedSrc = (src as any).src;
  }
  
  return <img src={adjustedSrc} {...rest} />;
};

const docsComponents = getDocsMDXComponents({
  pre: withIcons(Pre, { js: GitHubIcon }),
});

export const useMDXComponents: UseMDXComponents<any> = (components = {}) => ({
  ...docsComponents,
  a: LocaleAnchor,
  img: CustomImg,
  Leaderboard,
  ...components,
});
