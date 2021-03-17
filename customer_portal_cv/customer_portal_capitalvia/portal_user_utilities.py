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
import base64
import pyotp
from frappe import msgprint, _
from frappe.utils import cstr, nowdate, get_first_day, get_last_day, formatdate, getdate, flt, get_files_path
from frappe.twofactor import (should_run_2fa, authenticate_for_2factor, get_cached_user_pass, send_token_via_sms,
                              two_factor_is_enabled_for_, confirm_otp_token, get_otpsecret_for_, get_verification_obj)
from frappe.utils.password import update_password as _update_password
from frappe.utils.password import set_encrypted_password, delete_login_failed_cache, passlibctx, decrypt
from frappe.core.doctype.sms_settings.sms_settings import send_sms


@frappe.whitelist(allow_guest=True)
def initiate_pwd_reset():
    email = frappe.form_dict.get('email')
    if email and frappe.db.exists('User', email):
        authenticate_for_2factor(email)
        phone = get_phone_no(email)
        if phone:
            tmp_id = frappe.local.response['tmp_id']
            otp_secret = frappe.cache().get(tmp_id + '_otp_secret')
            token = frappe.cache().get(tmp_id + '_token')
            # Surprisingly following 2FA method is not working
            # status = send_token_via_sms(otp_secret, token=token, phone_no=phone)
            from frappe.core.doctype.sms_settings.sms_settings import send_sms
            hotp = pyotp.HOTP(otp_secret)
            msg = 'Your verification code is {}'.format(hotp.at(int(token)))
            send_sms([cstr(phone)], msg)
        frappe.db.commit()
    else:
        raise frappe.PermissionError("User does not exist")


def get_phone_no(user):
    user_info = frappe.db.sql("""
        select
            lead.primary_mobile
        from
            `tabUser` user
            left join `tabLead` lead on lead.email_id = user.name
        where
            user.name = '{0}'
    """.format(user), as_dict=True)
    return user_info[0].primary_mobile if user_info else None


@frappe.whitelist(allow_guest=True)
def confirm_device_otp_token():
    email = frappe.form_dict.get('email')
    tmp_id = frappe.form_dict.get('tmp_id')
    otp = frappe.form_dict.get('otp')

    if email and not frappe.db.exists('User', email):
        raise frappe.PermissionError("User does not exist")

    if not otp:
        raise frappe.PermissionError("OTP not found")

    if not tmp_id:
        raise frappe.PermissionError("ID not found")

    hotp_token = frappe.cache().get(tmp_id + '_token')
    otp_secret = frappe.cache().get(tmp_id + '_otp_secret')

    if not otp_secret:
        raise frappe.PermissionError("Login expired")

    hotp = pyotp.HOTP(otp_secret)
    if hotp_token:
        if hotp.verify(otp, int(hotp_token)):
            frappe.cache().delete(tmp_id + '_token')
            key = _generate_key(email)
            return key
        else:
            raise frappe.PermissionError("OTP does not match")

    totp = pyotp.TOTP(otp_secret)
    if totp.verify(otp):
        key = _generate_key(email)
        return key
    else:
        raise frappe.PermissionError("OTP does not match")


def _generate_key(user):
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
    return key


def _get_user_for_update_password(key, old_password):
    # verify old password
    if key:
        user = frappe.db.get_value("User", {"reset_password_key": key})
        if not user:
            return {
                'message': _("The Link specified has either been used before or Invalid")
            }

    elif old_password:
        # verify old password
        frappe.local.login_manager.check_password(
            frappe.session.user, old_password)
        user = frappe.session.user

    else:
        return

    return {
        'user': user
    }


@frappe.whitelist(allow_guest=True)
def reset_password():
    pwd = frappe.form_dict.get('pwd')
    apwd = frappe.form_dict.get('apwd')
    key = frappe.form_dict.get('key')

    if pwd and key and pwd == apwd:
        res = _get_user_for_update_password(key, None)
        if res.get('message'):
            frappe.local.response.http_status_code = 410
            return res['message']
        else:
            user = res['user']

        _update_password(user, pwd, logout_all_sessions=1)
        return "SUCCESS"
    else:
        raise frappe.ValidationError(
            "Passwords does not match or key is missing")


@frappe.whitelist()
def reset_pin():
    pwd, apwd = None, None
    if frappe.session.user != "Guest":
        pwd = frappe.form_dict.get('pwd')
        apwd = frappe.form_dict.get('apwd')

    if pwd and apwd:
        set_encrypted_password("User", frappe.session.user,
                               pwd, fieldname="pin")
        frappe.db.commit()
        return "SUCCESS"
    else:
        raise frappe.ValidationError(
            "Passwords does not match or key is missing")


@frappe.whitelist(allow_guest=True)
def check_pin(user, pin):
    doctype = 'User'
    fieldname = 'pin'
    '''Checks if user and password are correct, else raises frappe.AuthenticationError'''

    auth = frappe.db.sql("""select `name`, `password` from `__Auth`
    where `doctype`=%(doctype)s and `name`=%(name)s and `fieldname`=%(fieldname)s and `encrypted`=1""",
                         {'doctype': doctype, 'name': user, 'fieldname': fieldname}, as_dict=True)

    # if not auth or not passlibctx.verify(pin, auth[0].password):
    if not auth or not pin == decrypt(auth[0].password):
        raise frappe.AuthenticationError(_('Incorrect User or Password'))

    # lettercase agnostic
    user = auth[0].name
    delete_login_failed_cache(user)

    frappe.local.login_manager.login_as(user)
