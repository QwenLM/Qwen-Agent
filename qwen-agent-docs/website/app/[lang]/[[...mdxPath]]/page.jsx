import { generateStaticParamsFor, importPage } from "nextra/pages";
import { useMDXComponents as getMDXComponents } from "../../../mdx-components";
import "./index.css";

export const generateStaticParams = generateStaticParamsFor("mdxPath");

export async function generateMetadata(props) {
  const params = await props.params;
  // 当访问根路径时，mdxPath 为 undefined，需要转换为空数组
  const mdxPath = params.mdxPath || [];
  const lang = params.lang || "en";
  const { metadata } = await importPage(mdxPath, lang);
  return metadata;
}

const Wrapper = getMDXComponents().wrapper;

const Page = async (props) => {
  const params = await props.params;
  // 当访问根路径时，mdxPath 为 undefined，需要转换为空数组
  const mdxPath = params.mdxPath || [];
  const lang = params.lang || "en";
  const result = await importPage(mdxPath, lang);
  const { default: MDXContent, toc, metadata } = result;

  return (
    <Wrapper toc={toc} metadata={metadata}>
      <MDXContent {...props} params={params} />
    </Wrapper>
  );
};

export default Page;
