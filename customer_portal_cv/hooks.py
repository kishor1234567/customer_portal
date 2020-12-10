# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "customer_portal_cv"
app_title = "Customer Portal CapitalVia"
app_publisher = "CapitalVia"
app_description = "CapitalVia Customer Portal"
app_icon = "octicon octicon-file-directory"
app_color = "green"
app_email = "nick9822@gmail.com"
app_license = "Proprietary"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/customer_portal_cv/css/customer_portal_cv.css"
# app_include_js = "/assets/customer_portal_cv/js/customer_portal_cv.js"

# include js, css files in header of web template
# web_include_css = "/assets/customer_portal_cv/css/customer_portal_cv.css"
# web_include_js = "/assets/customer_portal_cv/js/customer_portal_cv.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "customer_portal_cv.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "customer_portal_cv.install.before_install"
# after_install = "customer_portal_cv.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "customer_portal_cv.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Customer": {
        "after_insert": "customer_portal_cv.customer_portal_capitalvia.cp_facilitator.create_customer",
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"customer_portal_cv.tasks.all"
# 	],
# 	"daily": [
# 		"customer_portal_cv.tasks.daily"
# 	],
# 	"hourly": [
# 		"customer_portal_cv.tasks.hourly"
# 	],
# 	"weekly": [
# 		"customer_portal_cv.tasks.weekly"
# 	]
# 	"monthly": [
# 		"customer_portal_cv.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "customer_portal_cv.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "customer_portal_cv.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "customer_portal_cv.task.get_dashboard_data"
# }
