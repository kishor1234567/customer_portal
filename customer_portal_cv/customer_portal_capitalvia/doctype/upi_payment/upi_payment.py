# -*- coding: utf-8 -*-
# Copyright (c) 2020, CapitalVia and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.core.doctype.communication.email import make


class UPIPayment(Document):
    def before_insert(self):
        self.set_customer_sp()

    def set_customer_sp(self):
        user_info = frappe.db.sql("""
        select
            cust.name,
			cust.sales_person,
			cust.customer_name
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
        where
            user.name = '{0}'
    	""".format(self.owner), as_dict=True)
        if user_info:
            self.customer = user_info[0].name
            self.sales_person = user_info[0].sales_person
            self.customer_name = user_info[0].customer_name

    def on_update_after_submit(self):
        if self.workflow_state == "Approved":
            self.send_email_sp()

    def send_email_sp(self):
        sp_email = frappe.db.sql("""
		select
			sp_user.email
		from
			`tabSales Person` sp
			left join `tabEmployee` emp on emp.name = sp.employee
			left join `tabUser` sp_user on sp_user.name = emp.user_id
		where
			sp.name = '{0}'
			""".format(self.sales_person), as_dict=True)
        sp_email = sp_email[0].email if sp_email and sp_email[0].email else ""
        sub = "Approved Payment {0}".format(self.customer)
        msg = "Payment of your Customer {0} is approved.".format(
            self.customer)
        make(content=msg, subject=sub, sender="alert@capitalvia.com", sender_full_name="Alerts by CapitalVia",
             recipients=sp_email, communication_medium="Email", send_email=True)
