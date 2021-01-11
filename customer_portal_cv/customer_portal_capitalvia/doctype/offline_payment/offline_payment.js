// Copyright (c) 2020, CapitalVia and contributors
// For license information, please see license.txt

frappe.ui.form.on('Offline Payment', {
	refresh: function(frm) {
		if(frm.doc.payment_ack_image) {
			$(frm.fields_dict['ack_preview'].wrapper).html("<a href='"+frm.doc.payment_ack_image+"' target='_blank'><img src='"+frm.doc.payment_ack_image+"'></img></a>");
		} else {
			$(frm.fields_dict['ack_preview'].wrapper).html("");
		}
	}
});
