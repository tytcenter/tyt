

import base64

from lxml import etree, objectify

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from ..models.special_dict import CaselessDictionary

TYPE_CFDI22_TO_CFDI33 = {
    'ingreso': 'I',
    'egreso': 'E',
    'traslado': 'T',
    'nomina': 'N',
    'pago': 'P',
}


class AttachXmlsWizard(models.TransientModel):
    _name = 'multi.file.attach.xmls.wizard'
    _description = 'AttachXmlsWizard'
    
    dragndrop = fields.Char()

    @api.model
    def remove_wrong_file(self, files):
        wrong_file_dict = self.check_xml(files)
        remove_list = []
        if 'wrongfiles' in wrong_file_dict.keys():
            for key in wrong_file_dict['wrongfiles']:
                value_keys = wrong_file_dict['wrongfiles'][key].keys()
                if 'uuid_duplicated' in value_keys:
                    remove_list.append(key)
        return remove_list

    @staticmethod
    def _xml2capitalize(xml):
        """Receive 1 lxml etree object and change all attrib to Capitalize.
        """
        def recursive_lxml(element):
            for attrib, value in element.attrib.items():
                new_attrib = "%s%s" % (attrib[0].upper(), attrib[1:])
                element.attrib.update({new_attrib: value})

            for child in element.getchildren():
                child = recursive_lxml(child)
            return element
        return recursive_lxml(xml)

    @staticmethod
    def _l10n_mx_edi_convert_cfdi32_to_cfdi33(xml):
        """Convert a xml from cfdi32 to cfdi33
        :param xml: The xml 32 in lxml.objectify object
        :return: A xml 33 in lxml.objectify object
        """
        if xml.get('version', None) != '3.2':
            return xml
        # TODO: Process negative taxes "Retenciones" node
        # TODO: Process payment term
        xml = AttachXmlsWizard._xml2capitalize(xml)
        xml.attrib.update({
            'TipoDeComprobante': TYPE_CFDI22_TO_CFDI33[
                xml.attrib['tipoDeComprobante']],
            'Version': '3.3',
            'MetodoPago': 'PPD',
        })
        return xml

    
    @api.model
    def l10n_mx_edi_get_tfd_etree(self, cfdi):
        '''Get the TimbreFiscalDigital node from the cfdi.

        :param cfdi: The cfdi as etree
        :return: the TimbreFiscalDigital node
        '''
        if not hasattr(cfdi, 'Complemento'):
            return None
        attribute = 'tfd:TimbreFiscalDigital[1]'
        namespace = {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}
        for Complemento in cfdi.Complemento:
            node = Complemento.xpath(attribute, namespaces=namespace)
            if node:
                break
        return node[0] if node else None
    
    @api.model
    def check_xml(self, files):
        """ Validate that attributes in the xml before create invoice
        or attach xml in it
        :param files: dictionary of CFDIs in b64
        :type files: dict
        param account_id: The account by default that must be used in the
        lines of the invoice if this is created
        :type account_id: int
        :return: the Result of the CFDI validation
        :rtype: dict
        """
        if not isinstance(files, dict):
            raise UserError(_("Something went wrong. The parameter for XML "
                              "files must be a dictionary."))
        wrongfiles = {}
        attachments = {}
        attachment_uuids = {}
        attach_obj = self.env['ir.attachment']
        company = self.env.company
        company_vat = company.vat
        company_id = company.id
        NSMAP = {
                 'xsi':'http://www.w3.org/2001/XMLSchema-instance',
                 'cfdi':'http://www.sat.gob.mx/cfd/3', 
                 'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
                 'pago10': 'http://www.sat.gob.mx/Pagos',
                 }
        for key, xml64 in files.items():
            try:
                if isinstance(xml64, bytes):
                    xml64 = xml64.decode()
                xml_str = base64.b64decode(xml64.replace('data:text/xml;base64,', ''))
                # Fix the CFDIs emitted by the SAT
                xml_str = xml_str.replace(b'xmlns:schemaLocation', b'xsi:schemaLocation')
                xml = objectify.fromstring(xml_str)
                tree = etree.fromstring(xml_str)
            except (AttributeError, SyntaxError) as exce:
                wrongfiles.update({key: {
                    'xml64': xml64, 'where': 'CheckXML',
                    'error': [exce.__class__.__name__, str(exce)]}})
                continue
            xml = self._l10n_mx_edi_convert_cfdi32_to_cfdi33(xml)
            xml_tfd = self.l10n_mx_edi_get_tfd_etree(xml)
            
            xml_uuid = False if xml_tfd is None else xml_tfd.get('UUID', '')
            
            if not xml_uuid:
                msg = {'signed': True, 'xml64': True}
                wrongfiles.update({key: msg})
                continue
            else:
                xml_uuid = xml_uuid.upper()

            cfdi_type = xml.get('TipoDeComprobante', 'I')
            receptor = xml.Receptor.attrib or {}
            receptor_rfc = receptor.get('Rfc','')
            if receptor_rfc == company_vat:
                cfdi_type = 'S'+cfdi_type
            
            try:
                ns = tree.nsmap
                ns.update({'re': 'http://exslt.org/regular-expressions'})
            except Exception:
                ns = {'re': 'http://exslt.org/regular-expressions'}
            
            cfdi_version = tree.get("Version",'4.0')
            if cfdi_version=='4.0':
                NSMAP.update({'cfdi':'http://www.sat.gob.mx/cfd/4', 'pago20': 'http://www.sat.gob.mx/Pagos20',})
            else:
                NSMAP.update({'cfdi':'http://www.sat.gob.mx/cfd/3', 'pago10': 'http://www.sat.gob.mx/Pagos',})
            
            if cfdi_type in ['I','E','P','N','T']:
                element_tag = 'Receptor'
            else:
                element_tag = 'Emisor'
            try:
                elements = tree.xpath("//*[re:test(local-name(), '%s','i')]"%(element_tag), namespaces=ns)
            except Exception:
                elements = None
            
            client_rfc, client_name = '', ''
            if elements:
                attrib_dict = CaselessDictionary(dict(elements[0].attrib))
                client_rfc = attrib_dict.get('rfc') 
                client_name = attrib_dict.get('nombre')

            monto_total = 0
            if cfdi_type=='P' or cfdi_type=='SP':

                Complemento = tree.findall('cfdi:Complemento', NSMAP)
                for complementos in Complemento:
                   if cfdi_version == '4.0':
                      pagos = complementos.find('pago20:Pagos', NSMAP)
                      pago = pagos.find('pago20:Totales', NSMAP)
                      monto_total = pago.attrib['MontoTotalPagos']
                   else:
                      pagos = complementos.find('pago10:Pagos', NSMAP)
                      try:
                         pago = pagos.find('pago10:Pago',NSMAP)
                         monto_total = pago.attrib['Monto']
                      except Exception as e:
                         for payment in pagos.find('pago10:Pago',NSMAP):
                            monto_total += float(payment.attrib['Monto'])
                   if pagos:
                       break
            else:
                monto_total = tree.get('Total', tree.get('total'))

            filename = xml_uuid + '.xml'
            vals = {
                    'cfdi_type' : cfdi_type,
                    'cfdi_uuid' : xml_uuid,
                    'rfc_tercero' : client_rfc,
                    'nombre_tercero' : client_name,
                    'cfdi_total' : monto_total, 
                    'date_cfdi' : tree.get('Fecha',tree.get('fecha')),
                    'serie_folio' : tree.get('Folio',tree.get('folio')),
                    'name' : filename,
                    'store_fname' : filename,
                    'datas' : xml64.replace('data:text/xml;base64,', ''),
                    'type' :'binary',
                    'company_id' :company_id,
                    }
                    
            attachment_uuids.update({xml_uuid : [vals, key]})
            #uuids.append(xml_uuid)
            
        
        attas = attach_obj.sudo().search([('cfdi_uuid','in',list(attachment_uuids.keys())), ('company_id', '=', company_id)])
        exist_uuids = dict([(att.cfdi_uuid, att.id) for att in attas]) #attas.mapped('cfdi_uuid')
        
        
        for uuid, data in attachment_uuids.items():
            key = data[1]
            if uuid in exist_uuids:
                attachments.update({key: {'attachment_id': exist_uuids.get(uuid)}})
                continue
            vals = data[0]
            #cfdi_type ='S'+cfdi_type
            attach_rec = attach_obj.create(vals)
            attachments.update({key: {'attachment_id': attach_rec.id}})
        
        return {'wrongfiles': wrongfiles,
                'attachments': attachments}

