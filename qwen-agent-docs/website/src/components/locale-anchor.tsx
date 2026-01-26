"use client";

import cn from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

const LOCALES = ["en", "zh", "de", "fr", "ru", "ja", "pt-BR"] as const;
type Locale = (typeof LOCALES)[number];

function LinkArrowIcon(props: React.SVGProps<SVGSVGElement>) {
  // 轻量替代 nextra 内部的 LinkArrowIcon，实现同等视觉语义
  return (
    <svg
      viewBox='0 0 24 24'
      fill='none'
      stroke='currentColor'
      strokeWidth='2'
      strokeLinecap='round'
      strokeLinejoin='round'
      aria-hidden='true'
      focusable='false'
      {...props}
    >
      <path d='M7 17L17 7' />
      <path d='M10 7h7v7' />
    </svg>
  );
}

function isExternalUrl(href: string) {
  return (
    href.startsWith("http://") ||
    href.startsWith("https://") ||
    href.startsWith("//") ||
    href.startsWith("mailto:") ||
    href.startsWith("tel:")
  );
}

function getLocaleFromPathname(pathname: string | null): Locale | null {
  if (!pathname) return null;
  const parts = pathname.split("/").filter(Boolean);
  const maybe = parts[0];
  return (LOCALES as readonly string[]).includes(maybe)
    ? (maybe as Locale)
    : null;
}

function hasLocalePrefix(path: string) {
  const parts = path.split("/").filter(Boolean);
  const maybe = parts[0];
  return (LOCALES as readonly string[]).includes(maybe);
}

export function LocaleAnchor(
  props: React.AnchorHTMLAttributes<HTMLAnchorElement>
) {
  const { href = "", children, ...rest } = props;
  const pathname = usePathname();
  const locale = getLocaleFromPathname(pathname);

  const className = cn(
    "x:focus-visible:nextra-focus",
    "x:text-primary-600 x:underline x:hover:no-underline x:decoration-from-font x:[text-underline-position:from-font]"
  );

  // 锚点：保持原样
  if (typeof href === "string" && href.startsWith("#")) {
    return (
      <a href={href} {...rest} className={className}>
        {children}
      </a>
    );
  }

  // 外链：打开新窗口（对齐 Nextra Anchor 行为）
  if (typeof href === "string" && isExternalUrl(href)) {
    return (
      <a
        href={href}
        target='_blank'
        rel='noreferrer'
        {...rest}
        className={className}
      >
        {children}
        {typeof children === "string" && (
          <>
            &nbsp;
            <LinkArrowIcon
              // based on font-size
              height='1em'
              className='x:inline x:align-baseline x:shrink-0'
            />
          </>
        )}
      </a>
    );
  }

  // 站内绝对路径：自动补齐 /{lang}
  if (typeof href === "string" && href.startsWith("/")) {
    const normalized =
      hasLocalePrefix(href) || !locale ? href : `/${locale}${href}`;
    return (
      <Link href={normalized} {...rest} className={className}>
        {children}
      </Link>
    );
  }

  // 相对路径：解析成站内绝对路径（基于当前 pathname），并尽量保持/补齐 /{lang}
  if (typeof href === "string" && href.length > 0) {
    try {
      // 对于文档站点（trailingSlash: true），pathname 通常是一个“目录路径”（以 "/" 结尾），
      // MDX 的相对链接（./、../）也应当按“目录”语义解析。
      // 这里确保 base 始终是一个目录（以 "/" 结尾），避免把当前目录层级（例如 /en/guide/）
      // 误当成文件路径，从而把相对链接解析到 /en/get_started/... 这类错误位置。
      const basePathnameRaw = pathname || "/";
      const baseDir = basePathnameRaw.endsWith("/")
        ? basePathnameRaw
        : basePathnameRaw.slice(0, basePathnameRaw.lastIndexOf("/") + 1) || "/";

      const base = `http://local${baseDir}`;
      const url = new URL(href, base);
      const absolutePath = `${url.pathname}${url.search}${url.hash}`;
      const normalized =
        hasLocalePrefix(absolutePath) || !locale
          ? absolutePath
          : `/${locale}${absolutePath}`;
      return (
        <Link href={normalized} {...rest} className={className}>
          {children}
        </Link>
      );
    } catch {
      // 解析失败则回退为原生 <a>
    }
  }

  return (
    <a href={href} {...rest} className={className}>
      {children}
    </a>
  );
}
