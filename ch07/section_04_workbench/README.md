# 7.4 Agent Platform Workbench

`nyc_taxi_eda_and_lightgbm.ipynb` は、NYC Taxi CSV を入力に EDA、前処理、LightGBM 学習を行う Notebook です。出力はグラフと指定した Cloud Storage のモデルです。

NotebookをAgent Platform Workbenchまたは対応するJupyter環境で開き、先頭の設定セルにバケット名などの必須値を設定して実行します。

EDAとLightGBM学習はNotebookを開いたPython環境で実行されます。CSVの読み込みとモデルの保存ではCloud Storage APIを呼び出します。実行には、Google Cloudへの認証と、対象バケットを読み書きする権限が必要です。Agent Platform WorkbenchやCloud Storageなど、使用するサービスとリソースに応じて料金が発生します。操作の背景と環境準備は書籍7.4節を参照してください。
