# Agent Platform Feature Storeによる特徴量管理（サンプルコード）

第Ⅱ部 6章のサンプルコードです。
前提条件（API の有効化・IAM ロール）や各手順の詳細は書籍 第Ⅱ部 6章を参照してください。

## ファイル

| ファイル | 内容 |
| --- | --- |
| `ch17.ipynb` | 本章のハンズオン用ノートブック |
| `clean_up.py` | 作成したリソースを一括削除するスクリプト（ノートブック末尾のクリーンアップセルと同じ処理） |

## 実行方法

1. Colab Enterprise で `ch17.ipynb` を開きます。
2. `PROJECT_ID` にご自身の Google Cloud プロジェクト ID を入力します。
3. 上のセルから順に実行します。

FeatureOnlineStore の作成やデータ同期には数分〜十数分かかります。継続的同期のシミュレーションセルは任意実行のため、必要な場合のみ `RUN_CONTINUOUS_SYNC_DEMO = True` に変更して実行してください。
