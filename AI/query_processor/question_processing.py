import json
from AI.config.config import AIModel
from AI.config.prompts import *
from typing import List
from langchain_core.pydantic_v1 import BaseModel, Field

class FollowUpQuestionResponse(BaseModel):
    explanation: str = Field(description="The explanation for your response")
    is_code_request: bool = Field(description="Indicates if the request is related to Move-on-Aptos code")
    follow_up_questions: List[str] = Field(default_factory=list, description="List of follow-up questions")

class PackageID(BaseModel):
    package_id: str = Field(description="The package id or contract address (often starting with '0x'). If no package id or contract address in user query then return empty string.")
    is_package_id: bool = Field(description="Whether the user query contains package id or contract address. True or False.")

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
        prompt = rewrite_question_prompt.format(question=question, chat_history=chat_history)
        messages = [
        (
            "system",system_prompt
        ),
        ("human", prompt)
    ]
        completion = AIModel.claude_3_haiku.invoke(messages)
        return completion.content.strip().strip("\n")
    
    def get_package_id(self, query):
        messages = [
        (
            "system",system_prompt
        ),
        ("human", package_id_identification_prompt.format(query = query))
    ]
        structured_llm= AIModel.claude_3_haiku.with_structured_output(PackageID)
        response = structured_llm.invoke(messages)
        return response.package_id, response.is_package_id

    
    def get_follow_up_questions(self, question, chat_history):
        messages = [
        (
            "system",system_prompt
        ),
        ("human", follow_up_questions_prompt.format(question = question, chat_history = chat_history))
    ]
        structured_llm= AIModel.claude_3_haiku.with_structured_output(FollowUpQuestionResponse)
        response = structured_llm.invoke(messages)
        return response

    def get_final_question(self, user_question, follow_up_questions, follow_up_answers):
        follow_up_questions_answers = ''
        for id in range(len(follow_up_questions)):
            index = id + 1
            follow_up_questions_answers += "\n" + self.follow_up_questions_answers_format.format(index=index, question=follow_up_questions[id], answer=follow_up_answers[id])
        prompt = final_question_prompt.format(user_question=user_question, follow_up_questions_answers=follow_up_questions_answers)
        completion = AIModel.claude_3_haiku.invoke(prompt)
        return completion.content.strip().strip("\n")

    def question_classification(self, question):
        prompt = question_classification_prompt.format(question=question)
        completion = AIModel.claude_3_haiku.invoke(prompt)
        review_response = completion.content.strip().strip("\n")
        return int(review_response)