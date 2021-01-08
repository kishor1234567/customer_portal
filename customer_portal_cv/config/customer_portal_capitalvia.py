from __future__ import unicode_literals
from frappe import _


def get_data():

    return [
        {
            "label": _("Document"),
            "icon": "octicon octicon-briefcase",
            "items": [
                {
                    "type": "doctype",
                    "name": "UPI Payment",
                    "label": _("UPI Payment"),
                },
                {
                    "type": "doctype",
                    "name": "Offline Payment",
                    "label": _("Offline Payment"),
                },
                {
                    "type": "doctype",
                    "name": "Customer Portal Devices",
                    "label": _("Customer Portal Devices"),
                },
                {
                    "type": "doctype",
                    "name": "HDFC UPI Settings",
                    "label": _("HDFC UPI Settings"),
                },
                {
                    "type": "doctype",
                    "name": "Digio Sign Document",
                    "label": _("Digio Sign Document"),
                },
            ]
        }
    ]
