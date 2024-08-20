from AI.config.config import *
from AI.query_processor.question_processing import QuestionProcessor
from AI.context_retrieval.context_retrieval import ContextRetriever
from AI.answer_generation.answer_generation import answer_question
def main():
    chat_history_str = ''
    while True:
        question = input("Enter your question (or type 'exit' to quit): ")
        if question.lower() == 'exit':
            break

        # Step 1: Rewrite the question
        rewritten_question = QuestionProcessor().rewrite_question(question, chat_history_str)
        print("Rewritten question: ", rewritten_question)
        
        # Step 2: Retrieve package ID for the rewritten question
        package_id_results = QuestionProcessor().get_package_id(rewritten_question)
        context = ''
        
        if package_id_results.package_id:
            # Step 3 If package ID is found, retrieve context from the web
            context = get_context_from_web(package_id_results.package_id)
        else:
            # Step 4  If no package ID is found, generate follow-up questions
            follow_up_question_list = QuestionProcessor().get_follow_up_questions(rewritten_question, chat_history_str)
            print("Follow-up questions: ", follow_up_question_list)

            follow_up_answer_list = []
            if follow_up_question_list.is_code_request:
                # Step 5 If follow-up questions require additional information, ask the user
                for follow_up_question in follow_up_question_list.follow_up_questions:
                    follow_up_answer = input(f"Enter information for the question: {follow_up_question}: ")
                    follow_up_answer_list.append(follow_up_answer)

            # Step 6 Create the final question based on follow-up questions and answers
            final_question = QuestionProcessor().get_final_question(rewritten_question, follow_up_question_list.follow_up_questions, follow_up_answer_list, chat_history_str)
            print("Final question: ", final_question)

        # Step 7 Classify the final question to determine the next step
        label = QuestionProcessor().question_classification(final_question)
        if label == 1:
            # Step 8 If the question is classified as requiring context, retrieve it
            context += ContextRetriever().get_context(final_question)  # Assume you have a variable summary containing document summaries

        # step 9 Answer the final question using the retrieved context
        answer = answer_question(final_question, context, chat_history_str)
        print("Answer: ", answer)

        # step 10 Update the chat history with the user's question and the assistant's answer
        chat_history_str += f'User: {question}\nAssistant: {answer}\n'

if __name__ == "__main__":
    main()