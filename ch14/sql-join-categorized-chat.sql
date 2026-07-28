SELECT DISTINCT
  message.timestamp,
  message.userEmail,
  userMessage,
  chatbotMessage,
  category
FROM `chatbot.sample_chat` message
INNER JOIN `chatbot.categorized_chat` cate
USING (timestamp, userEmail)