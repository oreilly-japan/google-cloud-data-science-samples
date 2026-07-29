# 第13章: Agent Platform Vizierによるベイズ最適化

本章ではGemini Enterprise Agent Platform（以下、Agent Platform）を使用します。第13章のビル空調シミュレーター、Agent Platform Vizierを利用する最適化、およびExperiments on Agent Platformに記録した結果のサロゲート解析のサンプルです。背景、操作の意味、結果の解釈は書籍第13章を参照してください。

## ファイル

| ファイル | 役割 |
| --- | --- |
| `building_simulator.py` | ローカルのビル空調シミュレーター |
| `01_grid_search.py` | 1変数のグリッドサーチ例 |
| `02_bayesian_optimization.py` | 2変数の最適化例 |
| `03_multi_objective_optimization.py` | 多目的最適化例 |
| `04_surrogate_analysis.py` | 実行結果を入力にしたサロゲート解析 |
| `vizier_runner.py` | Vizier のリクエスト構築と実行処理 |
| `cleanup.py` | 指定した Study を削除する補助コマンド |

最適化スクリプトは、書籍で扱うAgent Platform Vizierの操作を、Agent Platform APIのPython SDKで実行する参考例です。

## 準備

この`ch13/`ディレクトリで依存関係を設定します。

```bash
uv sync --locked
```

`building_simulator.py`と、ローカルCSVを入力にする`04_surrogate_analysis.py`はローカルで実行され、Google Cloud APIを呼び出しません。最適化スクリプトの目的関数もローカルの建物シミュレーターで計算します。

最適化スクリプトからAgent Platform VizierのStudyとTrialを作成し、Experimentsへ結果を記録する場合は、Google Cloud APIを呼び出します。Google Cloud APIを呼び出すコマンドの実行には、Google Cloudへの認証と、対象プロジェクトで各操作を行う権限が必要です。また、使用するサービスやリソースに応じて料金が発生します。

## 実行

`--project` と `--location` を指定します。これらは `GOOGLE_CLOUD_PROJECT` と `GOOGLE_CLOUD_LOCATION` 環境変数でも設定できます。コマンド例の`your-project-id`などは例示用の値です。Google Cloud上で実行する場合は、自身の環境の値へ置き換えてください。`--dry-run`ではGoogle Cloud APIを呼び出さずに、作成予定のリクエストをローカルで確認できます。

```bash
# ローカルのビル空調シミュレーター（Google Cloud APIは呼び出しません）
uv run python -c 'from building_simulator import BuildingEnvironmentSimulator; print(BuildingEnvironmentSimulator(seed=42).calculate_cost(24, 10, 5, 50))'

# 1変数のグリッドサーチ
uv run python 01_grid_search.py \
  --project your-project-id --location us-central1 --dry-run

# 2変数の最適化
uv run python 02_bayesian_optimization.py \
  --project your-project-id --location us-central1 --dry-run

# 多目的最適化
uv run python 03_multi_objective_optimization.py \
  --project your-project-id --location us-central1 --dry-run
```

Google Cloud上でStudyとTrialを作成し、Experimentsへ結果を記録するには`--confirm-cloud-run`が必要です。`02_bayesian_optimization.py`と`03_multi_objective_optimization.py`では、さらに`--allow-billable`を指定します。

```bash
uv run python 02_bayesian_optimization.py \
  --project your-project-id --location us-central1 \
  --confirm-cloud-run --allow-billable
```

最適化スクリプトの入力はプロジェクト、ロケーション、Study と Experiment の表示名、trial 数です。Google Cloud APIを呼び出した場合は、Studyのリソース名と完了したTrial数を出力します。

サロゲート解析は`param.*`列と`metric.cost`列を持つローカルCSVを入力にし、特徴量重要度をJSONとしてローカルに出力します。次のコマンドはGoogle Cloud APIを呼び出しません。

```bash
uv run python 04_surrogate_analysis.py \
  --input-csv non_sensitive_trials.csv --output-json feature_importances.json
```

`--experiment`でExperimentsから結果を読み取る場合はGoogle Cloud APIを呼び出すため、`--confirm-cloud-read`の指定が必要です。実行には、Google Cloudへの認証と、対象プロジェクトでExperimentsの結果を読み取る権限が必要です。

`cleanup.py`は完全なStudyリソース名を受け取ります。`--dry-run`ではGoogle Cloud APIを呼び出さずに削除対象を確認できます。

```bash
uv run python cleanup.py \
  --study-name projects/your-project-id/locations/us-central1/studies/your-study-id \
  --location us-central1 --dry-run
```

Google Cloud上のStudyを削除する場合は、`--dry-run`を外して`--confirm-delete`を指定します。削除を実行するには、Google Cloudへの認証と、対象Studyを削除する権限が必要です。実行前に、表示されたリソース名が削除対象と一致することを確認してください。
