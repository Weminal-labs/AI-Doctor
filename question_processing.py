import json
from .config import claude_3_haiku
from .prompts import *
class QuestionProcessor:
    def __init__(self):
        self.follow_up_questions_answers_format = '''
        <question{index}>
            <![CDATA[
            {question}
            ]]>
        </question{index}>
        <answer{index}>
            <![CDATA[
            {answer}
            ]]>
        </answer{index}>'''

    def rewrite_question(self, question, chat_history):
        prompt = self.prompt_loader.prompts.get("rewrite_question_prompt").format(question=question, chat_history=chat_history)
        completion = claude_3_haiku.invoke(prompt)
        return completion.content.strip().strip("\n")

    def get_follow_up_questions(self, question, chat_history):
        prompt = self.prompt_loader.prompts.get("get_follow_up_questions_prompt").format(question=question, chat_history=chat_history)
        completion = claude_3_haiku.invoke(prompt)
        return completion.content.strip().strip("\n")

    def get_final_question(self, user_question, follow_up_questions, follow_up_answers, chat_history):
        
        
        follow_up_questions_answers = ''
        for id in range(len(follow_up_questions)):
            index = id + 1
            follow_up_questions_answers += "\n" + self.follow_up_questions_answers_format.format(index=index, question=follow_up_questions[id], answer=follow_up_answers[id])
        
        prompt = self.prompt_loader.prompts.get("get_final_question_prompt").format(user_question=user_question, follow_up_questions_answers=follow_up_questions_answers)
        completion = claude_3_haiku.invoke(prompt)
        return completion.content.strip().strip("\n")

    def question_classification(self, question):
        prompt = self.prompt_loader.prompts.get("question_classification_prompt").format(question=question)
        completion = claude_3_haiku.invoke(prompt)
        review_response = completion.content.strip().strip("\n")
        return int(review_response)