from frappe.model.document import Document

from frappe_education_kenya.teaching import exam_print_questions, prevent_preparation_delete, validate_paper


class ExamPaper(Document):
	def validate(self):
		validate_paper(self)

	def before_print(self, settings=None):
		self.exam_questions = exam_print_questions(self)

	def get_print_questions(self):
		return exam_print_questions(self)

	def on_trash(self):
		prevent_preparation_delete(self)
