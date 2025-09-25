
from prompt.few_shot import *
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.chains.combine_documents import create_stuff_documents_chain
from session_utils import get_session_history
from prompt_utils import *

def build_default_rag_chain(llm, examples, system_prompt):
    example_prompt = build_default_chat_prompt_template()
    few_shot_prompt = build_few_shot_prompt(example_prompt, examples)
    qa_prompt = build_system_fewshot_history_human_prompt(few_shot_prompt, system_prompt)
    llm_chain = wrap_llm_output_as_answer(qa_prompt, llm)
    return wrap_llm_chain_with_session_history(llm_chain)


def build_create_article_rag_chain(llm, level, type):
    example_prompt = build_default_chat_prompt_template()
    examples = (
        create_article_examples_LEVEL1 if (type == "GENERAL" and level == "LEVEL1")
        else (create_article_examples_LEVEL2 if type == "GENERAL" 
            else create_article_script_examples)
    )
    few_shot_prompt = build_few_shot_prompt(example_prompt,examples)
    system_prompt = build_system_prompt_by_level_and_type(level, type)
    qa_prompt = build_system_fewshot_history_human_prompt(few_shot_prompt, system_prompt,create_article_human_prompt)
    llm_chain = build_document_chain(qa_prompt, llm)
    return wrap_llm_chain_with_session_history(llm_chain)


def build_document_chain(qa_prompt, llm):
    document_chain = create_stuff_documents_chain(llm, qa_prompt)
    return document_chain | (lambda text: {"answer": text})


def wrap_llm_chain_with_session_history(llm_chain):
    # LLM 체인을 세션 메시지 히스토리와 함께 실행 가능하도록 래핑
    # - llm_chain: 실행할 LLM 체인
    return RunnableWithMessageHistory(
        llm_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

def wrap_llm_output_as_answer(prompt, llm):
    # 프롬프트를 LLM에 전달하고, 결과를 {"answer": text} 형태로 래핑
    return prompt | llm | (lambda text: {"answer": text})