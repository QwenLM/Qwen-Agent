"use client";

import React from "react";

interface ModelScore {
  model: string;
  icon: string;
  isThinking: boolean;
  avgAcc: number;
  travel: {
    csScore: number;
    psScore: number;
    compScore: number;
    caseAcc: number;
  };
  shopping: {
    matchScore: number;
    caseAcc: number;
  };
}

// All Models Data
const allModels: ModelScore[] = [
  // Thinking Models
  { model: "OpenAI/GPT-5.2-high", icon: "/icons/icon_openai.png", isThinking: true, avgAcc: 44.6, travel: { csScore: 88.5, psScore: 83.3, compScore: 85.8, caseAcc: 35.0 }, shopping: { matchScore: 84.8, caseAcc: 54.2 } },
  { model: "Anthropic/Claude-4.5-Opus (w/ thinking)", icon: "/icons/icon_anthropic.png", isThinking: true, avgAcc: 33.9, travel: { csScore: 79.3, psScore: 70.9, compScore: 75.1, caseAcc: 22.7 }, shopping: { matchScore: 80.0, caseAcc: 45.0 } },
  { model: "OpenAI/GPT-5-high", icon: "/icons/icon_openai.png", isThinking: true, avgAcc: 31.6, travel: { csScore: 78.7, psScore: 65.9, compScore: 72.3, caseAcc: 18.9 }, shopping: { matchScore: 80.4, caseAcc: 44.2 } },
  { model: "Google/Gemini-3-Flash-Preview", icon: "/icons/ico_gemini.png", isThinking: true, avgAcc: 28.8, travel: { csScore: 67.1, psScore: 57.7, compScore: 62.4, caseAcc: 5.9 }, shopping: { matchScore: 80.6, caseAcc: 51.7 } },
  { model: "Alibaba/Qwen3-Max (w/ thinking)", icon: "/icons/icon_qwen.png", isThinking: true, avgAcc: 28.7, travel: { csScore: 64.0, psScore: 61.7, compScore: 62.8, caseAcc: 13.8 }, shopping: { matchScore: 82.6, caseAcc: 43.5 } },
  { model: "Anthropic/Claude-4.5-Sonnet (w/ thinking)", icon: "/icons/icon_anthropic.png", isThinking: true, avgAcc: 25.5, travel: { csScore: 65.2, psScore: 58.4, compScore: 61.8, caseAcc: 7.6 }, shopping: { matchScore: 80.0, caseAcc: 43.3 } },
  { model: "OpenAI/o3", icon: "/icons/icon_openai.png", isThinking: true, avgAcc: 24.9, travel: { csScore: 76.5, psScore: 55.6, compScore: 66.1, caseAcc: 11.3 }, shopping: { matchScore: 76.9, caseAcc: 38.5 } },
  { model: "Google/Gemini-3-Pro-Preview", icon: "/icons/ico_gemini.png", isThinking: true, avgAcc: 23.2, travel: { csScore: 58.4, psScore: 25.1, compScore: 41.8, caseAcc: 0.7 }, shopping: { matchScore: 78.0, caseAcc: 45.8 } },
  { model: "DeepSeek-AI/DeepSeek-V3.2 (w/ thinking)", icon: "/icons/icon_dpsk.png", isThinking: true, avgAcc: 21.6, travel: { csScore: 47.4, psScore: 35.0, compScore: 41.2, caseAcc: 0.7 }, shopping: { matchScore: 78.8, caseAcc: 42.5 } },
  { model: "ByteDance/Seed-1.8-high", icon: "/icons/icon_seed.png", isThinking: true, avgAcc: 20.4, travel: { csScore: 43.6, psScore: 56.7, compScore: 50.1, caseAcc: 0.0 }, shopping: { matchScore: 77.5, caseAcc: 40.8 } },
  { model: "xAI/Grok-4.1-fast (reasoning)", icon: "/icons/icon_x.png", isThinking: true, avgAcc: 17.2, travel: { csScore: 57.1, psScore: 37.7, compScore: 47.4, caseAcc: 2.7 }, shopping: { matchScore: 74.0, caseAcc: 31.7 } },
  { model: "Alibaba/Qwen-Plus (w/ thinking)", icon: "/icons/icon_qwen.png", isThinking: true, avgAcc: 17.1, travel: { csScore: 35.4, psScore: 22.4, compScore: 28.9, caseAcc: 0.0 }, shopping: { matchScore: 73.3, caseAcc: 34.1 } },
  { model: "Google/Gemini-2.5-Pro", icon: "/icons/ico_gemini.png", isThinking: true, avgAcc: 17.0, travel: { csScore: 62.3, psScore: 42.0, compScore: 52.2, caseAcc: 3.2 }, shopping: { matchScore: 69.1, caseAcc: 30.8 } },
  { model: "Z.ai/GLM-4.7 (w/ thinking)", icon: "/icons/icon_glm.png", isThinking: true, avgAcc: 14.0, travel: { csScore: 44.0, psScore: 44.6, compScore: 44.3, caseAcc: 0.4 }, shopping: { matchScore: 72.5, caseAcc: 27.5 } },
  { model: "OpenAI/o4-mini", icon: "/icons/icon_openai.png", isThinking: true, avgAcc: 12.4, travel: { csScore: 58.0, psScore: 36.6, compScore: 47.2, caseAcc: 3.0 }, shopping: { matchScore: 69.1, caseAcc: 21.7 } },
  { model: "Moonshot-AI/Kimi-K2-thinking", icon: "/icons/icon_kimi.png", isThinking: true, avgAcc: 12.1, travel: { csScore: 45.2, psScore: 32.5, compScore: 38.9, caseAcc: 0.0 }, shopping: { matchScore: 65.8, caseAcc: 24.2 } },
  // Non-thinking Models
  { model: "Anthropic/Claude-4.5-Opus (w/o thinking)", icon: "/icons/icon_anthropic.png", isThinking: false, avgAcc: 26.3, travel: { csScore: 67.5, psScore: 58.8, compScore: 63.1, caseAcc: 6.7 }, shopping: { matchScore: 82.2, caseAcc: 45.8 } },
  { model: "Anthropic/Claude-4.5-Sonnet (w/o thinking)", icon: "/icons/icon_anthropic.png", isThinking: false, avgAcc: 17.2, travel: { csScore: 53.4, psScore: 42.8, compScore: 48.1, caseAcc: 1.1 }, shopping: { matchScore: 75.8, caseAcc: 33.3 } },
  { model: "Alibaba/Qwen3-Max (w/o thinking)", icon: "/icons/icon_qwen.png", isThinking: false, avgAcc: 12.8, travel: { csScore: 36.7, psScore: 30.7, compScore: 31.8, caseAcc: 0.8 }, shopping: { matchScore: 70.2, caseAcc: 24.7 } },
  { model: "ByteDance/Seed-1.8-minimal", icon: "/icons/icon_seed.png", isThinking: false, avgAcc: 11.3, travel: { csScore: 43.0, psScore: 47.5, compScore: 45.3, caseAcc: 0.0 }, shopping: { matchScore: 68.1, caseAcc: 22.5 } },
  { model: "Alibaba/Qwen-Plus (w/o thinking)", icon: "/icons/icon_qwen.png", isThinking: false, avgAcc: 7.5, travel: { csScore: 37.3, psScore: 13.0, compScore: 25.1, caseAcc: 0.0 }, shopping: { matchScore: 63.9, caseAcc: 15.0 } },
  { model: "Z.ai/GLM-4.7 (w/o thinking)", icon: "/icons/icon_glm.png", isThinking: false, avgAcc: 7.1, travel: { csScore: 38.9, psScore: 22.5, compScore: 30.7, caseAcc: 0.0 }, shopping: { matchScore: 61.2, caseAcc: 14.2 } },
  { model: "DeepSeek-AI/DeepSeek-V3.2 (w/o thinking)", icon: "/icons/icon_dpsk.png", isThinking: false, avgAcc: 5.3, travel: { csScore: 37.4, psScore: 12.1, compScore: 24.7, caseAcc: 0.0 }, shopping: { matchScore: 58.3, caseAcc: 10.6 } },
  { model: "OpenAI/GPT-5.2-none", icon: "/icons/icon_openai.png", isThinking: false, avgAcc: 4.5, travel: { csScore: 54.3, psScore: 29.9, compScore: 42.1, caseAcc: 0.4 }, shopping: { matchScore: 58.6, caseAcc: 8.6 } },
  { model: "xAI/Grok-4.1-fast (non-reasoning)", icon: "/icons/icon_x.png", isThinking: false, avgAcc: 3.0, travel: { csScore: 39.6, psScore: 19.7, compScore: 29.6, caseAcc: 0.0 }, shopping: { matchScore: 50.1, caseAcc: 5.9 } },
];

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-yellow-400 text-white text-sm font-bold shadow">
        1
      </span>
    );
  }
  if (rank === 2) {
    return (
      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-gray-400 text-white text-sm font-bold shadow">
        2
      </span>
    );
  }
  if (rank === 3) {
    return (
      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-600 text-white text-sm font-bold shadow">
        3
      </span>
    );
  }
  return (
    <span className="text-gray-600 dark:text-gray-400 font-medium text-sm">
      {rank}
    </span>
  );
}

// Icon component that handles both image paths and emoji
function ModelIcon({ icon }: { icon: string }) {
  // Check if icon is an image path
  if (icon.startsWith('./') || icon.startsWith('/')) {
    return (
      <img 
        src={icon} 
        alt="Model icon" 
        className="w-5 h-5 object-contain"
      />
    );
  }
  // Otherwise, treat as emoji
  return <span className="text-base">{icon}</span>;
}

// Sort models by avgAcc
function sortByScore(models: ModelScore[]): ModelScore[] {
  return [...models].sort((a, b) => b.avgAcc - a.avgAcc);
}

// Find best values for highlighting
function findBestValues(models: ModelScore[]) {
  const best = {
    avgAcc: 0,
    travel: { csScore: 0, psScore: 0, compScore: 0, caseAcc: 0 },
    shopping: { matchScore: 0, caseAcc: 0 },
  };
  models.forEach((m) => {
    if (m.avgAcc > best.avgAcc) best.avgAcc = m.avgAcc;
    if (m.travel.csScore > best.travel.csScore) best.travel.csScore = m.travel.csScore;
    if (m.travel.psScore > best.travel.psScore) best.travel.psScore = m.travel.psScore;
    if (m.travel.compScore > best.travel.compScore) best.travel.compScore = m.travel.compScore;
    if (m.travel.caseAcc > best.travel.caseAcc) best.travel.caseAcc = m.travel.caseAcc;
    if (m.shopping.matchScore > best.shopping.matchScore) best.shopping.matchScore = m.shopping.matchScore;
    if (m.shopping.caseAcc > best.shopping.caseAcc) best.shopping.caseAcc = m.shopping.caseAcc;
  });
  return best;
}

function ScoreCell({ value, isBest }: { value: number; isBest: boolean }) {
  return (
    <td className={`px-2 py-2.5 text-center text-sm ${isBest ? "font-bold text-gray-900 dark:text-white" : "text-gray-600 dark:text-gray-400"}`}>
      {value.toFixed(1)}
    </td>
  );
}

export function Leaderboard() {
  const sortedModels = sortByScore(allModels);
  const best = findBestValues(allModels);

  return (
    <div className="my-8">
      {/* Title */}
      <h2 className="text-center text-2xl font-bold mb-2">
        🏆 Leaderboard 🏆
      </h2>
      
      {/* Subtitle */}
      <p className="text-center text-sm text-gray-500 dark:text-gray-400 mb-6">
        Comprehensive evaluation results on DeepPlanning. Results are averaged over four runs. <strong>Bold</strong> indicates the best result.
      </p>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <table className="w-full text-sm border-collapse bg-white dark:bg-gray-900">
          <thead>
            {/* Header Row 1 - Group Headers */}
            <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              <th className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-300" rowSpan={2}>
                Rank
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-300" rowSpan={2}>
                Model
              </th>
              <th className="px-2 py-2 text-center font-semibold text-gray-700 dark:text-gray-300" rowSpan={2}>
                Avg Acc.
              </th>
              <th className="px-2 py-2 text-center font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-600" colSpan={4}>
                Travel Planning
              </th>
              <th className="px-2 py-2 text-center font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-600 whitespace-nowrap" colSpan={2}>
                Shopping Planning
              </th>
            </tr>
            {/* Header Row 2 - Column Headers */}
            <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-xs">
              <th className="px-2 py-2 text-center text-gray-500 dark:text-gray-400 font-medium">CS<br />Score</th>
              <th className="px-2 py-2 text-center text-gray-500 dark:text-gray-400 font-medium">PS<br />Score</th>
              <th className="px-2 py-2 text-center text-gray-500 dark:text-gray-400 font-medium">Comp<br />Score</th>
              <th className="px-2 py-2 text-center text-gray-500 dark:text-gray-400 font-medium">Case<br />Acc.</th>
              <th className="px-2 py-2 text-center text-gray-500 dark:text-gray-400 font-medium">Match<br />Score</th>
              <th className="px-2 py-2 text-center text-gray-500 dark:text-gray-400 font-medium">Case<br />Acc.</th>
            </tr>
          </thead>
          <tbody>
            {sortedModels.map((item, index) => (
              <tr key={item.model} className="border-b border-gray-100 dark:border-gray-800 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-colors">
                <td className="px-4 py-2.5 text-center">
                  <RankBadge rank={index + 1} />
                </td>
                <td className="px-4 py-2.5 text-left whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <ModelIcon icon={item.icon} />
                    <span className="font-medium text-gray-800 dark:text-gray-200">{item.model}</span>
                  </div>
                </td>
                <ScoreCell value={item.avgAcc} isBest={item.avgAcc === best.avgAcc} />
                <ScoreCell value={item.travel.csScore} isBest={item.travel.csScore === best.travel.csScore} />
                <ScoreCell value={item.travel.psScore} isBest={item.travel.psScore === best.travel.psScore} />
                <ScoreCell value={item.travel.compScore} isBest={item.travel.compScore === best.travel.compScore} />
                <ScoreCell value={item.travel.caseAcc} isBest={item.travel.caseAcc === best.travel.caseAcc} />
                <ScoreCell value={item.shopping.matchScore} isBest={item.shopping.matchScore === best.shopping.matchScore} />
                <ScoreCell value={item.shopping.caseAcc} isBest={item.shopping.caseAcc === best.shopping.caseAcc} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <p className="mt-3 text-xs text-gray-500 dark:text-gray-400 text-center">
        CS Score = Commonsense Score | PS Score = Personalized Score | Comp Score = Composite Score | Case Acc. = Case Accuracy | Match Score = Match Score. <strong>Bold</strong> values indicate best performance per category.
      </p>
    </div>
  );
}

export default Leaderboard;
