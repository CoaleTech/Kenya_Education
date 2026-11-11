"""Teaching preparation, native workflows and examination confidentiality."""

import json
from html.parser import HTMLParser
from pathlib import Path

import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.model.workflow import apply_workflow
from frappe.utils import cint, flt, get_datetime, now_datetime, sanitize_html

MANAGERS = {"Academic Admin", "Head Teacher", "System Manager"}
LEARNERS = {"Student", "Guardian"}
FROZEN = {"Approved", "Locked", "Released"}
READ_TYPES = {"read", "select", "print", "report", "export", "email"}


def learner(user=None):
	user = user or frappe.session.user
	# Administrator holds every role, including the learner ones.
	return user != "Administrator" and bool(LEARNERS.intersection(frappe.get_roles(user)))


def manager(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or (
		not learner(user) and bool(MANAGERS.intersection(frappe.get_roles(user)))
	)


def instructor_names(user=None):
	"""Instructor identity is the installed Instructor -> Employee.user_id relation."""
	user = user or frappe.session.user
	instructor, employee = frappe.qb.DocType("Instructor"), frappe.qb.DocType("Employee")
	return (
		frappe.qb.from_(instructor)
		.join(employee)
		.on(instructor.employee == employee.name)
		.select(instructor.name)
		.where(employee.user_id == user)
	).run(pluck=True)


def released(doc):
	return bool(
		doc.workflow_state == "Released" and doc.release_on and get_datetime(doc.release_on) <= now_datetime()
	)


def preparation_permission(doc, user=None, ptype=None, **kwargs):
	user = user or frappe.session.user
	ptype = ptype or "read"
	if doc.doctype == "Exam Paper" and learner(user):
		return ptype in READ_TYPES and released(doc)
	if learner(user) or user == "Guest":
		return False
	if not manager(user) and doc.instructor not in instructor_names(user):
		return False
	if ptype in READ_TYPES:
		return True
	state = doc.get("workflow_state") or "Draft"
	if doc.get("name") and ptype == "write":
		# apply_workflow sets the target state before save checks permission.
		state = frappe.db.get_value(doc.doctype, doc.name, "workflow_state") or state
	if ptype in {"delete", "share"}:
		return ptype == "delete" and state == "Draft" and manager(user)
	# Transitions still require write permission. Controllers reject content edits in these states.
	if state == "Released":
		return False
	if state == "Locked":
		return user == "Administrator" or "System Manager" in frappe.get_roles(user)
	if not manager(user):
		return state in {"Draft", "Returned"}
	return True


def _visibility(doctype, user=None):
	user = user or frappe.session.user
	table = frappe.qb.DocType(doctype)
	if doctype == "Exam Paper" and learner(user):
		return (table.workflow_state == "Released") & (table.release_on <= now_datetime())
	if learner(user) or user == "Guest":
		return table.name.isnull()
	if manager(user):
		return table.name.isnotnull()
	instructors = instructor_names(user)
	return table.instructor.isin(instructors) if instructors else table.name.isnull()


def _sql(criterion):
	return criterion.get_sql(quote_char="`", with_namespace=True)


def scheme_query(user=None):
	return _sql(_visibility("Scheme of Work", user))


def lesson_query(user=None):
	return _sql(_visibility("Lesson Plan", user))


def paper_query(user=None):
	return _sql(_visibility("Exam Paper", user))


def _business_values(doc):
	"""Compare persisted content, including child rows, not volatile framework timestamps."""
	values = {key: doc.get(key) for key in ("name", "owner", "creation", "docstatus")}
	for field in doc.meta.fields:
		if field.fieldname == "workflow_state" or (
			field.fieldtype in no_value_fields and field.fieldtype not in {"Table", "Table MultiSelect"}
		):
			continue
		value = doc.get(field.fieldname)
		if field.fieldtype in {"Table", "Table MultiSelect"}:
			value = [
				{
					k: v
					for k, v in row.as_dict().items()
					if k
					not in {
						"creation",
						"modified",
						"modified_by",
						"owner",
						"docstatus",
						"parent",
						"parenttype",
						"parentfield",
					}
				}
				for row in value or []
			]
		values[field.fieldname] = value
	return values


def validate_preparation(doc):
	old = doc.get_doc_before_save()
	if learner() or not (manager() or doc.instructor in instructor_names()):
		frappe.throw(_("You may only prepare documents for your linked Instructor."), frappe.PermissionError)
	if not old:
		if doc.workflow_state not in {None, "", "Draft"}:
			frappe.throw(_("New teaching documents must start in Draft."))
		return
	if old.instructor != doc.instructor and not manager():
		frappe.throw(_("Only an academic administrator may change the Instructor."), frappe.PermissionError)
	if old.workflow_state not in {"Draft", "Returned"} and _business_values(old) != _business_values(doc):
		frappe.throw(_("Return the document to Draft before changing its content."))
	if old.workflow_state == "Released":
		frappe.throw(_("Released examination papers are immutable."))
	if old.workflow_state == "Locked":
		if doc.workflow_state != "Released" or not released(doc):
			frappe.throw(_("A locked paper can only be released at or after its release time."))
		frappe.only_for("System Manager")
	if old.workflow_state == doc.workflow_state and old.workflow_state not in {"Draft", "Returned"}:
		frappe.throw(_("This document is read-only; use a Workflow action."))


def prevent_preparation_delete(doc):
	if doc.workflow_state != "Draft":
		frappe.throw(_("Only Draft teaching documents may be deleted."))


def question_papers(question):
	item, paper = frappe.qb.DocType("Exam Paper Item"), frappe.qb.DocType("Exam Paper")
	return (
		frappe.qb.from_(paper)
		.join(item)
		.on(item.parent == paper.name)
		.select(paper.name, paper.instructor, paper.workflow_state, paper.release_on)
		.where((item.question == question) & (item.parenttype == "Exam Paper"))
	).run(as_dict=True)


def question_permission(doc, user=None, ptype=None, **kwargs):
	ptype = ptype or "read"
	papers = question_papers(doc.name)
	if ptype not in READ_TYPES and any(p.workflow_state in FROZEN for p in papers):
		return False
	return all(preparation_permission(frappe._dict(p, doctype="Exam Paper"), user, "read") for p in papers)


def _hidden_questions(user=None):
	item, paper = frappe.qb.DocType("Exam Paper Item"), frappe.qb.DocType("Exam Paper")
	return (
		frappe.qb.from_(item)
		.join(paper)
		.on(item.parent == paper.name)
		.select(item.question)
		.where(
			(item.parenttype == "Exam Paper") & item.question.isnotnull() & ~_visibility("Exam Paper", user)
		)
	)


def question_query(user=None):
	return _sql(frappe.qb.DocType("Question").name.notin(_hidden_questions(user)))


def quiz_permission(doc, user=None, ptype=None, **kwargs):
	return all(
		question_permission(frappe._dict(name=row.question_link), user, "read") for row in doc.question
	)


def quiz_query(user=None):
	row, quiz = frappe.qb.DocType("Quiz Question"), frappe.qb.DocType("Quiz")
	hidden = frappe.qb.from_(row).select(row.parent).where(row.question_link.isin(_hidden_questions(user)))
	return _sql(quiz.name.notin(hidden))


def protect_question(doc, method=None):
	if any(p.workflow_state in FROZEN for p in question_papers(doc.name)):
		frappe.throw(_("A question used by an approved, locked or released paper is immutable."))
	if not question_permission(doc, ptype="write"):
		frappe.throw(_("This question belongs to a confidential examination."), frappe.PermissionError)


def validate_topic_curriculum(doc, method=None):
	"""A Topic's strand sits at its level and its sub-strand under that strand (the pickers only narrow the list)."""
	strand, sub_strand = doc.get("cbc_strand"), doc.get("cbc_sub_strand")
	if strand and frappe.db.get_value("CBC Strand", strand, "cbc_level") != doc.get("cbc_level"):
		frappe.throw(
			_("Strand {0} is not in the level {1}.").format(strand, doc.get("cbc_level") or _("(none)"))
		)
	if sub_strand and frappe.db.get_value("CBC Sub Strand", sub_strand, "strand") != strand:
		frappe.throw(
			_("Sub-strand {0} is not under the strand {1}.").format(sub_strand, strand or _("(none)"))
		)


class ExamQuizMixin:
	"""Education's portal get_quiz/evaluate_quiz bypass Question DocPerm; guard their shared methods."""

	def _check_exam_questions(self):
		if not quiz_permission(self, ptype="read"):
			frappe.throw(_("This quiz contains confidential examination questions."), frappe.PermissionError)

	def get_questions(self):
		self._check_exam_questions()
		return super().get_questions()

	def evaluate(self, response_dict, quiz_name):
		self._check_exam_questions()
		return super().evaluate(response_dict, quiz_name)


class _ResourceLinks(HTMLParser):
	def __init__(self):
		super().__init__()
		self.links = []

	def handle_starttag(self, tag, attrs):
		self.links.extend(
			value for key, value in attrs if key in {"src", "href", "poster", "data", "srcset"} and value
		)


def _validate_question_resources(question):
	parser = _ResourceLinks()
	parser.feed(question.question or "")
	for option in question.options:
		parser.feed(option.option or "")
	for url in parser.links:
		if not url.startswith("/private/files/") or not frappe.db.exists(
			"File",
			{
				"file_url": url,
				"is_private": 1,
				"attached_to_doctype": "Question",
				"attached_to_name": question.name,
			},
		):
			frappe.throw(_("Exam question resources must be private File attachments to that Question."))
	if frappe.db.exists(
		"File", {"attached_to_doctype": "Question", "attached_to_name": question.name, "is_private": 0}
	):
		frappe.throw(_("Make all Question attachments private before using the question in an examination."))
	for attachment in frappe.get_all(
		"File",
		{"attached_to_doctype": "Question", "attached_to_name": question.name},
		["file_url", "content_hash", "is_private"],
	):
		if not attachment.is_private or not (attachment.file_url or "").startswith("/private/files/"):
			frappe.throw(_("All examination question attachments must be private local files."))
		if attachment.content_hash and frappe.db.exists(
			"File", {"content_hash": attachment.content_hash, "is_private": 0}
		):
			frappe.throw(_("An examination question attachment has a public copy; replace that resource."))


def validate_paper(doc):
	validate_preparation(doc)
	if cint(doc.duration_minutes) <= 0:
		frappe.throw(_("Duration must be greater than zero."))
	if not doc.items:
		frappe.throw(_("Add at least one examination question."))
	seen = set()
	for row in doc.items:
		if row.question in seen or flt(row.marks) <= 0:
			frappe.throw(_("Each question must occur once and have positive marks."))
		seen.add(row.question)
		question = frappe.get_doc("Question", row.question)
		if not question_permission(question, ptype="read"):
			frappe.throw(
				_("You cannot use another instructor's confidential examination question."),
				frappe.PermissionError,
			)
		_validate_question_resources(question)
	doc.total_marks = sum(flt(row.marks) for row in doc.items)
	if doc.workflow_state in {"Approved", "Locked", "Released"} and not doc.release_on:
		frappe.throw(_("Set a release time before approving an examination paper."))
	if doc.workflow_state == "Released" and not released(doc):
		frappe.throw(_("The examination release time has not been reached."))


def exam_print_questions(doc):
	frappe.has_permission("Exam Paper", "read", doc=doc, throw=True)
	if doc.workflow_state not in {"Locked", "Released"}:
		frappe.throw(_("Only locked or released examination papers may be printed."), frappe.PermissionError)
	questions = []
	for row in doc.items:
		question = frappe.get_doc("Question", row.question)
		questions.append(
			{
				"question": sanitize_html(question.question or ""),
				"marks": row.marks,
				"section": row.section,
				"options": [sanitize_html(option.option or "") for option in question.options],
			}
		)
	return questions


def _file_papers(doc):
	"""Also cover duplicate File records: core accepts access through any alias URL."""
	references = {(doc.get("attached_to_doctype"), doc.get("attached_to_name"))}
	for field in ("file_url", "content_hash"):
		if doc.get(field):
			for alias in frappe.get_all(
				"File", {field: doc.get(field)}, ["attached_to_doctype", "attached_to_name"]
			):
				references.add((alias.attached_to_doctype, alias.attached_to_name))
	papers = {}
	for doctype, name in references:
		if doctype == "Exam Paper" and name and frappe.db.exists("Exam Paper", name):
			paper = frappe.db.get_value(
				"Exam Paper", name, ["name", "instructor", "workflow_state", "release_on"], as_dict=True
			)
			papers[paper.name] = paper
		elif doctype == "Question" and name:
			for paper in question_papers(name):
				papers[paper.name] = paper
	return list(papers.values())


def file_permission(doc, user=None, ptype=None, **kwargs):
	ptype = ptype or "read"
	papers = _file_papers(doc)
	if not papers:
		return True
	if ptype not in READ_TYPES and any(p.workflow_state in FROZEN for p in papers):
		return False
	return all(
		preparation_permission(frappe._dict(p, doctype="Exam Paper"), user, ptype or "read") for p in papers
	)


def file_query(user=None):
	file = frappe.qb.DocType("File")
	# Include aliases by both URL and hash so sharing/copying a File cannot expose an embargoed blob.
	item, paper = frappe.qb.DocType("Exam Paper Item"), frappe.qb.DocType("Exam Paper")
	hidden = frappe.qb.from_(paper).select(paper.name).where(~_visibility("Exam Paper", user))
	questions = (
		frappe.qb.from_(item)
		.select(item.question)
		.where(item.parent.isin(hidden) & (item.parenttype == "Exam Paper"))
	)
	alias = frappe.qb.DocType("File").as_("exam_attachment")
	restricted = ((alias.attached_to_doctype == "Exam Paper") & alias.attached_to_name.isin(hidden)) | (
		(alias.attached_to_doctype == "Question") & alias.attached_to_name.isin(questions)
	)
	urls = frappe.qb.from_(alias).select(alias.file_url).where(restricted & alias.file_url.isnotnull())
	hashes = (
		frappe.qb.from_(alias).select(alias.content_hash).where(restricted & alias.content_hash.isnotnull())
	)
	return _sql(
		(file.file_url.isnull() | file.file_url.notin(urls))
		& (file.content_hash.isnull() | file.content_hash.notin(hashes))
	)


def protect_file(doc, method=None):
	old = doc.get_doc_before_save() if not doc.is_new() else None
	papers = _file_papers(doc)
	old_papers = _file_papers(old) if old else []
	if old_papers and (old.attached_to_doctype, old.attached_to_name) != (
		doc.attached_to_doctype,
		doc.attached_to_name,
	):
		frappe.throw(_("Examination attachments cannot be detached or reassigned."))
	for paper in papers + old_papers:
		if paper.workflow_state in FROZEN:
			frappe.throw(_("Attachments to approved, locked or released examinations are immutable."))
		frappe.has_permission("Exam Paper", "write", doc=paper.name, throw=True)
	if papers or doc.attached_to_doctype == "Exam Paper":
		doc.is_private = 1
		if doc.content_hash and frappe.db.exists("File", {"content_hash": doc.content_hash, "is_private": 0}):
			frappe.throw(_("This attachment has a public copy; upload different confidential content."))
		if doc.is_remote_file or (doc.file_url and not doc.file_url.startswith("/private/files/")):
			frappe.throw(
				_("Upload examination attachments as private local files, not public files or URLs.")
			)


class ExamFileMixin:
	"""Set privacy before File.before_insert writes bytes; doc_events alone execute too late."""

	def before_insert(self):
		protect_file(self)
		return super().before_insert()

	def validate(self):
		protect_file(self)
		return super().validate()

	def save_file_on_filesystem(self):
		protect_file(self)
		return super().save_file_on_filesystem()

	def is_downloadable(self):
		return file_permission(self, ptype="read") and super().is_downloadable()

	def get_content(self, encodings=None):
		if not file_permission(self, ptype="read"):
			frappe.throw(_("This examination attachment is confidential."), frappe.PermissionError)
		return super().get_content(encodings)

	def on_trash(self):
		protect_file(self)
		return super().on_trash()


@frappe.whitelist(methods=["GET"])
def scheme_weeks(scheme: str):
	if not isinstance(scheme, str):
		frappe.throw(_("Invalid Scheme of Work."))
	doc = frappe.get_doc("Scheme of Work", scheme)
	frappe.has_permission("Scheme of Work", "read", doc=doc, throw=True)
	if doc.workflow_state != "Approved":
		frappe.throw(_("Select an approved Scheme of Work."))
	return [{"name": row.name, "week_no": row.week_no, "topic": row.topic} for row in doc.weeks]


def release_exam_papers():
	"""Hourly scheduler; native workflow and all document validation remain active."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		for name in frappe.get_all(
			"Exam Paper", {"workflow_state": "Locked", "release_on": ["<=", now_datetime()]}, pluck="name"
		):
			try:
				paper = frappe.get_doc("Exam Paper", name, for_update=True)
				if paper.workflow_state == "Locked" and released(
					frappe._dict(paper.as_dict(), workflow_state="Released")
				):
					apply_workflow(paper, "Release")
				frappe.db.commit()  # nosemgrep: one released paper must not be rolled back by another's failure.
			except Exception:
				frappe.db.rollback()
				frappe.log_error(title=_("Exam Paper release failed: {0}").format(name))
	finally:
		frappe.set_user(previous_user)


def setup():
	"""Import this domain's real Workflow masters and locked print idempotently after model sync."""
	frappe.only_for("System Manager")
	root = Path(__file__).parent
	for path in sorted((root / "teaching_fixtures").glob("*.json")):
		for data in json.loads(path.read_text()):
			name = (
				data.get("name")
				or data.get("workflow_state_name")
				or data.get("workflow_action_name")
				or data.get("workflow_name")
			)
			if frappe.db.exists(data["doctype"], name):
				doc = frappe.get_doc(data["doctype"], name)
				doc.update({key: value for key, value in data.items() if key not in {"doctype", "name"}})
				doc.save()
			else:
				frappe.get_doc(data).insert()
