"""バッチ評価（batch_evaluate）の結果をCloud Storageから読み込んで表示するスクリプト。

第Ⅱ部8章「8.8 単一出力に対しての評価 > バッチ評価 > 結果の取得と表示」で使用します。
ch19.ipynb のバッチ評価ジョブが完了したあとに、このファイルの内容をノートブックの
セルに貼り付けて実行してください。

`GCS_DEST`（バッチ評価の出力先）と `PROJECT_ID` は、ノートブックの前のセルで定義済みの
値をそのまま利用します。単体で実行する場合は、以下の2行のコメントアウトを外してください。

    # PROJECT_ID = "your-project-id"
    # GCS_DEST = f"gs://{PROJECT_ID}-genai-eval/single-generation-eval/batch/"
"""

import json

import gcsfs
import pandas as pd
from IPython.display import display


def load_eval_results(gcs_dest: str, project_id: str):
    """GCS から最新の評価結果ファイルを読み込む。"""
    fs = gcsfs.GCSFileSystem(project=project_id)
    gcs_path = gcs_dest.replace("gs://", "")
    all_files = fs.find(gcs_path)
    agg_file = sorted(f for f in all_files if f.endswith("/aggregation_results.jsonl"))[-1]
    eval_file = sorted(f for f in all_files if f.endswith("/evaluation_results.jsonl"))[-1]
    return (
        pd.read_json(f"gs://{agg_file}", lines=True),
        pd.read_json(f"gs://{eval_file}", lines=True),
    )


def parse_aggregation(agg_raw: pd.DataFrame) -> pd.DataFrame:
    """集計結果 JSONL をメトリクス × 統計量のテーブルに整形する。"""
    melted = agg_raw.melt(
        id_vars=["aggregationMetric"], var_name="metric", value_name="result"
    )
    melted = melted[melted["result"].apply(lambda x: isinstance(x, dict))]
    melted["score"] = melted["result"].apply(lambda x: x["score"])
    summary = melted.pivot_table(
        index="metric", columns="aggregationMetric", values="score", aggfunc="first"
    )
    summary = summary.rename(
        columns={"AVERAGE": "average", "STANDARD_DEVIATION": "std_dev"}
    )
    summary.columns.name = None
    return summary


def parse_evaluation(eval_raw: pd.DataFrame) -> pd.DataFrame:
    """個別評価結果 JSONL をプロンプト × スコアのテーブルに整形する。"""
    instances = pd.json_normalize(
        eval_raw["jsonInstance"].apply(
            lambda x: json.loads(x) if isinstance(x, str) else x
        )
    )[["prompt", "response"]]
    scores = eval_raw["evaluationResults"].apply(
        lambda rs: {
            k: v["score"]
            for r in rs for k, v in r.items()
            if isinstance(v, dict) and "score" in v
        }
    )
    return pd.concat([instances, pd.DataFrame(scores.tolist())], axis=1)


agg_raw, eval_raw = load_eval_results(GCS_DEST, PROJECT_ID)  # noqa: F821

print("=== 集計結果 ===")
display(parse_aggregation(agg_raw))

print("\n=== 個別評価結果 ===")
display(parse_evaluation(eval_raw))
