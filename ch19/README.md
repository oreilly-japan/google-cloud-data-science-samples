# Gen AI Evaluation ServiceによるLLMとAIエージェントの品質評価（サンプルコード）

第Ⅱ部 8章のサンプルコードです。
前提条件（API の有効化・IAM ロール）や各手順の詳細は書籍 第Ⅱ部 8章を参照してください。

## ファイル

| ファイル | 内容 |
| --- | --- |
| `ch19.ipynb` | 本章のハンズオン用ノートブック（8.6〜8.9） |
| `view_batch_eval_results.py` | バッチ評価（8.8節）の結果を Cloud Storage から読み込んで表示するスクリプト（同じ内容のセルをノートブックにも収録） |

## 実行方法

1. 評価結果の保存先となる Cloud Storage バケットを作成します（書籍 8.6節）。

    ```zsh
    gcloud storage buckets create gs://YOUR_PROJECT_ID-genai-eval --location=us-central1
    ```

2. Colab Enterprise で `ch19.ipynb` を開きます。
3. 上のセルから順に実行します。最初のセルの `pip install` が完了したら、**ランタイムを再起動**してから続きを実行してください。

プロジェクト ID は環境変数 `GOOGLE_CLOUD_PROJECT` から読み取ります（Colab Enterprise では通常自動設定されています）。リージョンは Gen AI Evaluation Service が利用可能な `us-central1` に固定しています。

## クリーンアップ

ハンズオンが終わったら、ノートブック末尾のクリーンアップセルを必ず実行してください（Agent Engine リソースと Cloud Storage 上の評価結果が削除されます）。バケット自体を削除する場合は以下を実行します。

```zsh
gcloud storage rm -r gs://YOUR_PROJECT_ID-genai-eval
```
