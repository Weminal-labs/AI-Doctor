import json
import os

class PromptLoader:
    def __init__(self, json_file):
        self.json_file = json_file
        self.prompts = self.load_prompts()

    def load_prompts(self):
        with open(self.json_file, 'r') as file:
            return json.load(file)

# Sử dụng
prompt_loader = PromptLoader(os.path.join(os.path.dirname(__file__), 'prompts.json'))
answer_question_prompt = prompt_loader.prompts.get("answer_question_prompt")
rewrite_question_prompt = prompt_loader.prompts.get("rewrite_question_prompt")
get_follow_up_questions_prompt = prompt_loader.prompts.get("get_follow_up_questions_prompt")
get_final_question_prompt = prompt_loader.prompts.get("get_final_question_prompt")
question_classification_prompt = prompt_loader.prompts.get("question_classification_prompt")