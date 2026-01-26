import { redirect } from 'next/navigation';

export default function HomePage() {
  // 直接重定向到英文文档首页
  redirect('/en/');
}
