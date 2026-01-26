import { generateStaticParamsFor, importPage } from "nextra/pages";
import { useMDXComponents as getMDXComponents } from "../../../mdx-components";
import "./index.css";

// 手动过滤 Nextra 生成的参数，移除 mdxPath 开头的语言前缀
const nextraGenerateParams = generateStaticParamsFor("mdxPath", "lang");

export async function generateStaticParams() {
  const params = await nextraGenerateParams();

  // 过滤并修正参数：如果 mdxPath 以 "en" 开头，说明是重复的语言前缀，需要移除
  const filtered = params
    .map(p => {
      if (p.mdxPath && p.mdxPath.length > 0 && p.mdxPath[0] === "en") {
        return { ...p, mdxPath: p.mdxPath.slice(1) };
      }
      return p;
    })
    // 去重（因为移除 en 后可能有重复的路径）
    .filter((p, index, arr) => {
      const key = JSON.stringify(p.mdxPath || []);
      return arr.findIndex(x => JSON.stringify(x.mdxPath || []) === key) === index;
    });

  return filtered;
}

export async function generateMetadata(props) {
  const params = await props.params;
  // 当访问根路径时，mdxPath 为 undefined，需要转换为空数组
  const mdxPath = params.mdxPath || [];
  const lang = params.lang || "en";
  // importPage 需要完整路径（包含语言前缀），因为 Nextra 内部是基于 content/en/... 结构来查找的
  const fullMdxPath = [lang, ...mdxPath];
  const { metadata } = await importPage(fullMdxPath);
  return metadata;
}

const Wrapper = getMDXComponents().wrapper;

const Page = async (props) => {
  const params = await props.params;
  // 当访问根路径时，mdxPath 为 undefined，需要转换为空数组
  const mdxPath = params.mdxPath || [];
  const lang = params.lang || "en";
  // importPage 需要完整路径（包含语言前缀）
  const fullMdxPath = [lang, ...mdxPath];
  const result = await importPage(fullMdxPath);
  const { default: MDXContent, toc, metadata } = result;

  return (
    <Wrapper toc={toc} metadata={metadata}>
      <MDXContent {...props} params={params} />
    </Wrapper>
  );
};

export default Page;
