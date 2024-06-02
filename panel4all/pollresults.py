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
	def initialize_from_filenames(self, variable_information_file:str, variable_values_file:str, results_closed_questions_file:str, results_open_questions_file:str=None):
		return self.initialize_from_dataframes(
			variable_information_table = pandas.read_csv(variable_information_file, skiprows=1, skipfooter=1, engine='python'),
			variable_values_table = pandas.read_csv(variable_values_file, skiprows=1),
			results_closed_questions = pandas.read_csv(results_closed_questions_file),
			results_open_questions = pandas.read_csv(results_open_questions_file).rename(columns=lambda x: re.sub(':? ?','',x)) if results_open_questions_file else None,
		)

	def initialize_from_dataframes(self, variable_information_table:pandas.DataFrame, variable_values_table:pandas.DataFrame, results_closed_questions:pandas.DataFrame, results_open_questions:pandas.DataFrame=None):
		### 1. Variable information table --- map question code to label.
		self.variable_information_table = variable_information_table
		logger.debug("variable_information_table:\n%s", self.variable_information_table)
		self.map_question_code_to_label = {row["Variable"]: row["Label"] for index, row in self.variable_information_table.iterrows()}
		logger.debug("map_question_code_to_label:\n%s",self.map_question_code_to_label)

		### 2. Variable values table --- map answer code to label.
		self.variable_values_table = variable_values_table
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

		### 3. Results to closed questions
		self.results_closed_questions = results_closed_questions
		logger.debug("results_closed_questions:\n%s", self.results_closed_questions)
		self.columns = self.results_closed_questions.columns
		self.map_voter_id_to_closed_answers = {int(row["id"]): row for _, row in self.results_closed_questions.iterrows()}
		logger.debug("map_voter_id_to_closed_answers:\n%s", self.map_voter_id_to_closed_answers)
		self.voter_ids = list(self.map_voter_id_to_closed_answers.keys())

		### 4. Results to open questions
		if results_open_questions is not None:
			self.results_open_questions = results_open_questions
			self.map_voter_id_to_open_answers = {int(row["user_ID"]): row for _, row in self.results_open_questions.iterrows()}
			logger.debug("map_voter_id_to_open_answers:\n%s",self.map_voter_id_to_open_answers)
		else:
			self.results_open_questions =  self.map_voter_id_to_open_answers = None
			logger.debug("No open questions file")

		return self


	def filtered(self, filter_query:str):
		"""
		return a new PollResults object, that contains the data of the present object filtered by the given query.

		BUG: Currently, open questions are not filtered.
		"""
		return PollResults().initialize_from_dataframes(
			variable_information_table = self.variable_information_table,
			variable_values_table = self.variable_values_table,
			results_closed_questions = self.results_closed_questions.query(filter_query),
			results_open_questions = self.results_open_questions
		)

	def print_question_and_answer_labels(self):
		"""
		Pretty-print the question codes and labels, and for each question - its answer codes and labels.
		"""
		for question_code,question_label in self.map_question_code_to_label.items():
			print(f"\n{question_code}: {question_label}")
			if question_code in self.map_question_code_to_map_answer_code_to_label:
				for answer_code,answer_label in self.map_question_code_to_map_answer_code_to_label[question_code].items():
					print(f"\t{answer_code}: {answer_label}")

	def voter_id(self, voter_index:int=0, voter_id:int=None):
		"""
		Get the unique voter id.

		The voter can be given either by voter_index (starts with 0) or voter_id (unique id in the panel).
		If both are given, voter_id takes precedence.
		"""
		if voter_id is None:
			voter_id = self.voter_ids[voter_index]
		return voter_id

	def subquestion_codes(self, question_code:str):
		"""
		returns the codes of all subquestions of a single multi-answer question.
		"""
		return [q for q in self.map_question_code_to_label if q.startswith(question_code)]

	def get_voter_answer_single(self, question_code:str, voter_index:int=0, voter_id:int=None):
		"""
		get the answer of a single voter to a single-answer question.

		The voter can be given either by voter_index (starts with 0) or voter_id (unique id in the panel).
		If both are given, voter_id takes precedence.

		:return the answer label.
		"""
		voter_id = self.voter_id(voter_index, voter_id)
		voter_closed_answers = self.map_voter_id_to_closed_answers[voter_id]
		if question_code in voter_closed_answers:            # single-answer question
			voter_answer = voter_closed_answers[question_code]
			return self.map_question_code_to_map_answer_code_to_label[question_code][voter_answer]
		raise ValueError(f"Cannot find answer of voter {voter_id} to question {question_code}")	

	def get_voter_answer_multiple(self, question_code:str, voter_index:int=0, voter_id:int=None):
		"""
		get the answers of a single voter to a multi-answer question.

		The voter can be given either by voter_index (starts with 0) or voter_id (unique id in the panel).
		If both are given, voter_id takes precedence.

		:return a map from the subquestion label to the answer code.
		"""
		voter_id = self.voter_id(voter_index, voter_id)
		voter_closed_answers = self.map_voter_id_to_closed_answers[voter_id]
		subquestion_codes = self.subquestion_codes(question_code)
		if len(subquestion_codes)>0:
			return {self.map_question_code_to_label[code]: voter_closed_answers[code] for code in subquestion_codes}
		raise ValueError(f"Cannot find answer of voter {voter_id} to multi-answer question {question_code}")
	
	def get_voter_answer_rank(self, question_code:str, voter_index:int=0, voter_id:int=None):
		"""
		get the answer of a single voter to a "ranking" question.

		The voter can be given either by voter_index (starts with 0) or voter_id (unique id in the panel).
		If both are given, voter_id takes precedence.

		:return a list of the subquestion labels, ordered from the highest ranked to the lowest-ranked.
		"""
		voter_id = self.voter_id(voter_index, voter_id)
		map_question_label_to_rank = self.get_voter_answer_multiple(question_code, voter_id=voter_id)
		return sorted(map_question_label_to_rank.keys(), key=map_question_label_to_rank.__getitem__)
	
	def get_voter_answer_approval(self, question_code:str, voter_index:int=0, voter_id:int=None):
		"""
		get the answer of a single voter to an "approval" (checkboxes) question.

		The voter can be given either by voter_index (starts with 0) or voter_id (unique id in the panel).
		If both are given, voter_id takes precedence.

		:return a set of the approved subquestion labels.
		"""
		voter_id = self.voter_id(voter_index, voter_id)
		map_question_label_to_rank = self.get_voter_answer_multiple(question_code, voter_id=voter_id)
		return {label for label,answer in map_question_label_to_rank.items() if answer>0}
	
	def get_voter_answers_single(self, question_code:str):
		"""
		:return all voters' answers to the given single-answer question.
		"""
		return [self.get_voter_answer_single(question_code, voter_id=id) for id in self.voter_ids]
	
	def get_voter_answers_multiple(self, question_code:str):
		"""
		:return all voters' answers to the given multi-answer question.
		"""
		return [self.get_voter_answer_multiple(question_code, voter_id=id) for id in self.voter_ids]
	
	def get_voter_answers_rank(self, question_code:str):
		"""
		:return all voters' answers to the given "ranking" question.
		"""
		return [self.get_voter_answer_rank(question_code, voter_id=id) for id in self.voter_ids]
	
	def get_voter_answers_approval(self, question_code:str):
		"""
		:return all voters' answers to the given "approval" question.
		"""
		return [self.get_voter_answer_approval(question_code, voter_id=id) for id in self.voter_ids]


	def print_answers_of_one_voter(self, voter_index:int=0, voter_id:int=None):
		"""
		Pretty-print the answers of one voter (by default the first one), for illustration.

		The voter can be given either by voter_index (starts with 0) or voter_id (unique id in the panel).
		If both are given, voter_id takes precedence.
		"""
		voter_id = self.voter_id(voter_index, voter_id)
		voter_closed_answers = self.map_voter_id_to_closed_answers[voter_id]
		voter_open_answers = self.map_voter_id_to_open_answers[voter_id]
		# print("voter_open_answers: ",voter_open_answers)

		for question_code,question_label in self.map_question_code_to_label.items():
			print(f"{question_code}: {question_label}")
			if question_code in voter_open_answers:             # open (free-text) question
				first_voter_answer = voter_open_answers[question_code]
				print(f"\tTEXT: {first_voter_answer}")
			elif f"{question_code}_1" in voter_open_answers:    # open (free-text) question
				first_voter_answer = voter_open_answers[f"{question_code}_1"]
				print(f"\tTEXT: {first_voter_answer}")
			elif question_code in voter_closed_answers:         # closed questions:
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
		results_jews = self.filtered(f"{religion_question_code}==1")
		results_nonjews = self.filtered(f"{religion_question_code}!=1")
		return (results_jews, results_nonjews)

	def frequency_dict(self, question_code:str, title:str=None)->dict:
		"""
		Computes a table of the frequencies of answers to a single-answer question (in percents).
		:param question_code: the question code.
		:param query (optional): a query to filter the results before computation.
		:return a map from answer code to its frequency.
		"""
		map_answer_code_to_label = self.map_question_code_to_map_answer_code_to_label[question_code]
		results = self.results_closed_questions
		frequency_series = (results.groupby(question_code).count()["id"] / len(results) * 100).round(2)
		the_dict = {"קוד": title}
		the_dict.update(frequency_series.to_dict())
		the_dict["חציון"] = map_answer_code_to_label[results.median(numeric_only=True)[question_code]]
		return the_dict

	def print_frequencies(self, question_code:str):
		"""
		Print a table of the frequencies of answers to a single-answer question (in percents).
		:param question_code: the question code.
		:param query (optional): a query to filter the results before computation.
		"""
		frequency_dict = self.frequency_dict(question_code)
		label = self.map_question_code_to_label[question_code]
		map_answer_code_to_label = self.map_question_code_to_map_answer_code_to_label[question_code]
		print(label,": ")
		for answer_code,frequency in frequency_dict.items():
			print(f"{answer_code}\t{map_answer_code_to_label.get(answer_code,'')}\t{frequency}%")

	def print_frequencies_by_religion(self, question_code:str, religion_question_code:str="col_10"):
		"""
		Print a table of the frequencies of answers to a single-answer question (in percents), 
		grouped by religion.
		:param question_code: the question code.
		:param query (optional): a query to filter the results before computation.
		:param religion_question_code: the question code of the "religion" demographic question.
		"""
		frequency_dict_all   = self.frequency_dict(question_code, title="כללי")
		frequency_dict_jews  = self.filtered(f"{religion_question_code}==1").frequency_dict(question_code, title="יהודים")
		frequency_dict_nonjews  = self.filtered(f"{religion_question_code}!=1").frequency_dict(question_code, title="לא-יהודים")
		label = self.map_question_code_to_label[question_code]
		map_answer_code_to_label = self.map_question_code_to_map_answer_code_to_label[question_code]
		print("\n",label,": ")
		for answer_code in frequency_dict_all.keys():
			percentsign = "%" if isinstance(frequency_dict_all[answer_code], numbers.Number) else ""
			print(f"{answer_code},{map_answer_code_to_label.get(answer_code,'')},{frequency_dict_all.get(answer_code,0)}{percentsign},{frequency_dict_jews.get(answer_code,0)}{percentsign},{frequency_dict_nonjews.get(answer_code,0)}{percentsign}")
