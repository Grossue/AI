from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, FewShotChatMessagePromptTemplate
from prompt.article_prompt import level_1, level_2, system_prompt_general, system_prompt_scripts,create_article_human_prompt

def build_default_chat_prompt_template():
    return ChatPromptTemplate.from_messages(
        [
            ("human", "{input}"),
            ("ai", "{answer}"),
        ]
    )

def build_system_fewshot_history_human_prompt(few_shot_prompt, system_prompt, human_prompt="{input}"):
    """
    챗 프롬프트 생성
    - system_prompt: 시스템 메시지
    - few_shot_prompt: few-shot 예시
    - human_prompt: 사용자 입력 프롬프트, 기본값은 "{input}"
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            few_shot_prompt,
            MessagesPlaceholder("chat_history"),
            ("human",  human_prompt),
        ]
    )

def build_few_shot_prompt(example_prompt, examples):
    return FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )


def build_system_prompt_by_level_and_type(level, type):
    system_prompt = system_prompt_general if type == "GENERAL" else system_prompt_scripts
    if level == "LEVEL1":
        system_prompt = level_1 + "\n" + system_prompt
    elif level == "LEVEL2":
        system_prompt = level_2 + "\n" + system_prompt
    return system_prompt
