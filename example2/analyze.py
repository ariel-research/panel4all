"""
Code for analyzing results of Example Poll #1
"""

import panel4all, logging

panel4all.logger.addHandler(logging.StreamHandler())
panel4all.logger.setLevel(logging.DEBUG)

example_folder = "."
poll_results = panel4all.PollResults().initialize_from_filenames(
    f"{example_folder}/variable_information.csv", 
    f"{example_folder}/variable_values.csv", 
    f"{example_folder}/results_closed_questions.csv", 
    f"{example_folder}/results_open_questions.csv")

print("\n\n=== Question and answer codes: ===")	
poll_results.print_question_and_answer_labels()

print("\n\n=== Example answers of one voter: ===")	
poll_results.print_answers_of_one_voter(voter_index=0)

print("\n\n=== Frequency table of Q2: ===")	
poll_results.print_frequencies("Q2")

print("\n\n=== Frequency table of Q2 by religion: ===")	
poll_results.print_frequencies_by_religion("Q2", religion_question_code="col_10")
