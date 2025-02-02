# Copyright (c) 2022, Datahenge LLC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from btu import Result, get_system_datetime_now
from btu.btu_core import btu_email

class BTUTaskLog(Document):

	def after_insert(self):

		# Update the "Last Result" column on the BTU Task.
		frappe.db.set_value("BTU Task", self.task, "last_runtime", get_system_datetime_now())

		try:
			btu_email.email_task_log_summary(self)
		except Exception as ex:
			message = "Error in BTU Task Log while attempting to send email about Task Log."
			message += f"\n{str(ex)}\n"
			frappe.msgprint(message)
			print(message)
			frappe.set_value("BTU Task Log", self.name, "stdout", message + (self.stdout or ""))


def write_log_for_task(task_id, result, stdout=None, date_time_started=None, schedule_id=None):
	"""
	Given a Task and Result, write to SQL table 'BTU Task Log'
	References:
		* btu_task.run_task_on_webserver()
		* TaskRunner().function_wrapper()
	"""

	# Important Fields in BTU Task Log:
	#     1.  task
	#     2.  task_desc_short
	#     3.  execution_time
	#     4.  stdout
	#     5.  schedule
	#     6.  result_message
	#     7.  success_fail
	#     8. date_time_started

	if not isinstance(result, Result):
		raise ValueError(f"Argument 'result' should be an instance of BTU class 'Result'. Found '{type(result)}' instead.")
	if stdout and not isinstance(stdout, str):
		raise ValueError(f"Argument 'stdout' should be a Python string.  Found '{type(result)}' instead.")

	new_log = frappe.new_doc("BTU Task Log")  # Create a new Log.
	new_log.task = task_id  # Field 1
	new_log.task_desc_short = frappe.get_doc("BTU Task", task_id).desc_short  # Field 2.
	if result.execution_time:
		new_log.execution_time = result.execution_time  # Field 3
	new_log.stdout = stdout  # Field 4
	if schedule_id:
		new_log.schedule = schedule_id  # Field 5
	new_log.result_message = result.message  # Field 6
	if result.okay:
		new_log.success_fail = 'Success'
	else:
		new_log.success_fail = 'Failed'  # Field 7
	if 	date_time_started:
		new_log.date_time_started = date_time_started  # Field 8

	# NOTE: Calling new_log.insert() will --not-- trigger Document class controller methods, like 'after_insert'
	#       Use save() instead.
	new_log.save(ignore_permissions=True)  # Not even System Administrators are supposed to create and save these.
	frappe.db.commit()
	return new_log.name


@frappe.whitelist()
def delete_logs_by_dates(from_date, to_date):
	"""
	Delete records in 'BTU Task Log' where execution date is between a date range.
	"""

	# Count the rows first, so we can return this value to the web page.
	sql_statement = """ SELECT count(*) as RowCount FROM `tabBTU Task Log`
	                    WHERE DATE(date_time_started) between %(from_date)s and %(to_date)s """

	result = frappe.db.sql(sql_statement,
	                       values={"from_date": from_date, "to_date": to_date},
				           debug=False,
				           explain=False)
	rows_to_delete = result[0][0]

	# Delete the rows:
	sql_statement = """ DELETE FROM `tabBTU Task Log`
	                    WHERE DATE(date_time_started) between %(from_date)s and %(to_date)s """
	frappe.db.sql(sql_statement,
	              values={"from_date": from_date, "to_date": to_date},
				  auto_commit=True)

	return rows_to_delete
