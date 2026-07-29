# src/data_utils.py
"""データ読み込み・分割ユーティリティ"""
import pandas as pd
from sklearn.model_selection import train_test_split


def load_data_from_gcs(bucket_name: str, data_path: str, fs) -> pd.DataFrame:
    """GCS から全ファイルを読み込んで結合

    Args:
        bucket_name: GCS バケット名
        data_path: データファイルのパスパターン（例: data/nyc-taxi-tip-2022/taxi-*.csv）
        fs: gcsfs.GCSFileSystem インスタンス

    Returns:
        結合された DataFrame
    """
    gcs_path_pattern = f"gs://{bucket_name}/{data_path}"
    file_list = fs.glob(gcs_path_pattern)

    if not file_list:
        raise FileNotFoundError(f"No files found: {gcs_path_pattern}")

    print(f"Found {len(file_list)} files. Loading all files...")
    df_list = [pd.read_csv(f"gs://{file}") for file in file_list]
    df = pd.concat(df_list, ignore_index=True)
    print(f"Loaded {len(df)} rows")

    return df


def split_data(df: pd.DataFrame, train_ratio: float = 0.9) -> pd.DataFrame:
    """データを学習用・予測用に分割

    末尾10%は9章の予測用に残すため、前90%のみを返す。

    Args:
        df: 入力 DataFrame
        train_ratio: 学習用に使用する割合（デフォルト: 0.9）

    Returns:
        学習用 DataFrame
    """
    train_size = int(len(df) * train_ratio)
    df_train = df.iloc[:train_size]
    print(f"Using first {int(train_ratio * 100)}% for training: {len(df_train)} rows")
    return df_train


def train_val_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_state: int = 42,
) -> tuple:
    """データを学習・検証・テストに分割

    Args:
        X: 特徴量 DataFrame
        y: ターゲット Series
        val_ratio: 検証データの割合（デフォルト: 0.1）
        test_ratio: テストデータの割合（デフォルト: 0.1）
        random_state: 乱数シード

    Returns:
        X_train, X_val, X_test, y_train, y_val, y_test のタプル
    """
    test_val_ratio = val_ratio + test_ratio

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=test_val_ratio, random_state=random_state
    )

    val_in_temp_ratio = val_ratio / test_val_ratio
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=(1 - val_in_temp_ratio), random_state=random_state
    )

    print(f"Train: {len(X_train)}, Validation: {len(X_val)}, Test: {len(X_test)}")

    return X_train, X_val, X_test, y_train, y_val, y_test
