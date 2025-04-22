# Qwen-Agent

[中文](./README_CN.md) ｜ [English](./README.md) | 日本語

<p align="left">
        日本語ドキュメントメンテナー: <a href="https://github.com/eltociear">Ikko Eltociear Ashimine</a>
</p>

Qwen-Agent は、オープンソースの言語モデル [Qwen](https://github.com/QwenLM/Qwen) のツール使用、プランニング、メモリー機能を利用するためのフレームワークです。
Qwen-Agent をベースに、BrowserQwen という **Chrome ブラウザ拡張機能** を開発しました。これは、以下のような主要機能を備えています:
- 現在のウェブページや PDF 資料について Qwen と話し合う。
- BrowserQwen は、閲覧した Web ページや PDF 資料を、あなたの許可を得て記録します。複数ページの内容を素早く理解したり、閲覧内容をまとめたり、面倒な記述作業を省くことができます。
- 数学の問題解決やデータの視覚化のための **Code Interpreter** を含むプラグインの統合をサポートしています。

# ユースケースデモンストレーション

スクリーンショットの代わりにビデオをご覧になりたい場合は、[ビデオデモンストレーション](#video-demonstration)をご参照ください。

## ワークステーション - エディターモード

**閲覧したウェブページや PDF に基づく長文記事の作成**

<figure>
    <img src="assets/screenshot-writing.png">
</figure>

**リッチテキスト作成を支援するプラグインの呼び出し**

<figure>
    <img src="assets/screenshot-editor-movie.png">
</figure>

## ワークステーション - チャットモード

**複数ウェブページの QA**

<figure >
    <img src="assets/screenshot-multi-web-qa.png">
</figure>

**code interpreter を使ってデータチャートを描く**

<figure>
    <img src="assets/screenshot-ci.png">
</figure>

## ブラウザアシスタント

**Web ページ QA**

<figure>
    <img src="assets/screenshot-web-qa.png">
</figure>

**PDF ドキュメント QA**

<figure>
    <img src="assets/screenshot-pdf-qa.png">
</figure>

# BrowserQwen ユーザーガイド

サポートプラットフォーム: MacOS、Linux、Windows。

## ステップ 1. モデルサービスの展開

***Alibaba Cloud の [DashScope](https://help.aliyun.com/zh/dashscope/developer-reference/quick-start) が提供するモデルサービスを使用している場合、この手順を省略できます。***

ただし、DashScope を使用する代わりに、独自のモデルサービスをデプロイしたい場合は、[Qwen](https://github.com/QwenLM/Qwen) プロジェクトが提供する以下の手順に従って、OpenAI API と互換性のあるモデルサービスをデプロイしてください:

```bash
# 依存関係のインストール。
git clone git@github.com:QwenLM/Qwen.git
cd Qwen
pip install -r requirements.txt
pip install fastapi uvicorn openai "pydantic>=2.3.0" sse_starlette

# c パラメータでモデルのバージョンを指定してモデルサービスを開始する。
# -サーバー名 0.0.0.0 は、他のマシンがあなたのサービスにアクセスすることを許可します。
# --server-name 127.0.0.1 は、モデルをデプロイするマシンがサービスにアクセスすることだけを許可します。
python openai_api.py --server-name 0.0.0.0 --server-port 7905 -c QWen/QWen-14B-Chat
```

現在、-c 引数には GPU メモリ消費量の多い順に以下のモデルを指定できます:

- [`Qwen/Qwen-7B-Chat-Int4`](https://huggingface.co/Qwen/Qwen-7B-Chat-Int4)
- [`Qwen/Qwen-7B-Chat`](https://huggingface.co/Qwen/Qwen-7B-Chat-Int4)
- [`Qwen/Qwen-14B-Chat-Int4`](https://huggingface.co/Qwen/Qwen-14B-Chat-Int4)
- [`Qwen/Qwen-14B-Chat`](https://huggingface.co/Qwen/Qwen-14B-Chat)

7B モデルについては、コードとモデルのウェイトの両方が変更されているため、2023年9月25日以降に Hugging Face の公式リポジトリから取り出したバージョンを使用してください。

## ステップ 2. ローカル データベース サービスの展開

ローカルマシン（Chromeブラウザを開くことができるマシン）に、閲覧履歴と会話履歴を管理するデータベースサービスをデプロイする必要があります。

まだインストールしていない場合は、以下の依存関係をインストールしてください:

```bash
# 依存関係のインストール。
git clone https://github.com/QwenLM/Qwen-Agent.git
cd Qwen-Agent
pip install -r requirements.txt
```

ステップ 1 をスキップして DashScope のモデルサービスを使用する場合は、次のコマンドを実行してください:

```bash
# llm フラグを使用して DashScope 上のモデルを指定し、データベースサービスを開始します。
# llm の値は、リソース消費量の多い順に、以下のいずれかを指定します:
#   - qwen-7b-chat (オープンソースの 7B-Chat モデルと同じ)
#   - qwen-14b-chat (オープンソースの 14B-Chat モデルと同じ)
#   - qwen-turbo
#   - qwen-plus
# YOUR_DASHSCOPE_API_KEY を実際の API キーに置き換える必要があります。
export DASHSCOPE_API_KEY=YOUR_DASHSCOPE_API_KEY
python run_server.py --model_server dashscope --llm qwen-7b-chat --workstation_port 7864
```

ステップ 1 に従って、DashScope の代わりに独自のモデルサービスを使用している場合は、次のコマンドを実行してください:

```bash
# ステップ 1 でデプロイしたモデルサービスを --model_server で指定して、データベースサービスを起動します。
# ステップ 1 のマシンの IP アドレスが 123.45.67.89 の場合、
#     --model_server http://123.45.67.89:7905/v1 を指定することができます
# ステップ 1 とステップ 2 が同じマシン上にある場合、
#     --model_server http://127.0.0.1:7905/v1 を指定することができます
python run_server.py --model_server http://{MODEL_SERVER_IP}:7905/v1 --workstation_port 7864
```

これで[http://127.0.0.1:7864/](http://127.0.0.1:7864/)にアクセスして、ワークステーションのエディターモードとチャットモードを使うことができます。

ワークステーションの使い方のヒントについては、ワークステーションのページの説明を参照するか、[ビデオデモンストレーション](#ビデオデモンストレーション)をご覧ください。

## ステップ 3. ブラウザアシスタントのインストール

BrowserQwen の Chrome 拡張機能をインストールする:

- Chrome ブラウザを開き、アドレスバーに `chrome://extensions/` と入力し、Enter キーを押す。
- 右上の `Developer mode` がオンになっていることを確認し、`Load unpacked` をクリックして、このプロジェクトから `browser_qwen` ディレクトリをアップロードし、有効にする。
- Chrome ブラウザの右上にある拡張機能アイコンをクリックして、BrowserQwen をツールバーに固定します。

Chrome 拡張機能をインストールした後、拡張機能を有効にするにはページを更新する必要があることに注意してください。

Qwen に現在のウェブページの内容を読ませたい場合:

- 画面上の `Add to Qwen's Reading List` ボタンをクリックすると、Qwen がバックグラウンドでページを分析することを許可します。
- ブラウザの右上にある Qwen アイコンをクリックすると、現在のページのコンテンツについて Qwen とのやり取りが始まります。

## ビデオデモンストレーション

BrowserQwen の基本操作については、以下のショーケースのビデオをご覧ください:

- 訪問したウェブページと PDF に基づく長文ライティング [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_write_article_based_on_webpages_and_pdfs.mp4)
- 与えられた情報に基づいて、code interpreter を使ってプロットを描く [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_chat_with_docs_and_code_interpreter.mp4)
- code interpreter を使用したファイルのアップロード、マルチターン会話、データ分析 [video](https://qianwen-res.oss-cn-beijing.aliyuncs.com/assets/qwen_agent/showcase_code_interpreter_multi_turn_chat.mp4)

# 評価ベンチマーク

また、Python コードを記述し、数学的な問題解決やデータ分析、その他の一般的なタスクに Code Interpreter を使用する際のモデルの性能を評価するためのベンチマークもオープンソース化しています。ベンチマークは [benchmark](benchmark/README.md) ディレクトリにあります。現在の評価結果は以下の通りです:

<table>
    <tr>
        <th colspan="4" align="center">生成コードの実行可能率 (%)</th>
    </tr>
    <tr>
        <th align="center">Model</th><th align="center">Math↑</th><th align="center">Visualization↑</th><th align="center">General↑</th>
    </tr>
    <tr>
        <td>GPT-4</td><td align="center">91.9</td><td align="center">85.9</td><td align="center">82.8</td>
    </tr>
    <tr>
        <td>GPT-3.5</td><td align="center">89.2</td><td align="center">65.0</td><td align="center">74.1</td>
    </tr>
    <tr>
        <td>LLaMA2-7B-Chat</td>
        <td align="center">41.9</td>
        <td align="center">33.1</td>
        <td align="center">24.1 </td>
    </tr>
    <tr>
        <td>LLaMA2-13B-Chat</td>
        <td align="center">50.0</td>
        <td align="center">40.5</td>
        <td align="center">48.3 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-7B-Instruct</td>
        <td align="center">85.1</td>
        <td align="center">54.0</td>
        <td align="center">70.7 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-13B-Instruct</td>
        <td align="center">93.2</td>
        <td align="center">55.8</td>
        <td align="center">74.1 </td>
    </tr>
    <tr>
        <td>InternLM-7B-Chat-v1.1</td>
        <td align="center">78.4</td>
        <td align="center">44.2</td>
        <td align="center">62.1 </td>
    </tr>
    <tr>
        <td>InternLM-20B-Chat</td>
        <td align="center">70.3</td>
        <td align="center">44.2</td>
        <td align="center">65.5 </td>
    </tr>
    <tr>
        <td>Qwen-7B-Chat</td>
        <td align="center">82.4</td>
        <td align="center">64.4</td>
        <td align="center">67.2 </td>
    </tr>
    <tr>
        <td>Qwen-14B-Chat</td>
        <td align="center">89.2</td>
        <td align="center">84.1</td>
        <td align="center">65.5</td>
    </tr>
</table>

<table>
    <tr>
        <th colspan="4" align="center">コード実行結果の精度 (%)</th>
    </tr>
    <tr>
        <th align="center">Model</th><th align="center">Math↑</th><th align="center">Visualization-Hard↑</th><th align="center">Visualization-Easy↑</th>
    </tr>
    <tr>
        <td>GPT-4</td><td align="center">82.8</td><td align="center">66.7</td><td align="center">60.8</td>
    </tr>
    <tr>
        <td>GPT-3.5</td><td align="center">47.3</td><td align="center">33.3</td><td align="center">55.7</td>
    </tr>
    <tr>
        <td>LLaMA2-7B-Chat</td>
        <td align="center">3.9</td>
        <td align="center">14.3</td>
        <td align="center">39.2 </td>
    </tr>
    <tr>
        <td>LLaMA2-13B-Chat</td>
        <td align="center">8.3</td>
        <td align="center">8.3</td>
        <td align="center">40.5 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-7B-Instruct</td>
        <td align="center">14.3</td>
        <td align="center">26.2</td>
        <td align="center">60.8 </td>
    </tr>
    <tr>
        <td>CodeLLaMA-13B-Instruct</td>
        <td align="center">28.2</td>
        <td align="center">27.4</td>
        <td align="center">62.0 </td>
    </tr>
    <tr>
        <td>InternLM-7B-Chat-v1.1</td>
        <td align="center">28.5</td>
        <td align="center">4.8</td>
        <td align="center">40.5 </td>
    </tr>
    <tr>
        <td>InternLM-20B-Chat</td>
        <td align="center">34.6</td>
        <td align="center">21.4</td>
        <td align="center">45.6 </td>
    </tr>
    <tr>
        <td>Qwen-7B-Chat</td>
        <td align="center">41.9</td>
        <td align="center">40.5</td>
        <td align="center">54.4 </td>
    </tr>
    <tr>
        <td>Qwen-14B-Chat</td>
        <td align="center">58.4</td>
        <td align="center">53.6</td>
        <td align="center">59.5</td>
    </tr>
</table>

Qwen-7B-Chat は、2023年9月25日以降に更新されたバージョンを指します。

# 免責事項

このプロジェクトは正式な製品ではなく、Qwen シリーズモデルの能力を強調する概念実証プロジェクトです。
