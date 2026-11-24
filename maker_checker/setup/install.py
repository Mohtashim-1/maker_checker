"""Create Document Maker / Document Checker roles and approval workflows."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

ROLES = ("Document Maker", "Document Checker")

# Transactional DocTypes covered by maker-checker
DOC_TYPES = (
	# Accounts / Sales
	"Sales Invoice",
	"Payment Entry",
	"Journal Entry",
	"Sales Order",
	"Delivery Note",
	"Payment Request",
	# Purchase
	"Purchase Invoice",
	"Purchase Order",
	"Purchase Receipt",
	# Stock
	"Stock Entry",
	# HR (if HRMS installed)
	"Expense Claim",
)

WORKFLOW_STATES = (
	("Draft", "0", "Primary"),
	("Pending Approval", "0", "Warning"),
	("Approved", "1", "Success"),
	("Rejected", "0", "Danger"),
)

ACTIONS = (
	"Submit for Approval",
	"Approve",
	"Reject",
)


def after_install():
	_ensure_roles()
	_ensure_workflow_masters()
	for dt in DOC_TYPES:
		try:
			_ensure_custom_fields_for(dt)
			_ensure_workflow(dt)
			_grant_role_permissions_for(dt)
		except Exception:
			frappe.log_error(title=f"Maker Checker setup failed: {dt}")
	frappe.clear_cache()


def after_migrate():
	after_install()


def _ensure_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def _insert_after_for(dt: str) -> str | None:
	"""Pick a stable field without requiring a fully valid DocType meta."""
	for candidate in ("amended_from", "remarks", "title", "naming_series"):
		if frappe.db.exists("DocField", {"parent": dt, "fieldname": candidate}) or frappe.db.exists(
			"Custom Field", {"dt": dt, "fieldname": candidate}
		):
			return candidate
	return None


def _ensure_custom_fields_for(dt: str):
	"""Rejection reason helper on one DocType."""
	if not frappe.db.exists("DocType", dt):
		return
	if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": "mc_rejection_reason"}):
		return
	insert_after = _insert_after_for(dt)
	section = {
		"fieldname": "maker_checker_section",
		"fieldtype": "Section Break",
		"label": "Maker / Checker",
		"collapsible": 1,
	}
	if insert_after:
		section["insert_after"] = insert_after
	create_custom_fields(
		{
			dt: [
				section,
				{
					"fieldname": "mc_rejection_reason",
					"fieldtype": "Small Text",
					"label": "Rejection Reason",
					"insert_after": "maker_checker_section",
					"depends_on": "eval:doc.workflow_state=='Rejected' || doc.workflow_state=='Pending Approval'",
				},
			]
		},
		update=True,
	)


def _ensure_workflow_masters():
	for state, _doc_status, style in WORKFLOW_STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": state, "style": style}
			).insert(ignore_permissions=True)
		else:
			# keep style updated lightly
			pass
	for action in ACTIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": action}
			).insert(ignore_permissions=True)


def _workflow_name(dt: str) -> str:
	return f"{dt} Maker Checker"


def _ensure_workflow(dt: str):
	if not frappe.db.exists("DocType", dt):
		return
	# Only submittable DocTypes can use Approved = docstatus 1
	if not frappe.db.get_value("DocType", dt, "is_submittable"):
		return

	name = _workflow_name(dt)
	# Only create once — do not wipe in-flight approvals on migrate
	if frappe.db.exists("Workflow", name):
		# Ensure active
		frappe.db.set_value("Workflow", name, "is_active", 1)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": name,
			"document_type": dt,
			"is_active": 1,
			"override_status": 0,
			"send_email_alert": 1,
			"workflow_state_field": "workflow_state",
			"states": [
				{
					"state": "Draft",
					"doc_status": "0",
					"allow_edit": "Document Maker",
				},
				{
					"state": "Draft",
					"doc_status": "0",
					"allow_edit": "Document Checker",
				},
				{
					"state": "Draft",
					"doc_status": "0",
					"allow_edit": "Accounts User",
				},
				{
					"state": "Draft",
					"doc_status": "0",
					"allow_edit": "Accounts Manager",
				},
				{
					"state": "Draft",
					"doc_status": "0",
					"allow_edit": "System Manager",
				},
				{
					"state": "Pending Approval",
					"doc_status": "0",
					"allow_edit": "Document Checker",
				},
				{
					"state": "Pending Approval",
					"doc_status": "0",
					"allow_edit": "Accounts Manager",
				},
				{
					"state": "Pending Approval",
					"doc_status": "0",
					"allow_edit": "System Manager",
				},
				{
					"state": "Approved",
					"doc_status": "1",
					"allow_edit": "Accounts Manager",
				},
				{
					"state": "Approved",
					"doc_status": "1",
					"allow_edit": "System Manager",
				},
				{
					"state": "Rejected",
					"doc_status": "0",
					"allow_edit": "Document Maker",
				},
				{
					"state": "Rejected",
					"doc_status": "0",
					"allow_edit": "Document Checker",
				},
				{
					"state": "Rejected",
					"doc_status": "0",
					"allow_edit": "System Manager",
				},
			],
			"transitions": [
				{
					"state": "Draft",
					"action": "Submit for Approval",
					"next_state": "Pending Approval",
					"allowed": "Document Maker",
					"allow_self_approval": 1,
				},
				{
					"state": "Draft",
					"action": "Submit for Approval",
					"next_state": "Pending Approval",
					"allowed": "Accounts User",
					"allow_self_approval": 1,
				},
				{
					"state": "Draft",
					"action": "Submit for Approval",
					"next_state": "Pending Approval",
					"allowed": "System Manager",
					"allow_self_approval": 1,
				},
				{
					"state": "Rejected",
					"action": "Submit for Approval",
					"next_state": "Pending Approval",
					"allowed": "Document Maker",
					"allow_self_approval": 1,
				},
				{
					"state": "Rejected",
					"action": "Submit for Approval",
					"next_state": "Pending Approval",
					"allowed": "System Manager",
					"allow_self_approval": 1,
				},
				{
					"state": "Pending Approval",
					"action": "Approve",
					"next_state": "Approved",
					"allowed": "Document Checker",
					"allow_self_approval": 0,
				},
				{
					"state": "Pending Approval",
					"action": "Approve",
					"next_state": "Approved",
					"allowed": "Accounts Manager",
					"allow_self_approval": 0,
				},
				{
					"state": "Pending Approval",
					"action": "Approve",
					"next_state": "Approved",
					"allowed": "System Manager",
					"allow_self_approval": 1,
				},
				{
					"state": "Pending Approval",
					"action": "Reject",
					"next_state": "Rejected",
					"allowed": "Document Checker",
					"allow_self_approval": 0,
					"condition": "doc.mc_rejection_reason",
				},
				{
					"state": "Pending Approval",
					"action": "Reject",
					"next_state": "Rejected",
					"allowed": "Accounts Manager",
					"allow_self_approval": 0,
					"condition": "doc.mc_rejection_reason",
				},
				{
					"state": "Pending Approval",
					"action": "Reject",
					"next_state": "Rejected",
					"allowed": "System Manager",
					"allow_self_approval": 1,
					"condition": "doc.mc_rejection_reason",
				},
			],
		}
	)
	doc.insert(ignore_permissions=True)


def _grant_role_permissions_for(dt: str):
	"""Ensure Maker/Checker can work on one DocType (alongside standard roles)."""
	_upsert_perm(
		dt,
		"Document Maker",
		create=1,
		read=1,
		write=1,
		print=1,
		email=1,
		report=1,
		export=1,
		share=1,
	)
	_upsert_perm(
		dt,
		"Document Checker",
		create=0,
		read=1,
		write=1,
		submit=1,
		cancel=1,
		print=1,
		email=1,
		report=1,
		export=1,
		share=1,
	)


def _upsert_perm(doctype: str, role: str, **rights):
	"""Add Custom DocPerm if role has no row yet."""
	exists = frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role})
	if exists:
		return
	# Also skip if standard DocPerm already covers it
	if frappe.db.exists("DocPerm", {"parent": doctype, "role": role}):
		return
	perm = {"doctype": "Custom DocPerm", "parent": doctype, "parenttype": "DocType", "parentfield": "permissions", "role": role}
	perm.update(
		{
			"read": rights.get("read", 0),
			"write": rights.get("write", 0),
			"create": rights.get("create", 0),
			"delete": rights.get("delete", 0),
			"submit": rights.get("submit", 0),
			"cancel": rights.get("cancel", 0),
			"amend": rights.get("amend", 0),
			"print": rights.get("print", 0),
			"email": rights.get("email", 0),
			"report": rights.get("report", 0),
			"export": rights.get("export", 0),
			"share": rights.get("share", 0),
		}
	)
	try:
		frappe.get_doc(perm).insert(ignore_permissions=True)
	except Exception:
		# Fallback: update DocType permissions via apply
		frappe.clear_cache(doctype=doctype)
