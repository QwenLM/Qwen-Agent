"use client";
import { useEffect } from "react";

export const FontLoader = () => {
  useEffect(() => {
    // 根据环境设置字体路径前缀
    const isProduction = process.env.NODE_ENV === "production";
    const fontPrefix = isProduction ? "/Qwen-Agent" : "";

    // 创建字体样式
    const fontStyles = `
      /* Local Monoton Font */
      @font-face {
        font-family: "Monoton";
        src: url("${fontPrefix}/fonts/Monoton/Monoton-Regular.ttf") format("truetype");
        font-weight: normal;
        font-style: normal;
        font-display: swap;
      }

      /* Local Orbitron Font - Multiple Weights */
      @font-face {
        font-family: "Orbitron";
        src: url("${fontPrefix}/fonts/Orbitron/Orbitron-VariableFont_wght.ttf") format("truetype-variations");
        font-weight: 400 900;
        font-style: normal;
        font-display: swap;
      }

      @font-face {
        font-family: "Orbitron";
        src: url("${fontPrefix}/fonts/Orbitron/static/Orbitron-Regular.ttf") format("truetype");
        font-weight: 400;
        font-style: normal;
        font-display: swap;
      }

      @font-face {
        font-family: "Orbitron";
        src: url("${fontPrefix}/fonts/Orbitron/static/Orbitron-Medium.ttf") format("truetype");
        font-weight: 500;
        font-style: normal;
        font-display: swap;
      }

      @font-face {
        font-family: "Orbitron";
        src: url("${fontPrefix}/fonts/Orbitron/static/Orbitron-SemiBold.ttf") format("truetype");
        font-weight: 600;
        font-style: normal;
        font-display: swap;
      }

      @font-face {
        font-family: "Orbitron";
        src: url("${fontPrefix}/fonts/Orbitron/static/Orbitron-Bold.ttf") format("truetype");
        font-weight: 700;
        font-style: normal;
        font-display: swap;
      }

      @font-face {
        font-family: "Orbitron";
        src: url("${fontPrefix}/fonts/Orbitron/static/Orbitron-ExtraBold.ttf") format("truetype");
        font-weight: 800;
        font-style: normal;
        font-display: swap;
      }

      @font-face {
        font-family: "Orbitron";
        src: url("${fontPrefix}/fonts/Orbitron/static/Orbitron-Black.ttf") format("truetype");
        font-weight: 900;
        font-style: normal;
        font-display: swap;
      }
    `;

    // 创建 style 元素并添加到 head
    const style = document.createElement("style");
    style.textContent = fontStyles;
    style.id = "dynamic-fonts";
    document.head.appendChild(style);

    // 清理函数
    return () => {
      const existingStyle = document.getElementById("dynamic-fonts");
      if (existingStyle) {
        existingStyle.remove();
      }
    };
  }, []);

  return null; // 这个组件不渲染任何内容
};
