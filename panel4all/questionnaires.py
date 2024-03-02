#!python3

"""
Utility functions for analyzing questionnaire results.

AUTHOR: Erel Segal-Halevi:
SINCE : 2021-05
"""

import pandas, numpy as np, re
from collections import defaultdict

class PollResults:
	def __init__(self, variable_information_file:str, variable_values_file:str, results_closed_questions_file:str, results_open_questions_file:str):
		"""
		Initialize the PollResults structure from CSV files.

		:param variable_information_file: a CSV file from the "Variable Information" tab. Maps question code to question label.
		:param variable_values_file: a CSV file from the "Variable Values" tab. Maps answer code to answer label.
		:param results_closed_questions_file: a CSV file from the third tab in the main Excel file. Maps voter id to voter answers to closed questions.
		:param results_open_questions_file: a CSV file from a different Excel file. Maps voter id to voter answers to open (free-text) questions.
		"""
		self.variable_information_table = pandas.read_csv(variable_information_file, skiprows=1, skipfooter=1, engine='python')
		# print("variable_information_table:\n", self.variable_information_table)
		self.map_question_code_to_label = {row["Variable"]: row["Label"] for index, row in self.variable_information_table.iterrows()}
		# self.map_question_code_to_label = self.variable_information_table[["Variable","Label"]].set_index("Variable").to_dict()["Label"]
		# print("map_question_code_to_label:\n",self.map_question_code_to_label)

		self.variable_values_table = pandas.read_csv(variable_values_file, skiprows=1)
		# self.variable_values_table.fillna(method="ffill")
		# self.variable_values_table.fillna(value=999)
		# self.variable_values_table.ffill()
		# print("variable_values_table: \n", self.variable_values_table)
		self.map_question_code_to_map_answer_code_to_label = defaultdict(dict)
		for _,row in self.variable_values_table.iterrows():
			question_code_raw = row.iloc[0]
			if  pandas.isnull(question_code_raw):
				pass
			else:
				question_code = question_code_raw
			answer_code = row.iloc[1]
			answer_label = row.iloc[2]
			self.map_question_code_to_map_answer_code_to_label[question_code][answer_code] = answer_label

		self.results_closed_questions = pandas.read_csv(results_closed_questions_file)
		# print(self.results_closed_questions)
		self.columns = self.results_closed_questions.columns
		self.map_voter_id_to_closed_answers = {int(row["id"]): row for _, row in self.results_closed_questions.iterrows()}
		# print("map_voter_id_to_closed_answers:\n",self.map_voter_id_to_closed_answers)
		self.voter_ids = list(self.map_voter_id_to_closed_answers.keys())

		self.results_open_questions = pandas.read_csv(results_open_questions_file) \
			.rename(columns=lambda x: re.sub(':? ?','',x))
		
		self.map_voter_id_to_open_answers = {int(row["user_ID"]): row for _, row in self.results_open_questions.iterrows()}
		# print("map_voter_id_to_open_answers:\n",self.map_voter_id_to_open_answers)

		# self.map_question_code_to_short_label = {code: label.split()[0] for code,label in self.map_question_code_to_label.items() if isinstance(label,str)}

	def print_question_and_answer_labels(self):
		"""
		Pretty-print the question codes and labels, and for each question - its answer codes and labels.
		"""
		for question_code,question_label in self.map_question_code_to_label.items():
			print(f"\n{question_code}: {question_label}")
			for answer_code,answer_label in self.map_question_code_to_map_answer_code_to_label[question_code].items():
				print(f"\t{answer_code}: {answer_label}")

	def print_voter_answers(self, voter_index:int=0, voter_id:int=None):
		"""
		Pretty-print the answers of the first voter, for illustration
		"""
		if voter_id is None:
			voter_id = self.voter_ids[voter_index]
		voter_closed_answers = self.map_voter_id_to_closed_answers[voter_id]
		voter_open_answers = self.map_voter_id_to_open_answers[voter_id]
		print("voter_open_answers: ",voter_open_answers)

		for question_code,question_label in self.map_question_code_to_label.items():
			print(f"{question_code}: {question_label}")
			if question_code in voter_open_answers:
				first_voter_answer = voter_open_answers[question_code]
				print(f"\tTEXT: {first_voter_answer}")
			elif f"{question_code}_1" in voter_open_answers:
				first_voter_answer = voter_open_answers[f"{question_code}_1"]
				print(f"\tTEXT: {first_voter_answer}")
			elif question_code in voter_closed_answers:
				if question_code in self.map_question_code_to_map_answer_code_to_label:
					first_voter_answer_code = int(voter_closed_answers[question_code])
					first_voter_answer_label = self.map_question_code_to_map_answer_code_to_label[question_code][first_voter_answer_code]
					print(f"\t{first_voter_answer_code}: {first_voter_answer_label}")
				else:
					first_voter_answer = voter_closed_answers[question_code]
					print(f"\tDATA: {first_voter_answer}")
			else:
				raise ValueError(f"Cannot find question code {question_code}")


	def subquestion_codes(self, question_code:str):
		"""
		returns the codes of all subquestions of a single multi-answer question.
		"""
		return [column for column in self.columns if column.startswith(question_code)]


	def add_label_to_single_answer_question(self, question_code:str, question_label:str):
		map_answer_number_to_label = self.map_answer_code_to_label.query(f"Question=='{question_code}'")[["Value","Label"]].set_index("Value")
		self.results = self.results\
			.join(map_answer_number_to_label, on=question_code)\
			.rename(columns={question_code: f"{question_label}_code", "Label": f"{question_label}_label"})

	def add_label_to_multi_answer_question(self,  question_code:str, question_label:str, short:bool=False):
		subquestion_codes = self.subquestion_codes(question_code)
		def selected_codes(row):
			return [code for code in subquestion_codes if row[code]==1]
		def selected_labels(row):
			map_question_code_to_label = self.map_question_code_to_short_label if short else self.map_question_code_to_label
			return [map_question_code_to_label[code] for code in subquestion_codes if row[code]==1]
		self.results[f"{question_label}_codes"] = self.results.apply(selected_codes, axis=1)
		self.results[f"{question_label}_labels"] = self.results.apply(selected_labels, axis=1)
		self.results.rename({code: code.replace(question_code, question_label) for code in subquestion_codes}, inplace=True)

	def add_label_to_rank_question(self, question_code:str, question_label:str):
		subquestion_codes = self.subquestion_codes(question_code)
		def ranked_codes(row):
			return sorted(subquestion_codes, key=lambda code: row[code])
		def ranked_labels(row):
			return [self.map_question_code_to_label[code] for code in ranked_codes(row)]
		self.results[f"{question_label}_codes"] = self.results.apply(ranked_codes, axis=1)
		self.results[f"{question_label}_labels"] = self.results.apply(ranked_labels, axis=1)



if __name__ == "__main__":
	# questionnaire = PollResults("map_question_code_to_label.csv", "map_answer_code_to_label.csv", "map_voter_id_to_numeric_answers.csv")
	poll_results = PollResults(
		"../example_data/variable_information.csv", 
		"../example_data/variable_values.csv", 
		"../example_data/results_closed_questions.csv", 
		"../example_data/results_open_questions.csv")
	# poll_results.print_questions_and_answers()
	poll_results.print_voter_answers(voter_index=0)

	# questionnaire.add_label_to_single_answer_question("Q2", "single_party")
	# questionnaire.add_label_to_multi_answer_question("Q3", "multi_parties", short=True)
	# questionnaire.add_label_to_single_answer_question("Q4", "single_candidate")
	# questionnaire.add_label_to_multi_answer_question("Q5", "multi_candidates", short=False)
	# questionnaire.add_label_to_rank_question("Q6", "candidate_rank")
	# questionnaire.add_label_to_single_answer_question("Q7", "best_method")

	# print(poll_results.results)
	# poll_results.results.to_csv("results_with_labels.csv")
