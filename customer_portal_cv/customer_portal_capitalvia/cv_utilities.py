# -*- coding: utf-8 -*-
# Copyright (c) 2020, GoElite and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import requests
import os
import redis
import ast
import json
import time
import base64
from frappe import msgprint, _
from frappe.utils import nowdate, get_first_day, get_last_day, formatdate, getdate, flt, get_files_path
from frappe.core.doctype.communication.email import make
from frappe.utils.pdf import get_pdf
from PyPDF2 import PdfFileWriter


class CvUtilities():
    pass


def check_permissions():
    if frappe.session.user == 'Guest':
        frappe.throw(
            _("You need to be logged in to access this page"), frappe.PermissionError)
    else:
        return frappe.session.user


@frappe.whitelist()
def get_personal_info():
    user = check_permissions()
    user_info = frappe.db.sql("""
        select
            cust.name as customer_id,
            lead.lead_name,
            lead.last_name,
            user.name as email_id,
            lead.primary_mobile,
            lead.date_of_birth,
            lead.pan_number,
            lead.risk_appetite as rpm,
            sp.sales_person_name as relationship_manager,
            addr.city,
            addr.state,
            lead.country
        from
            `tabUser` user
            left join `tabLead` lead on lead.email_id = user.name
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabDynamic Link` dl on (
                dl.link_name = cust.name
                and dl.link_doctype = 'Customer'
                and dl.parenttype = 'Address'
            )
            left join `tabAddress` addr on addr.name = dl.parent
            left join `tabSales Person` sp on sp.name = cust.sales_person
        where
            user.name = '{0}'
    """.format(user), as_dict=True)
    return user_info[0] if user_info else {}


@frappe.whitelist()
def get_risk_profile():
    user = check_permissions()
    risk_profile = frappe.db.sql("""
        select
            rf.name,
            rf.investment_amount,
            rf.risk_appetite,
            rf.reason,
            rf.creation
        from
            `tabUser` user
            left join `tabLead` lead on lead.email_id = user.name
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabRisk Profile` rf on (
                rf.document_number = cust.name
                or rf.document_number = lead.name
            )
        where
            user.name = '{0}'
        order by rf.creation desc
    """.format(user), as_dict=True)
    return risk_profile if risk_profile and risk_profile[0].name else []


@frappe.whitelist()
def get_subscriptions():
    user = check_permissions()
    subscriptions = frappe.db.sql("""
        select
            si.name,
            si.posting_date as date,
            sii.item_name as plan,
            si.currency,
            si.grand_total,
            si.from_date,
            si.to_date
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSales Invoice` si on si.customer = cust.name
            left join `tabSales Invoice Item` sii on sii.parent = si.name
        where
            user.name = '{0}'
        order by si.posting_date desc
    """.format(user), as_dict=True)
    return subscriptions if subscriptions and subscriptions[0].name else []


@frappe.whitelist()
def get_trading_signals():
    user = check_permissions()
    trading_signals = frappe.db.sql("""
        select
            sig.name,
            sig.category,
            sig.service_option_equity,
            sig.service_option_commodity,
            sig.service_option_forex,
            sig.action,
            sig.script_name,
            sig.status,
            sig.service,
            sig.entry_lots,
            sig.min_entry_price,
            sig.max_entry_price,
            sig.target_price,
            sig.entry_date,
            sl.creation,
            sig.fumsg1,
            sig.fumsg1_time,
            sig.fumsg2,
            sig.fumsg2_time,
            sig.fumsg3,
            sig.fumsg3_time,
            sig.fumsg4,
            sig.fumsg4_time,
            sig.message
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSignal Logs` sl on sl.customer = cust.name
            left join `tabSignalify` sig on sig.name = sl.signal
            left join `tabSignal Draft` sig_draft on sig_draft.name = sig.draft
        where
            user.name = '{0}' and sl.creation is not null and sig.name is not null
        order by sl.creation desc
    """.format(user), as_dict=True)
    return trading_signals if trading_signals and trading_signals[0].name else []


@frappe.whitelist()
def get_tickets():
    user = check_permissions()
    tickets = frappe.db.sql("""
        select
            issue.name,
            issue.subject,
            issue.status,
            issue.issue_type,
            todo.owner as assign,
            issue.modified
        from
            `tabUser` user
            left join `tabIssue` issue on issue.raised_by = user.name
            left join `tabToDo` todo on todo.reference_name = issue.name
        where
            user.name = '{0}'
        order by issue.creation desc
    """.format(user), as_dict=True)
    return tickets if tickets and tickets[0].name else []


@frappe.whitelist()
def get_ratings():
    user = check_permissions()
    ratings = frappe.db.sql("""
        select
            csat.creation as created,
            csat.rating,
            csat.feedback
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabCSAT` csat on csat.document_name = cust.name
        where
            user.name = '{0}'
        order by csat.creation desc
    """.format(user), as_dict=True)
    return ratings if ratings and ratings[0].rating else []


@frappe.whitelist()
def get_announcements():
    user = check_permissions()
    announcements = frappe.db.sql("""
        select
            note.title,
            note.url,
            note.content as message,
            "info" as type,
            note.creation as created,
            note.offers
        from
            `tabNote` note
        where note.public = 1
        order by note.creation desc
    """, as_dict=True)
    return announcements if announcements else []


@frappe.whitelist()
def get_upi_payments():
    user = check_permissions()
    payments = frappe.db.sql("""
        select
            pay.modified,
            pay.vpa_address,
            pay.upi_transaction_reference_id,
            pay.amount
        from
            `tabUPI Payment` pay
        where
            pay.owner = '{0}'
            and pay.transaction_status = 'SUCCESS'
        order by pay.modified desc
    """.format(user), as_dict=True)
    return payments if payments else []


@frappe.whitelist()
def post_ticket():
    user = check_permissions()
    full_name, sub, msg = frappe.form_dict.get('fullName'), frappe.form_dict.get(
        'subject'), frappe.form_dict.get('message')

    make(content=msg, subject=sub, sender="alerts@capitalvia.com", sender_full_name=full_name,
         recipients="support@capitalvia.com", communication_medium="Email", send_email=True)
    frappe.publish_realtime(event="new_notifications", message={
                            "type": "default", "message": "Your ticket is posted and will soon be reflected here."}, user=frappe.session.user)
    return "Success"


@frappe.whitelist()
def get_html_test(data):
    user = check_permissions()
    html = frappe.get_print("Project", "Testing", "Standard")
    return html


@frappe.whitelist()
def post_rating():
    try:
        user = check_permissions()
        customer = frappe.db.sql("""
            select
                cust.name,
                cust.sales_person
            from
                `tabUser` user
                left join `tabCustomer` cust on cust.email_id = user.name
            where
                user.name = '{0}'
            """.format(user), as_dict=True)
        full_name, rating, comments, satisfaction, rating_service, rating_cam = frappe.form_dict.get('fullName'), frappe.form_dict.get(
            'rating'), frappe.form_dict.get('comments'), frappe.form_dict.get('satisfactionLevel'), frappe.form_dict.get('serviceRating'), frappe.form_dict.get('spRating')
        word_ratings = {
            "5": "Excellent",
            "4": "Good",
            "3": "Average",
            "2": "Below Average",
            "1": "Poor"
        }
        doc = frappe.get_doc({
            "doctype": "CSAT",
            "customer_name": full_name,
            "rating": word_ratings.get(str(rating), "") if rating else "",
            "rating_for_service": word_ratings.get(str(rating_service), "") if rating_service else "",
            "rating_for_cam": word_ratings.get(str(rating_cam), "") if rating_cam else "",
            "feedback_status": satisfaction,
            "feedback": comments,
            "document_type": "Customer",
            "document_name": customer[0].name,
            "sales_person": customer[0].sales_person
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.publish_realtime(event="refresh_data",
                                message="fetchMyRatings", user=user)
        frappe.publish_realtime(event="new_notifications", message={
                                "type": "default", "message": "Thank you for your ratings."}, user=user)
        return "Success"
    except Exception as e:
        frappe.log_error(e)


@ frappe.whitelist()
def test_socket():
    check_permissions()
    frappe.publish_realtime("refresh_data", "fetchMySubscriptions")
    frappe.publish_realtime("new_notifications", {
                            "type": "default", "message": "This is a test notification"})
    return "Done"


@ frappe.whitelist()
def googly_post():
    token = frappe.sessions.get_csrf_token()
    frappe.publish_realtime(event="spinner_code",
                            message={"sid": frappe.local.session.sid,
                                     "csrf_token": token},
                            user=frappe.session.user)


@ frappe.whitelist()
def googly_http_post():
    token = frappe.sessions.get_csrf_token()
    return token


@ frappe.whitelist()
def get_trading_signal():
    user = check_permissions()
    signal = frappe.form_dict.get('signal')
    trading_signals = frappe.db.sql("""
        select
            sig.name,
            sig.category,
            sig.service_option_equity,
            sig.service_option_commodity,
            sig.service_option_forex,
            sig.action,
            sig.script_name,
            sig.status,
            sig.entry_lots,
            sig.min_entry_price,
            sig.max_entry_price,
            sig.target_price,
            sig.entry_date,
            sl.creation,
            sig.service,
            sig.fumsg1,
            sig.fumsg1_time,
            sig.fumsg2,
            sig.fumsg2_time,
            sig.fumsg3,
            sig.fumsg3_time,
            sig.fumsg4,
            sig.fumsg4_time,
            sig.message
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSignal Logs` sl on sl.customer = cust.name
            left join `tabSignalify` sig on sig.name = sl.signal
            left join `tabSignal Draft` sig_draft on sig_draft.name = sig.draft
        where
            user.name = '{0}' and sig.name='{1}'
    """.format(user, signal), as_dict=True)
    return trading_signals if trading_signals else []


@ frappe.whitelist()
def get_trading_signals_stats():
    user = check_permissions()
    signal_stats = frappe.db.sql("""
        select
            UNIX_TIMESTAMP(DATE(sl.creation)) as datestamp,
            count(sig.name) as no_of_signals
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSignal Logs` sl on sl.customer = cust.name
            left join `tabSignalify` sig on sig.name = sl.signal
        where
            user.name = '{0}' and sl.creation is not null and sig.name is not null
        group by DATE(sl.creation)
        order by sl.creation desc
    """.format(user), as_dict=True)

    signal_cat_stats = frappe.db.sql("""
        select
            sig.category,
            count(sig.name) as no_of_signals
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSignal Logs` sl on sl.customer = cust.name
            left join `tabSignalify` sig on sig.name = sl.signal
        where
            user.name = '{0}' and sl.creation is not null and sig.name is not null
        group by sig.category
        order by sl.creation desc
    """.format(user), as_dict=True)
    return signal_stats, signal_cat_stats


@ frappe.whitelist()
def get_invoice_download_link():
    user = check_permissions()
    sinv = frappe.form_dict.get('sinv')
    if sinv:
        invoices = frappe.db.sql("""
            select
                si.name
            from
                `tabUser` user
                left join `tabCustomer` cust on cust.email_id = user.name
                left join `tabSales Invoice` si on si.customer = cust.name
                left join `tabSales Invoice Item` sii on sii.parent = si.name
            where
                user.name = '{0}' and si.name = '{1}'
            order by si.posting_date desc
        """.format(user, sinv), as_dict=True)

        if invoices:
            hash_secret = frappe.generate_hash(sinv, 16)
            frappe.cache().set_value(hash_secret, sinv)
            frappe.enqueue(_call_through, action="SALES_INVOICE", args=frappe._dict({
                'sinv': sinv,
                'fid': hash_secret,
                'iuser': user
            }), queue='short', timeout=4000)
            return hash_secret
        else:
            return "Invalid Invoice"
    else:
        return "Invalid Invoice"


def _call_through(action, args):
    frappe.set_user("Administrator")
    if action == "SALES_INVOICE":
        frappe.enqueue("customer_portal_cv.customer_portal_capitalvia.cv_utilities.create_invoice_pdf",
                       sinv=args.sinv, fid=args.fid, iuser=args.iuser, queue='short', timeout=4000)
    if action == "CALLBACK_UPI":
        frappe.enqueue("customer_portal_cv.customer_portal_capitalvia.cv_utilities.callback_upi_wrapper",
                       meRes=args.meRes, pgMerchantId=args.pgMerchantId, queue='short', timeout=4000)


def create_invoice_pdf(sinv, fid, iuser):
    file_path = get_files_path("portal-files")
    frappe.create_folder(file_path)
    output = PdfFileWriter()
    output = frappe.get_print(
        "Sales Invoice", sinv, "standard", as_pdf=True, output=output)
    file = os.path.join(file_path, "{0}.pdf".format(fid))
    output.write(open(file, "wb"))
    frappe.publish_realtime(event="invoice_ready",
                            message={"sub": sinv,
                                     "dict": {"bgCompleted": 1, "fid": fid}},
                            user=iuser)
    frappe.publish_realtime("new_notifications", {
                            "type": "default", "message": "PDF for Invoice# {sub} is available to download.".format(sub=sinv)}, user=iuser)


@ frappe.whitelist()
def get_risk_profile_each():
    user = check_permissions()
    rf = frappe.form_dict.get('rf')
    risk_profile = frappe.db.sql("""
        select
            rf.reason,
            rf.risk_appetite,
            rf.annual_income,
            rf.investment_objective,
            rf.risk_score,
            rf.risk_appetite,
            rf.document_type,
            rf.age_group,
            rf.drop_value,
            rf.assets,
            rf.liabilities,
            rf.debts,
            rf.investment_duration,
            rf.income_security,
            rf.life_stage,
            rf.investment_amount,
            rf.investment_horizon,
            rf.understanding,
            rf.creation
        from
            `tabUser` user
            left join `tabLead` lead on lead.email_id = user.name
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabRisk Profile` rf on (
                rf.document_number = cust.name
                or rf.document_number = lead.name
            )
        where
            user.name = '{0}' and rf.name = '{1}'
        order by rf.creation desc
    """.format(user, rf), as_dict=True)
    return risk_profile if risk_profile else []


@ frappe.whitelist()
def get_tickets_each():
    user = check_permissions()
    ticket = frappe.form_dict.get('ticket')
    tickets = frappe.db.sql("""
        select
            issue.name,
            issue.subject,
            issue.status,
            issue.issue_type,
            todo.owner as assign,
            issue.modified,
            com.subject,
            com.content as message,
            com.sender,
            com.recipients
        from
            `tabUser` user
            left join `tabIssue` issue on issue.raised_by = user.name
            left join `tabToDo` todo on todo.reference_name = issue.name
            left join `tabCommunication` com on com.reference_name = issue.name
        where
            user.name = '{0}' and issue.name='{1}'
        order by com.creation desc
    """.format(user, ticket), as_dict=True)
    return tickets if tickets else []


@ frappe.whitelist()
def post_referrals():
    user = check_permissions()
    full_name, addresses = frappe.form_dict.get(
        'fullName'), frappe.form_dict.get('email_addresses')
    sub = "You are invited to CapitalVia by {0}".format(full_name)
    msg = """Hello! <br>
            Congratulations! you have been refereed by {0}. <br>
            To start using CapitalVia's Service signup here - https://www.capitalvia.com/offers""".format(full_name)

    make(content=msg, subject=sub, sender="alerts@capitalvia.com", sender_full_name=full_name,
         recipients=addresses, communication_medium="Email", send_email=True)
    frappe.publish_realtime(event="new_notifications", message={
                            "type": "default", "message": "Thank you for your referrals."}, user=frappe.session.user)
    frappe.db.commit()
    return "Success"


@ frappe.whitelist()
def initiate_payment():
    user = check_permissions()
    vpa_address, amount, upi_link, fee_request = frappe.form_dict.get(
        'vpa_address'), frappe.form_dict.get('amount'), frappe.form_dict.get('upiLink'), frappe.form_dict.get('fee_request')

    fcm_token = frappe.form_dict.get('fcm_token', None)

    from customer_portal_cv.customer_portal_capitalvia.upi_payment import UPIPayment
    payobj = UPIPayment()
    data = payobj.initiate_payment(
        vpa_address, amount, upi_link, fee_request, fcm_token)
    return data


@ frappe.whitelist(allow_guest=True)
def callback_upi(meRes, pgMerchantId):
    #queue_slack_notification("Callback received")
    frappe.enqueue(_call_through, action="CALLBACK_UPI", args=frappe._dict({
        'meRes': meRes,
        'pgMerchantId': pgMerchantId
    }), queue='short', timeout=4000)
    return "Success"


def callback_upi_wrapper(meRes, pgMerchantId):
    from customer_portal_cv.customer_portal_capitalvia.upi_payment import callback_payment

    from customer_portal_cv.customer_portal_capitalvia.fcm_utils import FcmUtils
    fcmObj = FcmUtils()

    upi_erp_id, result = callback_payment(meRes, pgMerchantId)
    upi_pay_doc = frappe.get_doc("UPI Payment", upi_erp_id)
    owner = upi_pay_doc.owner
    qr_req = upi_pay_doc.collection_request_status

    if result == "SUCCESS":
        frappe.publish_realtime("payment_status", {
            "upi_erp_id": upi_erp_id, "result": "SUCCESS"})
        frappe.publish_realtime(event="new_notifications", message={
            "type": "default", "message": "Your last payment was successful. Thank you for your payment."}, user=owner)
        if qr_req == "QR OR DEEP LINKING INITIATED":
            frappe.publish_realtime(event="qr_notification", message={
                "type": "default", "message": "Your last payment of Rs. {} was successful. Thank you for your payment.".format(upi_pay_doc.amount)}, user=owner)
        if upi_pay_doc.fee_request:
            # Update fee request with paydoc is still to be done
            frappe.db.set_value(
                "Fee Request", upi_pay_doc.fee_request, "upi_payment", upi_pay_doc.name)
            frappe.db.set_value(
                "Fee Request", upi_pay_doc.fee_request, "status", "Success")
            frappe.db.commit()

            if upi_pay_doc.fcm_token:
                fcmObj.send_single_notification(
                    message={
                        "title": "Payment Successful",
                        "body": "Your last payment of Rs. {} was successful. Thank you for your payment.".format(upi_pay_doc.amount)
                    },
                    data={
                        "route": "payment",
                        "payment_state": "SUCCESS"
                    },
                    token=upi_pay_doc.fcm_token
                )
    else:
        frappe.publish_realtime("payment_status", {
            "upi_erp_id": upi_erp_id, "result": "TRY AGAIN"})
        frappe.publish_realtime(event="new_notifications", message={
            "type": "default", "message": "Your last payment was unsuccessful. Please try again."}, user=owner)

        if upi_pay_doc.fcm_token:
            fcmObj.send_single_notification(
                message={
                    "title": "Payment Unsuccessful",
                    "body": "Your last payment was unsuccessful. Please try again."
                },
                data={
                    "route": "payment",
                    "payment_state": "FAILED"
                },
                token=upi_pay_doc.fcm_token
            )
    return "Success"


@ frappe.whitelist(allow_guest=True)
def reset_password():
    user = frappe.form_dict.get("user")

    user = frappe.get_doc("User", user)
    from frappe.utils import random_string, get_url

    try:
        rate_limit = frappe.db.get_single_value(
            "System Settings", "password_reset_limit")
    except:
        rate_limit = None

    if rate_limit:
        frappe.core.doctype.user.user.check_password_reset_limit(
            user.name, rate_limit)

    key = random_string(32)
    user.db_set("reset_password_key", key)

    url = "/update-password?key=" + key

    link = get_url(url)
    new_link = link.replace("update", "portal#/reset")

    user.password_reset_mail(new_link)

    if rate_limit:
        frappe.core.doctype.user.user.update_password_reset_limit(user.name)
    return new_link


@ frappe.whitelist()
def get_latest_announcement():
    user = check_permissions()
    announcements = frappe.db.sql("""
        select
            note.title,
            note.url,
            note.content as message,
            "info" as type,
            note.creation as created,
            note.offers
        from
            `tabNote` note
        where note.public = 1
        order by note.creation desc
        limit 1
    """, as_dict=True)
    return announcements[0] if announcements and announcements[0].message else []


@ frappe.whitelist()
def get_latest_trading_signal():
    user = check_permissions()
    trading_signals = frappe.db.sql("""
        select
            sig.name,
            0 as rx,
            sig.action,
            sig.fumsg1,
            sig.fumsg1_time,
            sig.fumsg2,
            sig.fumsg2_time,
            sig.fumsg3,
            sig.fumsg3_time,
            sig.fumsg4,
            sig.fumsg4_time,
            sig.message as message,
            sl.creation as creation,
            sig.script_name,
            sig.min_entry_price,
            sig.max_entry_price,
            sig.target_price,
            sig.entry_lots as quantity,
            "" as action_notes
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSignal Logs` sl on sl.customer = cust.name
            left join `tabSignalify` sig on sig.name = sl.signal
            left join `tabSignal Draft` sig_draft on sig_draft.name = sig.draft
        where
            user.name = '{0}' and sl.creation is not null and sig.name is not null
        
        union

        select
            rx.name,
            1 as rx,
            rx_chd.action,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            case
                when rx_chd.idx = 1 THEN rx.recommendation_1
                when rx_chd.idx = 2 THEN rx.recommendation_2
                when rx_chd.idx = 3 THEN rx.recommendation_3
                when rx_chd.idx = 4 THEN rx.recommendation_4
                when rx_chd.idx = 5 THEN rx.recommendation_5
                when rx_chd.idx = 6 THEN rx.recommendation_6
                else ""
            end as message,
            sl.creation as creation,
            "",
            0.00,
            0.00,
            0.00,
            0.00,
            item.action_notes as action_notes
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSignal Logs` sl on sl.customer = cust.name
            left join `tabRX` rx on rx.name = sl.rx_id
            left join `tabSX Table` rx_chd on rx_chd.parent = rx.name
            left join `tabItem` item on item.name = rx.product
        where
            user.name = '{0}' and sl.creation is not null and rx.name is not null
        order by creation desc limit 1
    """.format(user), as_dict=True)
    return trading_signals[0] if trading_signals and trading_signals[0].name and trading_signals[0].creation else {}


@ frappe.whitelist()
def get_trading_signal_stats_mobile():
    user = check_permissions()
    trading_signals_stats = frappe.db.sql("""
        select
            sig.category,
            count(sig.name) as noOfCalls
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSignal Logs` sl on sl.customer = cust.name
            left join `tabSignalify` sig on sig.name = sl.signal
            left join `tabSignal Draft` sig_draft on sig_draft.name = sig.draft
        where
            user.name = '{0}' and sl.creation is not null and sig.name is not null
        group by sig.category
    """.format(user), as_dict=True)
    return trading_signals_stats if trading_signals_stats and trading_signals_stats[0].category else {}


@ frappe.whitelist()
def get_trading_signals_mobile():
    user = check_permissions()
    trading_signals = frappe.db.sql("""
        select
            sig.name,
            0 as rx,
            sig.action,
            sig.fumsg1,
            sig.fumsg1_time,
            sig.fumsg2,
            sig.fumsg2_time,
            sig.fumsg3,
            sig.fumsg3_time,
            sig.fumsg4,
            sig.fumsg4_time,
            sig.service,
            sig.message as message,
            sl.creation as creation,
            sl.name as signal_log_name,
            sl.executed,
            sig.script_name,
            sig.min_entry_price,
            sig.max_entry_price,
            sig.target_price,
            sig.entry_lots as quantity,
            "" as action_notes,
            sig.net_profit as profit
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSignal Logs` sl on sl.customer = cust.name
            left join `tabSignalify` sig on sig.name = sl.signal
            left join `tabSignal Draft` sig_draft on sig_draft.name = sig.draft
        where
            user.name = '{0}' and sl.creation is not null and sig.name is not null
        
        union

        select
            rx.name,
            rx.product,
            1 as rx,
            rx_chd.action,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            case
                when rx_chd.idx = 1 THEN rx.recommendation_1
                when rx_chd.idx = 2 THEN rx.recommendation_2
                when rx_chd.idx = 3 THEN rx.recommendation_3
                when rx_chd.idx = 4 THEN rx.recommendation_4
                when rx_chd.idx = 5 THEN rx.recommendation_5
                when rx_chd.idx = 6 THEN rx.recommendation_6
                else ""
            end as message,
            sl.creation as creation,
            sl.name as signal_log_name,
            sl.executed,
            "",
            0.00,
            0.00,
            0.00,
            0.00,
            item.action_notes as action_notes,
            rx_chd.net_profit as net_profit
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabSignal Logs` sl on sl.customer = cust.name
            left join `tabRX` rx on rx.name = sl.rx_id
            left join `tabSX Table` rx_chd on rx_chd.parent = rx.name
            left join `tabItem` item on item.name = rx.product
        where
            user.name = '{0}' and sl.creation is not null and rx.name is not null
        order by creation desc
    """.format(user), as_dict=True)
    return trading_signals if trading_signals and trading_signals[0].name and trading_signals[0].creation else []


# @frappe.whitelist()
# def get_trading_signals_mobile_each():
#     user = check_permissions()
#     signal = frappe.form_dict.get("signal")
#     trading_signals = frappe.db.sql("""
#         select
#             sig.name,
#             sig.creation,
#             sig.script_name,
#             sig.action,
#             sig.fumsg1,
#             sig.fumsg1_time,
#             sig.fumsg2,
#             sig.fumsg2_time,
#             sig.fumsg3,
#             sig.fumsg3_time,
#             sig.fumsg4,
#             sig.fumsg4_time,
#             sig.message
#             sig.min_entry_price,
#             sig.max_entry_price,
#             sig.target_price
#         from
#             `tabSignalify`
#         where
#             sig.name = '{0}'
#     """.format(signal), as_dict=True)
#     return trading_signals if trading_signals and trading_signals[0].name else []

@ frappe.whitelist()
def get_open_fee_requests():
    user = check_permissions()
    fee_reqs = frappe.db.sql("""
        select
            fee.name,
            fee.amount,
            fee.document_number,
            fee.currency,
            fee.creation
        from
            `tabUser` user
            left join `tabCustomer` cust on cust.email_id = user.name
            left join `tabFee Request` fee on fee.document_number = cust.name
        where
            user.name = '{0}' and fee.document_type = 'Customer' and fee.status = 'Initiated' and fee.amount > 0
        order by fee.creation desc
    """.format(user), as_dict=True)
    return fee_reqs if fee_reqs and fee_reqs[0].name else []


@ frappe.whitelist()
def insert_device_info():
    user = check_permissions()
    device_make, op_sys, fcm_token = frappe.form_dict.get(
        'device_make'), frappe.form_dict.get('op_sys'), frappe.form_dict.get('fcm_token')

    if not frappe.db.exists("Customer Portal Devices", {"fcm_token": fcm_token, "email": user}):
        customer = frappe.db.sql("""
                    select
                        cust.name
                    from
                        `tabUser` user
                        left join `tabCustomer` cust on cust.email_id = user.name
                    where
                        user.name = '{0}'
                """.format(user), as_dict=True)

        customer = customer[0].name if customer else ""

        dev_doc = frappe.new_doc("Customer Portal Devices")
        dev_doc.device_make = device_make
        dev_doc.os = op_sys
        dev_doc.fcm_token = fcm_token
        dev_doc.customer = customer
        dev_doc.email = user
        dev_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return "Success"
    return "Already present"


@ frappe.whitelist()
def create_non_upi_payment():
    try:
        user = check_permissions()
        fee_request = frappe.form_dict.get('feeRequest')
        try:
            if 'filedata' in frappe.form_dict:
                uploaded_content = base64.b64decode(
                    frappe.form_dict.filedata)
                uploaded_filename = frappe.form_dict.filename
        except:
            raise frappe.ValidationError

        customer = frappe.db.sql("""
                    select
                        cust.name
                    from
                        `tabUser` user
                        left join `tabCustomer` cust on cust.email_id = user.name
                    where
                        user.name = '{0}'
                """.format(user), as_dict=True)

        customer = customer[0].name if customer else ""

        dev_doc = frappe.new_doc("Offline Payment")
        dev_doc.fee_request = fee_request
        dev_doc.customer = customer
        dev_doc.insert(ignore_permissions=True)

        # Upload File
        from frappe.utils.file_manager import save_file
        f = save_file(
            fname=uploaded_filename, content=uploaded_content, dt=dev_doc.doctype, dn=dev_doc.name, is_private=1)
        dev_doc.payment_ack_image = f.file_url
        dev_doc.submit()

        # Update fee request with paydoc is still to be done
        frappe.db.set_value(
            "Fee Request", upi_pay_doc.fee_request, "offline_payment", upi_pay_doc.name)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(e)
    return "Success"


@ frappe.whitelist()
def check_request_status():
    user = check_permissions()
    fee_request = frappe.form_dict.get('fee_request')
    status = frappe.db.get_value("Fee Request", fee_request, "status")
    return status.upper() if status else "FAILED"


@ frappe.whitelist()
def check_collection_request_status():
    user = check_permissions()
    fee_request = frappe.form_dict.get('fee_request')
    payments = frappe.get_all("UPI Payment", filters={
                              "fee_request": fee_request, "collection_request_status": "SUCCESS"}, order_by="creation desc")
    if payments:
        upi_rec = frappe.get_doc("UPI Payment", payments[0].name)
        from customer_portal_cv.customer_portal_capitalvia.upi_payment import UPIPayment
        payobj = UPIPayment()
        payobj.check_transaction_status(upi_rec)
        return "Done"
    else:
        return "No Payments Found"


@frappe.whitelist()
def mark_executed():
    user = check_permissions()
    signal_log = frappe.form_dict.get('signal_log')
    if not signal_log:
        frappe.throw("Signal Log in required")

    frappe.db.set_value("Signal Logs", signal_log, "executed", 1)
    frappe.db.commit()
    return "SUCCESS"