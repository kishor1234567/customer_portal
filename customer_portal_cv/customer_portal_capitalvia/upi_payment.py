# -*- coding: utf-8 -*-
# Copyright (c) 2020, GoElite and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import os
import re
import redis
import ast
import json
import time
from frappe import msgprint, _
from frappe.utils import nowdate, get_first_day, get_last_day, formatdate, getdate, flt, get_files_path
from frappe.core.doctype.communication.email import make
from frappe.utils.pdf import get_pdf
from PyPDF2 import PdfFileWriter

import requests
import binascii
from Crypto import Random
from Crypto.Cipher import AES
import base64
from binhex import binhex, hexbin
import string
import random
from frappe.utils.password import get_decrypted_password

if frappe.db.get_value("HDFC UPI Settings", "HDFC UPI Settings", "test_mode") == "1":
    CHECK_VPA_URL = "https://upitest.hdfcbank.com/upi/checkMeVirtualAddress"
    COLLECT_TRAN_URL = "https://upitest.hdfcbank.com/upi/meTransCollectSvc"
    CHECK_COLLECT_REQ = "https://upitest.hdfcbank.com/upi/transactionStatusQuery"
else:
    CHECK_VPA_URL = "https://upi.hdfcbank.com/upi/checkMeVirtualAddress"
    COLLECT_TRAN_URL = "https://upi.hdfcbank.com/upi/meTransCollectSvc"
    CHECK_COLLECT_REQ = "https://upi.hdfcbank.com/upi/transactionStatusQuery"


class UPIPayment():
    def __init__(self):
        if frappe.db.get_value("HDFC UPI Settings", "HDFC UPI Settings", "test_mode") == "1":
            self.mcc = "6012"
            self.merchant_id = "HDFC000005853569"
            self.merchant_key = "d87822929aa83119f76cf6b762b87b0e"
            self.vpa = "capitalvia@hdfcbank"
        else:
            settings = frappe.get_doc(
                "HDFC UPI Settings", "HDFC UPI Settings")
            if settings.mcc and settings.merchant_id:
                self.mcc = settings.mcc
                self.merchant_id = settings.merchant_id
                self.merchant_key = get_decrypted_password(
                    "HDFC UPI Settings", "HDFC UPI Settings", "merchant_key")
                self.vpa = "capitalviaia@hdfcbank"
            else:
                frappe.throw("Connection details are missing")

    def initiate_payment(self, vpa_address, amount, upi_link, fee_request, fcm_token):
        self.vpa_address = vpa_address
        self.amount = amount
        self.fee_request = fee_request
        self.fcm_token = fcm_token
        if upi_link:
            return self.generate_link()
        else:
            self.check_vpa()
            return self.collect_transaction_request()

    def check_vpa(self):
        """
            PGMerchantId|Merchant Ref No|VPA|Status|1|2|3|4|5|6|7|8|NA|NA = 14 Nos
        """
        self.transaction_no = frappe.generate_hash("UPI Payment", 10)
        req = "{}|{}|{}|T|||||||||NA|NA".format(
            self.merchant_id, self.transaction_no, self.vpa_address)
        frappe.log_error(req)
        payload = {'requestMsg': _encrypt(
            req, self.merchant_key), 'pgMerchantId': self.merchant_id}

        headers = {
            'content-type': "application/json",
        }

        r = requests.request(
            "POST", CHECK_VPA_URL, data=json.dumps(payload), headers=headers)
        frappe.log_error(_decrypt(r.content, self.merchant_key))
        return _decrypt(r.content, self.merchant_key)

    def collect_transaction_request(self):
        """
            PGMerchantId|OrderNo|PayerVA|Amount|Remarks|expValue|MCC Code|1|2|3|4|5|6|7|8|NA|NA = 17 Nos.
            Request is valid till 5 minutes
        """
        remark = "Payment of {} from {}".format(
            self.amount, frappe.session.user)
        req = "{}|{}|{}|{}|{}|{}||||||||||NA|NA".format(
            self.merchant_id, self.transaction_no, self.vpa_address, self.amount, "CapitalVia Payment", 5)
        frappe.log_error(req)
        payload = {'requestMsg': _encrypt(
            req, self.merchant_key), 'pgMerchantId': self.merchant_id}

        headers = {
            'content-type': "application/json",
        }

        r = requests.request(
            "POST", COLLECT_TRAN_URL, data=json.dumps(payload), headers=headers)
        frappe.log_error(r.content)
        frappe.log_error(_decrypt(r.content, self.merchant_key))
        self.request_started = int(time.time())
        upi_ref_id, status, tran_status, field_6 = self.decode_pipes(
            "COLLECTION", _decrypt(r.content, self.merchant_key))

        fee_request_amount = frappe.db.get_value(
            "Fee Request", self.fee_request, "amount")
        if status == "SUCCESS":
            paydoc = frappe.new_doc("UPI Payment")
            paydoc.transaction_number = self.transaction_no
            paydoc.vpa_address = self.vpa_address
            paydoc.amount = fee_request_amount
            paydoc.remark = remark
            paydoc.upi_transaction_reference_id = upi_ref_id
            paydoc.collection_request_status = status
            paydoc.transaction_status = tran_status
            paydoc.fee_request = self.fee_request
            paydoc.fcm_token = self.fcm_token if self.fcm_token else ""
            paydoc.insert()
            paydoc.submit()
            frappe.db.commit()
            return self.transaction_no, "SUCCESS"
        else:
            return self.transaction_no, "FAILED"

    def validate_payment(self, data):
        """
            2711101|8495c0dbe5|111.00|2020:09:01 11:34:00|FAILED|Transaction fail|XB|NA|cup@hdfcbank|024511439257|
            NA|null|null|null|null|null|NA!NA!NA!NA|COLLECT!https://upitest.hdfcbank.com!NA!HDF9E5916829C0749A399F6343B21DA62D9!NA!|capitalvia@hdfcbank!NA!NA|NA|NA'
        """
        payload = _decrypt(data, self.merchant_key)
        upi_ref_id, upi_erp_id, amount, status, payer_vpa_address = self.decode_pipes(
            "CALLBACK", payload)

        new_status = status
        upi_doc = frappe.get_doc("UPI Payment", upi_erp_id)
        fee_request_amount = frappe.db.get_value(
            "Fee Request", upi_doc.fee_request, "amount")

        if flt(amount) < flt(fee_request_amount) and flt(amount) > 0 and status == "SUCCESS":
            new_status = "PARTIALLY PAID"
        elif flt(amount) > flt(fee_request_amount) and flt(amount) > 0 and status == "SUCCESS":
            new_status = "OVERPAID"
        elif flt(amount) == flt(fee_request_amount) and status == "SUCCESS":
            new_status = status

        upi_doc.callback_payload = payload
        upi_doc.transaction_status = new_status

        if not upi_doc.upi_transaction_reference_id:
            upi_doc.upi_transaction_reference_id = upi_ref_id

        if not upi_doc.vpa_address:
            upi_doc.vpa_address = payer_vpa_address

        upi_doc.save()
        frappe.db.commit()
        return upi_erp_id, new_status

    def decode_pipes(self, req_type, data):
        if req_type == "COLLECTION":
            data_list = data.split("|")
            return data_list[1], data_list[3], data_list[4], data_list[12]
        elif req_type == "CALLBACK":
            data_list = data.split("|")
            return data_list[0], data_list[1], data_list[2], data_list[4], data_list[8]
        elif req_type == "COLLECTION_POLLING":
            data_list = data.split("|")
            return data_list[0], data_list[1], data_list[2], data_list[4]

    def generate_link(self):
        """
            upi://pay?pa=test@hdfcbank&pn=Test.&mc=6012&tr=B5D73D0D9E414F1&tn=Transaction&am=100&cu=INR
        """
        remark = "Payment of {} from {}".format(
            self.amount, frappe.session.user)
        self.transaction_no = frappe.generate_hash("UPI Payment", 10)
        payment_string = "upi://pay?pa={}&pn={}&mcc={}&tr={}&tn={}&am={}&cu=INR".format(
            self.vpa, "CapitalVia", self.mcc, self.transaction_no, "CapitalVia%20Payment", self.amount)

        fee_request_amount = frappe.db.get_value(
            "Fee Request", self.fee_request, "amount")
        paydoc = frappe.new_doc("UPI Payment")
        paydoc.transaction_number = self.transaction_no
        paydoc.vpa_address = ""
        paydoc.amount = fee_request_amount
        paydoc.remark = remark
        paydoc.upi_transaction_reference_id = ""
        paydoc.collection_request_status = "QR OR DEEP LINKING INITIATED"
        paydoc.transaction_status = ""
        paydoc.fee_request = self.fee_request if self.fee_request else ""
        paydoc.fcm_token = self.fcm_token if self.fcm_token else ""
        paydoc.insert()
        paydoc.submit()
        frappe.db.commit()

        return payment_string, "UPI_LINK_SUCCESS"

    def check_transaction_status(self, upi_rec):
        """
            PGMerchantId|OrderNo|UPITxn ID |1|2|3|4|5|6|7|8|NA|NA=14Nos
            UPI000000000086|20160728111155|65437829217889||||||||||NA|NA
        """
        req = "{}|{}|{}||||||||||NA|NA".format(
            self.merchant_id, upi_rec.name, upi_rec.upi_transaction_reference_id)
        frappe.log_error(req)
        payload = {'requestMsg': _encrypt(
            req, self.merchant_key), 'pgMerchantId': self.merchant_id}

        headers = {
            'content-type': "application/json",
        }

        r = requests.request(
            "POST", CHECK_COLLECT_REQ, data=json.dumps(payload), headers=headers)
        res = _decrypt(r.content, self.merchant_key)
        frappe.log_error(res)
        upi_ref_id, order_no, amount, tran_status = self.decode_pipes(
            "COLLECTION_POLLING", res)
        if tran_status == "SUCCESS" and order_no == upi_rec.name and flt(amount) == flt(upi_rec.amount):
            upi_rec.transaction_status = tran_status
            frappe.publish_realtime(
                "payment_status", {"upi_erp_id": upi_rec.name, "result": "SUCCESS"})
            frappe.publish_realtime(event="new_notifications", message={
                                    "type": "default", "message": "Your last payment was successful. Thank you for your payment."}, user=upi_rec.owner)
            if upi_rec.fee_request:
                # Update fee request with paydoc is still to be done
                frappe.db.set_value(
                    "Fee Request", upi_rec.fee_request, "upi_payment", upi_rec.name)
                frappe.db.set_value(
                    "Fee Request", upi_rec.fee_request, "status", "Success")
                frappe.db.commit()

                if upi_rec.fcm_token:
                    from customer_portal_cv.customer_portal_capitalvia.fcm_utils import FcmUtils
                    fcmObj = FcmUtils()
                    fcmObj.send_single_notification(
                        message={
                            "title": "Payment Successful",
                            "body": "Your last payment of Rs. {} was successful. Thank you for your payment.".format(upi_rec.amount)
                        },
                        data={
                            "route": "payment",
                            "payment_state": "SUCCESS"
                        },
                        token=upi_rec.fcm_token
                    )
        elif tran_status != "PENDING":
            upi_rec.transaction_status = "FAILED"
            frappe.publish_realtime(
                "payment_status", {"upi_erp_id": upi_rec.name, "result": "TRY AGAIN"})
            frappe.publish_realtime(event="new_notifications", message={
                                    "type": "default", "message": "Your last payment was unsuccessful. Please try again."}, user=upi_rec.owner)

            if upi_rec.fcm_token:
                from customer_portal_cv.customer_portal_capitalvia.fcm_utils import FcmUtils
                fcmObj = FcmUtils()
                fcmObj.send_single_notification(
                    message={
                        "title": "Payment Unsuccessful",
                        "body": "Your last payment was unsuccessful. Please try again."
                    },
                    data={
                        "route": "payment",
                        "payment_state": "FAILED"
                    },
                    token=upi_rec.fcm_token
                )

        upi_rec.callback_payload = res
        upi_rec.save()
        frappe.db.commit()


def _encrypt(data, passphrase):
    try:
        key = binascii.unhexlify(passphrase)
        def pad(s): return s+chr(16-len(s) % 16)*(16-len(s) % 16)
        iv = Random.get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_ECB)
        encrypted_64 = base64.b16encode(
            cipher.encrypt(pad(data))).decode('ascii')
        clean = encrypted_64
    except Exception as e:
        print("Cannot encrypt datas...")
        print(e)
    return str(clean)


def _decrypt(data, passphrase):
    try:
        def unpad(s): return s[:-s[-1]]
        key = binascii.unhexlify(passphrase)
        encrypted_data = base64.b16decode(data)
        cipher = AES.new(key, AES.MODE_ECB)
        decrypted = cipher.decrypt(encrypted_data)
        clean = unpad(decrypted).decode('ascii').rstrip()
    except Exception as e:
        print("Cannot decrypt datas...")
        print(e)
    return clean


def generateRandom(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def callback_payment(response, merchant_id):
    payobj = UPIPayment()
    if payobj.merchant_id == merchant_id:
        return payobj.validate_payment(response)
