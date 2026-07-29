DECLARE prompt_template STRING;
DECLARE model_params JSON;

SET prompt_template = """ユーザーとチャットボットの会話履歴を与えます。その会話が以下のカテゴリーのうち、どれに最も当てはまるかをJSON形式で抽出してください。:
- 音楽
- 映画
- 温泉
- グルメ
- キャンプ
- 読書
- ゲーム
- スポーツ
- アウトドア
- ショッピング

上記のすべてのカテゴリーに当てはまらない場合のみ、「その他」としてください。

ユーザーが送信した文章は「__userMessage__」で、チャットボットは「__chatbotMessage__」と返信しました。

<出力フォーマット>
{"カテゴリー": (音楽|映画|温泉|グルメ|キャンプ|読書|ゲーム|スポーツ|アウトドア|ショッピング|その他)}
</出力フォーマット>""";

SET model_params = PARSE_JSON(
"""
{
  "generation_config": {
    "temperature": 0.0,
    "max_output_tokens": 1024,
    "thinking_config": {"thinking_budget": 0},
    "responseMimeType": "application/json",
    "responseSchema": {
      "type": "OBJECT",
      "properties": {
        "category": {
          "type": "STRING",
          "description": "会話が属するカテゴリー"
        }
      },
      "required": [
        "category"
      ]
    }
  }
}
""");


INSERT INTO `chatbot.categorized_chat`
WITH prompts AS (
  SELECT
    REPLACE(REPLACE(prompt_template, "__userMessage__", userMessage), "__chatbotMessage__", chatbotMessage) AS prompt,
    *
  FROM `chatbot.sample_chat`
)
SELECT
  timestamp,
  userEmail,
  JSON_VALUE(
    AI.GENERATE(
      prompt => prompt,
      endpoint => "https://aiplatform.googleapis.com/v1/projects/categorize-chat-with-gemini/locations/global/publishers/google/models/gemini-2.5-flash",
      model_params => model_params
    ).result,
    "$.category"
  ) AS category
FROM prompts