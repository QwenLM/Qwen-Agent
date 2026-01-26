/* eslint-env node */

import { Layout, Navbar } from "nextra-theme-docs";
import { getPageMap } from "nextra/page-map";
import { notFound } from "next/navigation";
import type { FC, ReactNode } from "react";

type LayoutProps = Readonly<{
  children: ReactNode;
  params: Promise<{
    lang: string;
  }>;
}>;

// 支持的语言列表
const SUPPORTED_LOCALES = ['en'];

// 为静态导出生成所有语言的参数
export async function generateStaticParams() {
  return SUPPORTED_LOCALES.map(lang => ({ lang }));
}

const LanguageLayout: FC<LayoutProps> = async ({ children, params }) => {
  const { lang } = await params;
  
  // 验证语言参数是否有效
  if (!SUPPORTED_LOCALES.includes(lang)) {
    notFound();
  }

  const sourcePageMap = await getPageMap(`/${lang}`);

  const navbar = (
    <Navbar
      logo={
        <span
          className='ms-2 select-none font-extrabold flex items-center'
          title='Qwen Agent: AI Agent Framework'
        >
          <img
            src='/favicon.png'
            alt='Qwen Agent'
            width={32}
            height={32}
            className='inline-block align-middle mr-2'
            style={{ verticalAlign: "middle" }}
          />
          <span className='text-[1.3rem] font-normal align-middle mr-1 max-md:hidden'>
            Qwen
          </span>
          <span className='text-[1.3rem] font-normal align-middle max-md:hidden'>
            Agent
          </span>
        </span>
      }
      projectLink='https://github.com/QwenLM/Qwen-Agent'
    />
  );

  return (
    <Layout
      navbar={navbar}
      footer={null}
      docsRepositoryBase='https://github.com/QwenLM/Qwen-Agent/blob/main/qwen-agent-docs/website/content'
      search={false}
      sidebar={{ defaultMenuCollapseLevel: 9999 }}
      pageMap={sourcePageMap}
      nextThemes={{ defaultTheme: "light" }}
    >
      {children}
    </Layout>
  );
};

export default LanguageLayout;
