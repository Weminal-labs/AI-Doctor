from config import *
from question_processing import QuestionProcessor
from context_retrieval import get_context
from answer_generation import answer_question
import json
def main(summary, clusters):
    chat_history_str = ''
    while True:
        question = input("Enter your question (or type 'exit' to quit): ")
        if question.lower() == 'exit':
            break

        # Step 1: Rewrite the question
        rewritten_question = QuestionProcessor().rewrite_question(question, chat_history_str)
        print("Rewritten question: ", rewritten_question)

        # Step 2: Get follow-up questions if needed
        follow_up_question_list = json.loads(QuestionProcessor().get_follow_up_questions(rewritten_question, chat_history_str))
        print("Follow-up questions: ", follow_up_question_list)

        follow_up_answer_list = []
        if follow_up_question_list['is_code_request']:
            for follow_up_question in follow_up_question_list['follow_up_questions']:
                follow_up_answer = input(f"Enter information for the question: {follow_up_question}: ")
                follow_up_answer_list.append(follow_up_answer)

        # Step 3: Create the final question
        final_question = QuestionProcessor().get_final_question(rewritten_question, follow_up_question_list['follow_up_questions'], follow_up_answer_list, chat_history_str)
        print("Final question: ", final_question)

        # Step 4: Classify the question
        label = QuestionProcessor().question_classification(final_question)
        context = ''
        if label == 1:
            # Step 5: Retrieve context
            context = get_context(final_question, summary)  # Assume you have a variable summary containing document summaries

        # Step 6: Answer the question
        answer = answer_question(final_question, context, chat_history_str)
        print("Answer: ", answer)

        # Update chat history
        chat_history_str += f'User: {question}\nAssistant: {answer}\n'

if __name__ == "__main__":
    summary = ''
    clusters = ''
    main(summary, clusters)