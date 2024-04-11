#!python3

"""
Utility functions for analyzing questionnaire results.

AUTHOR: Erel Segal-Halevi:
SINCE : 2021-05
"""

import pandas, numpy as np, re, numbers, logging
from collections import defaultdict

logger = logging.getLogger(__name__)

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
		logger.debug("variable_information_table:\n%s", self.variable_information_table)
		self.map_question_code_to_label = {row["Variable"]: row["Label"] for index, row in self.variable_information_table.iterrows()}
		logger.debug("map_question_code_to_label:\n%s",self.map_question_code_to_label)

		self.variable_values_table = pandas.read_csv(variable_values_file, skiprows=1)
		logger.debug("variable_values_table:\n%s", self.variable_values_table)
		map_question_code_to_map_answer_code_to_label = defaultdict(dict)
		for _,row in self.variable_values_table.iterrows():
			question_code_raw = row.iloc[0]
			if  pandas.isnull(question_code_raw):
				pass
			else:
				question_code = question_code_raw
			answer_code = row.iloc[1]
			answer_label = row.iloc[2]
			map_question_code_to_map_answer_code_to_label[question_code][answer_code] = answer_label
		self.map_question_code_to_map_answer_code_to_label = dict(map_question_code_to_map_answer_code_to_label)
		logger.debug("map_question_code_to_map_answer_code_to_label:\n%s", self.map_question_code_to_map_answer_code_to_label)

		self.results_closed_questions = pandas.read_csv(results_closed_questions_file)
		logger.debug("results_closed_questions:\n%s", self.results_closed_questions)
		self.columns = self.results_closed_questions.columns
		self.map_voter_id_to_closed_answers = {int(row["id"]): row for _, row in self.results_closed_questions.iterrows()}
		logger.debug("map_voter_id_to_closed_answers:\n%s", self.map_voter_id_to_closed_answers)
		self.voter_ids = list(self.map_voter_id_to_closed_answers.keys())

		self.results_open_questions = pandas.read_csv(results_open_questions_file) \
			.rename(columns=lambda x: re.sub(':? ?','',x))

		self.map_voter_id_to_open_answers = {int(row["user_ID"]): row for _, row in self.results_open_questions.iterrows()}
		logger.debug("map_voter_id_to_open_answers:\n%s",self.map_voter_id_to_open_answers)
		# self.map_question_code_to_short_label = {code: label.split()[0] for code,label in self.map_question_code_to_label.items() if isinstance(label,str)}


	def print_question_and_answer_labels(self):
		"""
		Pretty-print the question codes and labels, and for each question - its answer codes and labels.
		"""
		for question_code,question_label in self.map_question_code_to_label.items():
			print(f"\n{question_code}: {question_label}")
			if question_code in self.map_question_code_to_map_answer_code_to_label:
				for answer_code,answer_label in self.map_question_code_to_map_answer_code_to_label[question_code].items():
					print(f"\t{answer_code}: {answer_label}")

	def print_answers_of_one_voter(self, voter_index:int=0, voter_id:int=None):
		"""
		Pretty-print the answers of one voter (by default the first one), for illustration
		"""
		if voter_id is None:
			voter_id = self.voter_ids[voter_index]
		voter_closed_answers = self.map_voter_id_to_closed_answers[voter_id]
		voter_open_answers = self.map_voter_id_to_open_answers[voter_id]
		# print("voter_open_answers: ",voter_open_answers)

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
					voter_answer_code = int(voter_closed_answers[question_code])
					voter_answer_label = self.map_question_code_to_map_answer_code_to_label[question_code][voter_answer_code]
					print(f"\t{voter_answer_code}: {voter_answer_label}")
				else:
					first_voter_answer = voter_closed_answers[question_code]
					print(f"\tDATA: {first_voter_answer}")
			else:
				raise ValueError(f"Cannot find question code {question_code}")

	def partition_by_religion(self, religion_question_code:str="col_10"):
		self.results_jews = self.results_closed_questions.query(f"{religion_question_code}==1")
		self.results_nonjews = self.results_closed_questions.query(f"{religion_question_code}!=1")

	def frequency_dict(self, question_code:str, query:str=None, title:str=None)->dict:
		"""
		Computes a table of the frequencies of answers to the given question (in percents).

		:param question_code: the question code.
		:param query (optional): a query to filter the results before computation.
		:return a map from answer code to its frequency.
		"""
		map_answer_code_to_label = self.map_question_code_to_map_answer_code_to_label[question_code]
		results = self.results_closed_questions
		if query is not None:
			results = results.query(query)
		frequency_series = (results.groupby(question_code).count()["id"] / len(results) * 100).round(2)
		the_dict = {"קוד": title}
		the_dict.update(frequency_series.to_dict())
		the_dict["חציון"] = map_answer_code_to_label[results.median(numeric_only=True)[question_code]]
		return the_dict

	def print_frequencies(self, question_code:str, query:str=None):
		"""
		Print a table of the frequencies of answers to the given question (in percents).

		:param question_code: the question code.
		:param query (optional): a query to filter the results before computation.
		"""
		frequency_dict = self.frequency_dict(question_code, query)
		label = self.map_question_code_to_label[question_code]
		map_answer_code_to_label = self.map_question_code_to_map_answer_code_to_label[question_code]
		print(label,": ")
		for answer_code,frequency in frequency_dict.items():
			print(f"{answer_code}\t{map_answer_code_to_label.get(answer_code,'')}\t{frequency}%")

	def print_frequencies_by_religion(self, question_code:str, religion_question_code:str="col_10"):
		"""
		Print a table of the frequencies of answers to the given question (in percents), grouped by religion.

		:param question_code: the question code.
		:param query (optional): a query to filter the results before computation.
		:param religion_question_code: the question code of the "religion" demographic question.
		"""
		frequency_dict_all   = self.frequency_dict(question_code, title="כללי")
		frequency_dict_jews  = self.frequency_dict(question_code, query=f"{religion_question_code}==1", title="יהודים")
		frequency_dict_nonjews  = self.frequency_dict(question_code, query=f"{religion_question_code}!=1", title="לא-יהודים")

		label = self.map_question_code_to_label[question_code]
		map_answer_code_to_label = self.map_question_code_to_map_answer_code_to_label[question_code]
		print("\n",label,": ")
		for answer_code in frequency_dict_all.keys():
			percentsign = "%" if isinstance(frequency_dict_all[answer_code], numbers.Number) else ""
			print(f"{answer_code},{map_answer_code_to_label.get(answer_code,'')},{frequency_dict_all.get(answer_code,0)}{percentsign},{frequency_dict_jews.get(answer_code,0)}{percentsign},{frequency_dict_nonjews.get(answer_code,0)}{percentsign}")



	def subquestion_codes(self, question_code:str):
		"""
		returns the codes of all subquestions of a single multi-answer question.
		"""
		return [column for column in self.columns if column.startswith(question_code)]


	def add_label_to_single_answer_question(self, question_code:str, question_label:str):
		"""
		Rename the column titled `question_code` (e.g. "Q2") to `question_label` (a meaningful label for the question).
		"""
		map_answer_number_to_label = self.variable_information_table.query(f"Question=='{question_code}'")[["Value","Label"]].set_index("Value")
		self.results_closed_questions = self.results\
			.join(map_answer_number_to_label, on=question_code)\
			.rename(columns={question_code: f"{question_label}_code", "Label": f"{question_label}_label"})

	def add_label_to_multi_answer_question(self,  question_code:str, question_label:str, short:bool=False):
		subquestion_codes = self.subquestion_codes(question_code)
		def selected_codes(row):
			return [code for code in subquestion_codes if row[code]==1]
		def selected_labels(row):
			map_question_code_to_label = self.map_question_code_to_short_label if short else self.map_question_code_to_label
			return [map_question_code_to_label[code] for code in subquestion_codes if row[code]==1]
		self.results_closed_questions[f"{question_label}_codes"] = self.results.apply(selected_codes, axis=1)
		self.results_closed_questions[f"{question_label}_labels"] = self.results.apply(selected_labels, axis=1)
		self.results.rename({code: code.replace(question_code, question_label) for code in subquestion_codes}, inplace=True)

	def add_label_to_rank_question(self, question_code:str, question_label:str):
		subquestion_codes = self.subquestion_codes(question_code)
		def ranked_codes(row):
			return sorted(subquestion_codes, key=lambda code: row[code])
		def ranked_labels(row):
			return [self.map_question_code_to_label[code] for code in ranked_codes(row)]
		self.results_closed_questions[f"{question_label}_codes"] = self.results.apply(ranked_codes, axis=1)
		self.results_closed_questions[f"{question_label}_labels"] = self.results.apply(ranked_labels, axis=1)



if __name__ == "__main__":
	logger.addHandler(logging.StreamHandler())
	# logger.setLevel(logging.DEBUG)

	example_folder = "../example2"
	poll_results = PollResults(
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

	###  These functions can be used to change column names of questions to more meaningful names.
	# poll_results.add_label_to_single_answer_question("Q2", "single_party")
	# poll_results.add_label_to_multi_answer_question("Q3", "multi_parties", short=True)
	# poll_results.add_label_to_single_answer_question("Q4", "single_candidate")
	# poll_results.add_label_to_multi_answer_question("Q5", "multi_candidates", short=False)
	# poll_results.add_label_to_rank_question("Q6", "candidate_rank")
	# poll_results.add_label_to_single_answer_question("Q7", "best_method")
