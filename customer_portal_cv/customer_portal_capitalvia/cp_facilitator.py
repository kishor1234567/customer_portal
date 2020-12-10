# -*- coding: utf-8 -*-
# Copyright (c) 2020, GoElite and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import os
import redis
import ast
import json
import time
from frappe import msgprint, _
from frappe.utils import nowdate, get_first_day, get_last_day, formatdate, getdate, flt, get_files_path
from frappe.core.doctype.communication.email import make
from frappe.utils.pdf import get_pdf


class CpFacilitator():
    pass


def create_customer(doc, method):
    # add user
    if not frappe.db.exists("User", doc.email_id) == doc.email_id:
        email = doc.email_id
        first_name = doc.customer_name
        user = frappe.new_doc("User")
        user.update({
            "name": email,
            "email": email,
            "enabled": 1,
            "first_name": first_name or email,
            "user_type": "Website User",
            "send_welcome_email": 0
        })

        user.insert()

        roles = ["Customer"]
        user.add_roles(*roles)
        # send_welcome_mail_to_user(user)
        doc.disabled = 1
        doc.insert()

        # Contact Creation
        contact = frappe.new_doc("Contact")
        contact.update({
            "first_name": first_name or email,
            "email_id": email
        })
        contact.append('links', dict(
            link_doctype="Customer", link_name=doc.name))
        contact.flags.ignore_mandatory = True
        contact.insert(ignore_permissions=True)

        frappe.db.commit()


def send_welcome_mail_to_user(user):
    self = user
    from frappe.utils import get_url

    link = self.reset_password()
    link = convert_link(link)
    subject = None
    method = frappe.get_hooks("welcome_email")
    if method:
        subject = frappe.get_attr(method[-1])()
    if not subject:
        site_name = frappe.db.get_default(
            'site_name') or frappe.get_conf().get("site_name")
        if site_name:
            subject = _("Welcome to {0}").format(site_name)
        else:
            subject = _("Complete Registration")

    self.send_login_mail(subject, "new_user",
                         dict(
                             link=link,
                             site_url=get_url(),
                         ))


def convert_link(link):
    # original link https://staginghash.capitalvia.com/update-password?key=pC7VcW6a7VTGTsgfAb1zIytdMENknBAE
    # to link to https://staginghash.capitalvia.com/portal#/reset-password?key=pC7VcW6a7VTGTsgfAb1zIytdMENknBAE
    return link.replace("update", "portal#/reset")


@frappe.whitelist()
def customer_status_disabled():
    cust = frappe.get_list("Customer", filters={
                           "email_id": frappe.session.user}, fields=["name", "disabled"])
    if cust:
        return cust[0].disabled
    else:
        return 1


def hook_send_signal_notifications(doc, method):
    customer_list = frappe.get_list("Sales Invoice", filters=[["workflow_state", "in", ["Approved"]], ["from_date", "<=", nowdate()], [
        "end_date", ">=", nowdate()], ["item_name", "=", doc.service]],
        fields=['customer', 'name', 'customer_name', '`tabSales Invoice Item`.`item_name`'])

    email_list = []
    for e in customer_list:
        email_list.append(frappe.db.get_value(
            "Customer", e.customer, "email_id"))

    email_list.append("nick9822@gmail.com")

    for e in list(set(email_list)):
        frappe.publish_realtime(event="new_notifications", message={
            "type": "default", "message": doc.message}, user=e)

    frappe.publish_realtime(event="refresh_data",
                            message="fetchTradingSignals")


@frappe.whitelist()
def send_signal_notifications(message, recipients):
    if recipients != "[]":
        recipients = json.loads(recipients)
        email_list = frappe.db.sql("select cust.email_id from `tabCustomer` cust where cust.name in (%s)" % (
            ",".join(["%s"] * len(recipients))), tuple(recipients), as_list=True)

        email_list = [e[0] for e in email_list]
        email_list.append("nick9822@gmail.com")

        fcm_message = {
            "title": "New Signal",
            "body": message
        }
        fcm_data = {
            "route": "trading-signal"
        }

        frappe.enqueue(send_fcm_notifications, message=fcm_message,
                       data=fcm_data, email_list=email_list, queue='long', timeout=4000)

        for e in list(set(email_list)):
            frappe.publish_realtime(event="new_notifications", message={
                "type": "default", "message": message}, user=e)

        frappe.publish_realtime(event="refresh_data",
                                message="fetchTradingSignals")
    frappe.db.commit()


def send_fcm_notifications(message, data, email_list):
    from customer_portal_cv.customer_portal_capitalvia.fcm_utils import FcmUtils
    fcmObj = FcmUtils()

    tokens = frappe.db.sql("select devc.fcm_token from `tabCustomer Portal Devices` devc where devc.email in (%s)" % (
        ",".join(["%s"] * len(email_list))), tuple(email_list), as_list=True)
    tokens = [e[0] for e in tokens]

    res = fcmObj.send_multicast_notification(message, data, tokens)
    print(res.responses)
    for e in res.responses:
        print(e.message_id, e.exception)
    return res.responses
