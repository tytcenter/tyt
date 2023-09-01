/** @odoo-module */
import { _t } from 'web.core';
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { CharField } from "@web/views/fields/char/char_field";
import rpc from 'web.rpc';

export class attachXmlsWizard extends CharField {
     _onDragEnter(ev) {
         ev.stopPropagation();
         ev.preventDefault();
    }
    _onDragOver(ev) {
         ev.stopPropagation();
         ev.preventDefault();
         $(ev.currentTarget).removeClass('dnd_out').addClass('dnd_inside');
    }
    _onDrop(ev) {
        ev.preventDefault();
        this.handleFileUpload(ev.dataTransfer.files);
    }

     _onClickWrapper(ev) {
         $(document.getElementsByClassName('files')).val("");
         $(document.getElementsByClassName('files')).click();
    }

    _uploadFile(ev){
          if (ev.currentTarget.files.length > 0) {
               this.handleFileUpload(ev.currentTarget.files);
           }
    }
    _onButtonSave(e){
        e.preventDefault();
                $('.alert-warning.dnd-alert').remove();
                if (Object.keys(this.files).length <= 0) {
                    this.notification.add(this.env._t("There is no files selected"), {type: "danger",});
                }
                //@HP: this.getParent().state.context.active_ids --> no longer find parent class in 16.
                else if (Object.keys(this.files).length > 1 && this.env.model.root.context.active_ids) {
                    this.notification.add(this.env._t("There is no files selected"), {type: "danger",});
                }
                else {
                    $('#dragandrophandler').hide();
                    $('#dndfooter').find("#save").attr('disabled', true);
                    $('#filescontent').find(".xml_cont").removeClass('xml_cont_hover');
                    this.readFiles(this.files);
                }
    }

    _onButtonClose(e){
          e.preventDefault();
          this.props.record.model.root.model.actionService.doAction({'type': 'ir.actions.act_window_close'});
    }
    async _onButtonShow(e){
          e.preventDefault();
           if (this.attachment_ids.length > 0) {
            var domain = [['id', 'in', this.attachment_ids]];
                    this.action.doAction({
                        name: _t('XML Attchments'),
                        view_type: 'list',
                        view_mode: 'list,form',
                        res_model: 'ir.attachment',
                        type: 'ir.actions.act_window',
                        views: [[false, 'list'], [false, 'form']],
                        target: 'current',
                        domain: domain,
                    });
                }
    }
    setup() {
            super.setup();
            this.files = {};
            this.uploading_files = false;
            this.attachment_ids = [];
            this.notification = useService("notification");
            this.action = useService("action");
            var handler = $(document.getElementById("dragandrophandler"));
            // events drag and drop inside the page
            $(document).on('dragenter', function(e) {
                e.stopPropagation();
                e.preventDefault();
                handler.removeClass('dnd_inside dnd_normal').addClass('dnd_out');
            });
            $(document).on('dragover', function(e) {
                // allows to execute the drop event
                e.stopPropagation();
                e.preventDefault();
            });
            $(document).on('drop', function(e) {
                e.stopPropagation();
                e.preventDefault();
                handler.removeClass('dnd_out dnd_inside').addClass('dnd_normal');
            });
            $(document).on('dragleave', function(e) {
                e.stopPropagation();
                e.preventDefault();
                if (!e.originalEvent.clientX && !e.originalEvent.clientY) {
                    handler.removeClass('dnd_out dnd_inside').addClass('dnd_normal');
                }
            });
        }
        remove_all_xml(e){
            var alertnode = e.currentTarget.parentElement.parentElement;
            var filekey_current = alertnode.attributes.tag.value;
            var self = this;
            var remove_current_file = false;
            var files = this.files;
            var wrong_files = Object.values(this.files).filter(function(file) {
                return file.iscorrect === false;
            });
            var readfiles = {};

            $.each(wrong_files, function(key, file) {
                if (!file.iscorrect) {
                    var fr = new FileReader();
                    fr.onload = function() {
                        if (!file.iscorrect) {
                            readfiles[file.name] = fr.result;
                        }
                        if (Object.keys(wrong_files).length === Object.keys(readfiles).length) {
                            // self.sendFileToServer(readfiles);
                            rpc.query({
                                model: 'multi.file.attach.xmls.wizard',
                                method: 'remove_wrong_file',
                                args: [readfiles],
                                context: self.env.model.root.context,
                            }).then(function(results) {
                                // var type = e.currentTarget.attributes.tag.value;
                                var alertnode = e.currentTarget.parentElement.parentElement;
                                var filekey = results;
                                filekey.forEach(element => {
                                    self.removeWrongAlerts($(alertnode), element, true);
                                });
                            });
                        }
                    };
                    fr.readAsDataURL(file);
                }
            });
            $.each(self.alerts_in_queue.alertHTML, function(filekey, file) {
                if (file.alert[0].innerText.includes('The XML UUID</span> belong to other move')) {
                    if (filekey_current == filekey) {
                        remove_current_file = true;
                    }
                    else {
                        delete self.alerts_in_queue.alertHTML[filekey];
                        delete self.files[filekey];
                    }
                }
                else if (file.alert[0].innerText.includes('The move reference</span> belong to other')) {
                    if (filekey_current == filekey) {
                        remove_current_file = true;
                    }
                    else {
                        delete self.alerts_in_queue.alertHTML[filekey];
                        delete self.files[filekey];
                    }
                }
            });
            if (remove_current_file) {
                this.removeWrongAlerts($(alertnode), filekey_current, true);
            }
        }
        remove_single_xml(e){
         delete this.files[e.currentTarget.attributes.title.value];
                $(e.currentTarget).animate({'opacity': '0'}, 500, function() {
                    $(this).remove();
                });
        }

       remove_xml(e){
                var type = e.currentTarget.attributes.tag.value;
                var alertnode = e.currentTarget.parentElement.parentElement;
                var filekey = alertnode.attributes.tag.value;
                var self = this;
                if (type === 'remove') {
                    this.removeWrongAlerts($(alertnode), filekey, true);
                }
                else if (type === 'partner') {
                    rpc.query({
                        model: 'multi.file.attach.xmls.wizard',
                        method: 'create_partner',
                        args: [this.alerts_in_queue.alertHTML[filekey].xml64, filekey],
                        context: self.env.model.root.context,
                    }).then(function() {
                        self.sendErrorToServer(self.alerts_in_queue.alertHTML[filekey].xml64, filekey, 'check_xml');
                    });
                }
                else if (type === 'tryagain') {
                    this.sendErrorToServer(this.alerts_in_queue.alertHTML[filekey].xml64, filekey, 'check_xml');
                }
                else if (type === 'forcesave') {
                    self.env.model.root.context = _.extend(self.env.model.root.context, {'force_save': true});
                    self.sendErrorToServer(self.alerts_in_queue.alertHTML[filekey].xml64, filekey, 'check_xml');
                }
            }
       handleFileUpload(files) {
        /* Creates the file element in the DOM and shows alerts wheter the extension
            file is not the correct one or the file is already uploaded */
            var self = this;
            if (self.uploading_files) {
                self.notification.add(this.env._t("There are files uploading"), {title: this.env._t('Error'),type: "danger",});
            }
            else {
                self.uploading_files = true;
                var files_used = [];
                var wrong_files = [];
                $.each(files, function(i, file) {
                    if (file.type !== 'text/xml') {
                        wrong_files.push(file.name);
                    }
                    else if (Object.prototype.hasOwnProperty.call(self.files, file.name)) {
                        files_used.push(file.name);
                    }
                    else {
                        self.files[file.name] = file;
                        var newelement = $('<div class="xml_cont xml_cont_hover" id="xml_cont_hover" title="' + file.name + '">' +
                            '<img class="xml_img" height="100%" align="left" hspace="5"/>' +
                            '<p>' + file.name + '</p><div class="remove_xml" >&times;</div>' +
                            '</div>').css('opacity', '0');
                        $(document.getElementById('filescontent')).append(newelement);
                        newelement.animate({'opacity': '1'}, 500);
                    }
                });
                var alert_message = '';
                if (wrong_files.length > 0) {
                    alert_message += _t('<strong>Info!</strong> You only can upload XML files.<br>') +
                        wrong_files.join(" <b style='font-size:15px;font-wight:900;'>&#8226;</b> ");
                }
                if (files_used.length > 0) {
                    if (alert_message !== '') {
                        alert_message += '<br>';
                    }
                    alert_message += _t('<strong>Info!</strong> Some files are already loaded.<br>') +
                        files_used.join(" <b style='font-size:15px;font-wight:900;'>&#8226;</b> ");
                }
                if (alert_message !== '') {
                    $(document.getElementById('alertscontent')).html('<div class="alert alert-warning dnd-alert">' +
                        '<a href="#" class="close" data-dismiss="alert" aria-label="close">&times;</a>' + alert_message +
                        '</div>');
                }
                self.uploading_files = false;
            }
              $(("#xml_cont_hover")).on('click', self.remove_single_xml.bind(self));
        }
       readFiles(files) {
            /* Convert the file object uploaded to a base64 string */
            var self = this;
            var readfiles = {};
            $.each(files, function(key, file) {
                var fr = new FileReader();
                fr.onload = function() {
                    readfiles[key] = fr.result;
                    if (Object.keys(files).length === Object.keys(readfiles).length) {
                        self.sendFileToServer(readfiles);
                    }
                };
                fr.readAsDataURL(file);
            });
        }
       getFields(){
            var self = this;
            var fields = {};
            $.each(this.props.record.data, function(field, value) {
                if (!value || field === 'omit_cfdi_related' || field === 'product_create') {
                    fields[field] = value;
                }
                else if (value.constructor === Array) {
                    var valueList = [];
                    $.each(value.data, function(index, val) {
                        valueList.push(val.data.id);
                    });
                    fields[field] = valueList;
                }
                else {
                    fields[field] = value.data.id;
                }
            });
            return fields;
        }
       sendFileToServer(files) {
            /* Sends each base64 file string to the back-end server to create the moves */
            var self = this;
            var options = self.getFields();
            var ctx = this.props.record.context
            ctx.account_id = options.account_id;
            ctx.journal_id = options.journal_id;
            ctx.omit_cfdi_related = options.omit_cfdi_related;
            ctx.product_create = options.product_create;
            rpc.query({
                model: 'multi.file.attach.xmls.wizard',
                method: 'check_xml',
                args: [files],
                context: ctx,
            }).then(function(result) {
                var wrongfiles = result.wrongfiles;
                var attachments = result.attachments;
                $.each(attachments, function(key, data) {
                    self.attachment_ids.push(data.attachment_id);
                    self.files[key].iscorrect = true;
                    self.createdCorrectly(key);
                });
                $.each(wrongfiles, function(key, data) {
                    self.files[key].iscorrect = false;
                });
                if (Object.keys(wrongfiles).length > 0) {
                    self.handleFileWrong(wrongfiles);
                }
                if (Object.keys(wrongfiles).length === 0 || self.alerts_in_queue.total === 0) {
                    self.correctFinalRegistry();
                }
            });
        }
       createdCorrectly(key) {
            /* Colors the files content in the DOM when the move is created with that XML */
            var self = this;
            var alert = $('#filescontent div[title="' + key + '"]');
            alert.addClass('xml_correct');
            alert.find('div.remove_xml').html('&#10004;');
        }
       handleFileWrong(wrongfiles) {

            /* Saves the exceptions occurred at the moves creation */
            this.alerts_in_queue = {'alertHTML': {}, total: Object.keys(wrongfiles).length};
            var self = this;
            $.each(wrongfiles, function(key, file) {
                if ('cfdi_type' in file) {
                    if (Object.keys(self.files).length === 0) {
                        self.restart();
                    }
                    self.alerts_in_queue.total -= 1;
                    $('#filescontent div[title="' + key + '"]').remove();

                    self.notification.add(this.env._t("XML removed, the TipoDeComprobante is not I nor E."), {title: this.env._t('Error'),type: "danger",});
                }
                else {

                    var alert_parts = self.prepareWrongAlert(key, file);
                    var alertelement = $('<div tag="' + key + '" class="alert alert-' + alert_parts.alerttype + ' dnd-alert">' +
                        alert_parts.errors + '<div>' + alert_parts.buttons + _t('<span>Wrong File: <span class="index-alert"></span>') + '/' + self.alerts_in_queue.total +
                        '<b style="font-size:15px;font-wight:900;">&#8226;</b> ' + key + '</span></div></div>');
                    alertelement.find("#remove_xml").on('click', self.remove_xml.bind(self));
                    alertelement.find("#tryagain").on('click', self.remove_xml.bind(self));
                    alertelement.find("#remove_all_xml").on('click', self.remove_all_xml.bind(self));
                    self.alerts_in_queue.alertHTML[key] = {'alert': alertelement, 'xml64': file.xml64};
                }
                if (self.alerts_in_queue.total > 0 && self.alerts_in_queue.total === Object.keys(self.alerts_in_queue.alertHTML).length) {
                    self.nextWrongAlert();
                }
            });
        }
       prepareWrongAlert(key, data) {

            /* Prepares the buttons and message the move alert exception will contain */
            var self = this;
            var errors = '';
            var buttons = '';
            var able_buttons = [];
            var alerttype = '';
            if ('error' in data) {
                errors += self.wrongMsgServer(data, able_buttons);
                alerttype = 'danger';
            }
            else {
                errors += self.wrongMsgXml(data, able_buttons);
                alerttype = 'info';
            }
            if (able_buttons.includes('partner') && !able_buttons.includes('remove')) {
                 buttons +  = _t('<button class="dnd-alert-button" tag="remove">Remove XML</button>') +
                           _t('<button class="dnd-alert-button" tag="partner">Create Partner</button>');
            }
            else if (able_buttons.includes('tryagain')) {
                buttons + =  _t('<button id="remove_xml" class="dnd-alert-button remove" tag="remove" t-on-click="remove_xml">Remove XML</button>') +
                           _t('<button class="dnd-alert-button" tag="tryagain" id="tryagain">Try again</button>');
            }
            else if (able_buttons.includes('remove')) {
                buttons += _t('<button class="dnd-alert-button" tag="remove" t-on-click="remove_xml">Remove XML</button>');
            }
            if (buttons.length > 0) {
                buttons += _t('<button id="remove_all_xml" class="dnd-alert-remove-all-wrong-xml-button" style="background-color: #31708f; border: 0px solid; margin: 0 5px 0 0; color: #ffffff;" tag="remove">Remove all wrong XML</button>');
            }
            return {'errors': errors, 'buttons': buttons, 'alerttype': alerttype};
        }
       wrongMsgServer(data, able_buttons) {
            /* Prepares the message to the server error */
            var typemsg = {'CheckXML': _t('Error checking XML data.'), 'CreatePartner': _t('Error creating partner.'), 'CreateMove': _t('Error creating move.')};
            var errors = '<div><span level="2">' + data.error[0] + '</span> <span level="1">' + data.error[1] + '</span>.<br>' + typemsg[data.where] + '</div>';
            able_buttons.push('tryagain');
            return errors;
        }
       wrongMsgXml(file, able_buttons) {
            /* Prepares the message to the xml errors */
            var self = this;
            var errors = '';
            var map_error = {
                unsigned: _t('<div><span level="1">UUID</span> not found in the XML.</div>'),
                version: _t('<div><span level="1">Unable to generate moves from an XML with version 3.2.</span>You can create the move manually and then attach the xml.</div>'),
                nothing: _t('<div><strong>Info!</strong> XML data could not be read correctly.</div>'),
            };
            $.each(file, function(ikey, val) {
                if (ikey === 'wrong_company_r') {
                    errors += _t('<div><span level="1">The XML Receptor RFC</span> does not match with <span level="1">your Company RFC</span>: ') +
                              _t('XML Receptor RFC: <span level="2">') + val[0] + _t(', </span> Your Company RFC: <span level="2">') + val[1] + '</span></div>';
                    able_buttons.push('remove');
                }
                if (ikey === 'wrong_company_i') {
                    errors += _t('<div><span level="1">The XML Issuer RFC</span> does not match with <span level="1">your Company RFC</span>: ') +
                              _t('XML Issuer RFC: <span level="2">') + val[0] + _t(', </span> Your Company RFC: <span level="2">') + val[1] + '</span></div>';
                    able_buttons.push('remove');
                }
                if (ikey !== 'wrong_company_r' && ikey !== 'wrong_company_i' && ikey !== 'partner_not_found' && ikey !== 'xml64' && !able_buttons.includes('remove')) {
                    able_buttons.push('remove');
                }
                if (ikey === 'partner_not_found') {
                    errors += _t('<div><span level="1">The XML partner</span> was not found: <span level="2">') + val + '</span>.</div>';
                    able_buttons.push('partner');
                }
                if (ikey === 'reference_multi') {
                    errors += _t('<div><span level="1">The XML reference</span> matches another move reference. <span level="1">Partner: </span>') + val[0] + _t('<span level="1"> Reference: </span>') + val[1] + '</div>';
                }
                if (ikey === 'currency') {
                    errors += _t('<div><span level="1">The XML Currency</span> <span level="2">') + val + _t('</span> was not found or is disabled.</div>');
                }
                if (ikey === 'taxes') {
                    errors += _t('<div><span level="1">Some taxes</span> do not exist: <span level="2">') + val.join(', ') + '</span>.</div>';
                }
                if (ikey === 'taxes_wn_accounts') {
                    errors += _t('<div><span level="1">Some taxes</span> do not have account assigned: <span level="2">') + val.join(', ') + '</span>.</div>';
                }
                if (ikey === 'uuid_duplicated') {
                    errors += _t('<div><span level="1">The XML UUID</span> belong to other move. <span level="1">UUID: </span>') + val + '</div>';
                }
                if (ikey === 'cancelled') {
                    errors += _t('<div><span level="1">The XML state</span> is CANCELLED in SATs system. ') +
                              _t('XML Folio: <span level="2">') + val[1] + '</span></div>';
                    able_buttons.push('tryagain');
                }
                if (ikey === 'folio') {
                    errors += _t('<div><span level="1">The XML Folio</span> does not match with <span level="1">Partner document number</span>: ') +
                              _t('XML Folio: <span level="2">') + val[0] + _t(', </span> Partner document number: <span level="2">') + val[1] + '</span></div>';
                }
                if (ikey === 'amount') {
                    errors += _t('<div><span level="1">The XML amount total</span> does not match with <span level="1">move total</span>: ') +
                              _t('XML amount total: <span level="2">') + val[0] + _t(', </span> Move total: <span level="2">') + val[1] + '</span></div>';
                    able_buttons.push('tryagain');
                }
                if (ikey === 'amount_tax') {
                    errors += _t('<div><span level="1">The XML tax total amount</span> does not match with <span level="1">Move tax total amount</span>: ') +
                              _t('XML tax total: <span level="2">') + val[0] + _t(', </span> Move tax total: <span level="2">') + val[1] + '</span> Ref: ' + val[2] + '</div>';
                    able_buttons.push('tryagain');
                }
                if (ikey === 'moves_related_not_found') {
                    errors += _t('<div>The <span level="1">TipoDeComprobante</span> is <span level="1">"E"</span> and The XML UUIDs are not related to any move. <span level="1">UUID: </span>') + val + '</div>';
                    able_buttons.push('tryagain');
                }
                if (ikey === 'no_node_related_uuids') {
                    errors += _t('<div>The <span level="1">TipoDeComprobante</span> is <span level="1">"E"</span> and The node CFDI related is not set</span> Manually reconcile with the appropiate move. <span level="1">UUID: </span>') + val + '</div>';
                }
                if (ikey === 'invoice_not_found') {
                    errors += _t('<div><span level="1">The DocumentType is "E" and The XML UUID</span> is not related to any invoice. <span level="1">UUID: </span>') + val +'</div>';
                }
                if (Object.prototype.hasOwnProperty.call(map_error, ikey)) {
                    errors += map_error[ikey];
                }
            });
            return errors;
        }
       sendErrorToServer(xml64, key, function_def) {
            /* Sends again the base64 file string to the server to retry to create the move, or
            sends the partner's data to be created in db if does not exist */
            var self = this;
            var xml_file = {};
            xml_file[key] = xml64;
            var options = self.getFields();
            var ctx = self.env.model.root.context;
            ctx.account_id = options.account_id;
            rpc.query({
                model: 'multi.file.attach.xmls.wizard',
                method: function_def,
                args: [xml_file],
                context: ctx,
            }).then(function(data) {
                var wrongfiles = data.wrongfiles;
                var attachments = data.attachments;
                $.each(attachments, function(rkey, result) {
                    var alertobj = $('#alertscontent div[tag="' + rkey + '"].alert.dnd-alert');
                    self.attachment_ids.push(result.attachment_id);
                    self.createdCorrectly(rkey);
                    self.removeWrongAlerts(alertobj, rkey, false);
                });
                $.each(wrongfiles, function(rkey, result) {
                    var alert_parts = self.prepareWrongAlert(rkey, result);
                    var alertobj = $('#alertscontent div[tag="' + rkey + '"].alert.dnd-alert');
                    var footer = alertobj.find('div:last-child span:not(.index-alert)');
                    alertobj.removeClass('alert-danger alert-info').addClass('alert-' + alert_parts.alerttype);
                    alertobj.html(alert_parts.errors + '<div>' + alert_parts.buttons + '</div>');
                    alertobj.find('div:last-child').append(footer);
                });
            });
        }
       removeWrongAlerts(alertobj, filekey, removefile) {
            /* Removes the current error alert to continue with the others */
            var self = this;
            alertobj.slideUp(500, function() {
                delete self.alerts_in_queue.alertHTML[filekey];
                if (removefile) {
                    delete self.files[filekey];
                    $('#filescontent div[title="' + filekey + '"]').animate({'opacity': '0'}, 500, function() {
                        $.when($(this).remove()).done(function() {
                            self.continueAlert(alertobj);
                        });
                    });
                }
                else {
                    self.continueAlert(alertobj);
                }
            });
        }
       continueAlert(alertobj) {
            /* After the error alert is removed, execute the next actions
            (Next error alert, Restarts to attach more files, or Shows the final success alert) */
            var self = this;
            $.when(alertobj.remove()).done(function() {
                if (self.alerts_in_queue.alertHTML && Object.keys(self.alerts_in_queue.alertHTML).length > 0) {
                    self.nextWrongAlert();
                }
                else if (Object.keys(self.files).length === 0) {
                    self.restart();
                }
                else {
                    self.correctFinalRegistry();
                }
            });
        }
       nextWrongAlert() {
            /* Shows the next error alert */
            var self = this;
            var keys = Object.keys(self.alerts_in_queue.alertHTML);
            var alert = self.alerts_in_queue.alertHTML[keys[0]].alert.hide();
            alert.find('div:last-child .index-alert').html(self.alerts_in_queue.total - (keys.length - 1));
            $('#alertscontent').html(alert);
            alert.slideDown(500);
        }
       restart() {
            /* Restarts all the variables and restores all the DOM element to attach more new files */
            this.files = {};
            this.attachment_ids = [];
            this.uploading_files = false;
            this.alerts_in_queue = {};
            $("#dragandrophandler").show();
            $("#filescontent").html('');
            $("#files").val('');
            $('#dndfooter button#save').attr('disabled', false);
            $('#alertscontent div.alert').remove();
            $('#dndfooter button#show').hide();
        }
       correctFinalRegistry() {
            /* Shows the final success alert and the button to see the moves created */
            var self = this;
            var alert = $('<div class="alert alert-success dnd-alert">' + _t('Your moves were created correctly') + '.</div>').hide();
            $('#alertscontent').html(alert);
            alert.slideDown(500, function() {
            $('#dndfooter').find("#show").show();
            });
        }
}

attachXmlsWizard.template = "l10n_mx_sat_sync_itadmin_ee.multi_attach_xmls_template";

registry.category("fields").add("multi_attach_xmls_wizard_widget", attachXmlsWizard);