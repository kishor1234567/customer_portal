# -*- coding: utf-8 -*-
# Copyright (c) 2020, CapitalVia and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class OfflinePayment(Document):
    def on_update_after_submit(self):
        if self.workflow_state == "Approved":
            if self.fee_request:
                frappe.db.set_value(
                    "Fee Request", self.fee_request, "status", "Success")
                frappe.db.commit()
