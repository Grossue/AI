from langchain_openai import ChatOpenAI

def get_llm(model="chatgpt-4o-latest"): # gpt-5-mini gpt-4o gpt-4.1-mini chatgpt-4o-latest
  llm = ChatOpenAI(model=model)
  return llm

def get_json_llm():
    llm = get_llm()
    return llm.bind(response_format={"type": "json_object"})