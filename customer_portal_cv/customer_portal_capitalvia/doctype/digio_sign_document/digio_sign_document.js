// Copyright (c) 2021, CapitalVia and contributors
// For license information, please see license.txt

frappe.ui.form.on('Digio Sign Document', {
	refresh: function(frm) {

	},
	submit_for_signature: function(frm) {
		let filenameparts = frm.doc.file_to_sign.split("/");
		if (!frm.doc.file_to_sign.includes("pdf")) {
			frappe.throw("Only PDF documents are allowed to be signed");
		}

		if(frm.doc.customer_name && frm.doc.email) {
			toDataUrl(window.location.origin+frm.doc.file_to_sign, function(datab64) {
				frappe.dom.freeze();
				fetch('https://cors-anywhere.herokuapp.com/https://api.digio.in/v2/client/document/uploadpdf', {
						method: 'post',
						headers: {
							'authorization': 'Basic '+btoa('AIT1MY4Y4F58GQY5TO3OQSSAPIHKXLSO:Q5T4LBMAXP3SFCQVC54SCGGQJFBF3WW1'),
							'content-type': 'application/json'
						},
						body: JSON.stringify({
							"signers": [{
								"identifier": frm.doc.email,
								"name": frm.doc.customer_name,
								"reason": frm.doc.reason
							}],
							"expire_in_days": 1,
							"file_name": filenameparts[filenameparts.length - 1],
							"file_data": datab64.split(",")[1],
							"notify_signers": true,
							"send_sign_link": true
						})
					}).then(function(response) {
						return response.json();
					}).then(function(data) {
						frappe.dom.unfreeze();
						if(data && 'id' in data) {
							cur_frm.set_value("digio_id", data.id);
							cur_frm.set_value("submitted_for_signature", 1);
							cur_frm.save();
						} else {
							frappe.throw("Something went wrong!")
						}
					});
			});
		} else {
			frappe.throw("Customer Name and Email is mandatory");
		}
	},
	download_signed_file: function(frm) {
		let filenameparts = frm.doc.file_to_sign.split("/");
		frappe.dom.freeze();
		fetch('https://cors-anywhere.herokuapp.com/https://api.digio.in/v2/client/document/'+frm.doc.digio_id, {
					method: 'get',
					headers: {
						'authorization': 'Basic '+btoa('AIT1MY4Y4F58GQY5TO3OQSSAPIHKXLSO:Q5T4LBMAXP3SFCQVC54SCGGQJFBF3WW1'),
						'content-type': 'application/json'
					}
				}).then(function(response) {
					return response.json();
				}).then(function(data) {
					if(data.agreement_status == "completed") {
						fetch('https://cors-anywhere.herokuapp.com/https://api.digio.in/v2/client/document/download?document_id='+frm.doc.digio_id, {
							method: 'get',
							headers: {
								'authorization': 'Basic '+btoa('AIT1MY4Y4F58GQY5TO3OQSSAPIHKXLSO:Q5T4LBMAXP3SFCQVC54SCGGQJFBF3WW1'),
								'content-type': 'application/json'
							},
						}).then(function(response) {
							return response.blob();
						}).then(function(blob) {
							frappe.dom.unfreeze();
							var url = window.URL.createObjectURL(blob)
							var a = document.createElement('a')
							a.href = url
							a.target = "_blank"
							a.download = filenameparts[filenameparts.length - 1]
							a.click()
							a.remove()
							setTimeout(() => window.URL.revokeObjectURL(url), 100)
						});
					} else {
						frappe.dom.unfreeze();
						frappe.msgprint("Looks like the document is not signed yet.")
					}
				});
	}
});

function toDataUrl(url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.onload = function() {
        var reader = new FileReader();
        reader.onload = function() {
            callback(reader.result);
        }
        reader.readAsDataURL(xhr.response);
    };
    xhr.open('GET', url);
    xhr.responseType = 'blob';
    xhr.send();
}