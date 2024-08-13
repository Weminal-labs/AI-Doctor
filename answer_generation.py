from config import claude_3_haiku
from .prompts import *
def answer_question(question, context, chat_history):
    answer = claude_3_haiku.invoke(answer_question_prompt.format(question=question, context=context, chat_history = chat_history))
    input_tokens_cluster = answer.usage_metadata['input_tokens']
    output_tokens_cluster = answer.usage_metadata['output_tokens']
    print('in tokens:  ', input_tokens_cluster)
    print('out tokens:  ', output_tokens_cluster)
    return answer.content.strip().strip("\n")