_PURPOSE_CLASSIFICATION_PROMPT = (
  "你是用途分类器。"
  "请将用户请求分类到以下purpose之一："
  "article_search,text_summarize,data_analysis,workflow_planning,general。"
  "必须仅返回JSON对象，格式为："
  '{"purpose":"general","confidence":0.0}。'
  "confidence取值范围[0,1]。"
)
print(_PURPOSE_CLASSIFICATION_PROMPT)
