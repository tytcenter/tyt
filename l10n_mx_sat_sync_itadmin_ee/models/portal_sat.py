# -*- coding: utf-8 -*-
#!/usr/bin/env python

import base64
import calendar
import datetime
from copy import deepcopy

#try:
#    from HTMLParser import HTMLParser
#except ImportError:
from html.parser import HTMLParser
    
from uuid import UUID
#from xml.etree import ElementTree as ET
from lxml import etree
from OpenSSL import crypto
#from pathlib import Path

from requests import Session, exceptions, adapters

# v2
from io import BytesIO
from PIL import Image


import logging
_logger = logging.getLogger(__name__)

TIMEOUT = 120
TRY_COUNT = 3
VERIFY_CERT = True

class FormValues(HTMLParser):
    _description = 'FormValues'

    def __init__(self):
        super().__init__()
        #HTMLParser.__init__(self)
        self.values = {}
    def handle_starttag(self, tag, attrs):
        if tag in ('input', 'select'):
            a = dict(attrs)
            if a.get('type', '') and a['type'] == 'hidden':
                if 'name' in a and 'value' in a:
                    self.values[a['name']] = a['value']

class FormLoginValues(HTMLParser):
    _description = 'FormLoginValues'

    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            attrib = dict(attrs)
            try:
                self.values[attrib['id']] = attrib['value']
            except:
                pass


class ImageCaptcha(HTMLParser):
    _description = 'ImageCaptcha'

    def __init__(self):
        super().__init__()
        self.image = ''

    def handle_starttag(self, tag, attrs):
        attrib = dict(attrs)
        info = 'data:image/jpeg;base64,'
        if tag == 'img'and attrib['src'].startswith(info):
            self.image = attrib['src'][len(info):]


class Filters(object):
    _description = 'Filters' 

    def __init__(self, args):
        self.date_from = args['date_from']
        self.day = args.get('day', False)
        self.emitidas = args['emitidas']
        self.date_to = None
        if self.date_from:
            self.date_to = args.get('date_to', self._now()).replace(
                hour=23, minute=59, second=59, microsecond=0)
        self.uuid = str(args.get('uuid', ''))
        self.stop = False
        self.hour = False
        self.minute = False
        self._init_values(args)
    def __str__(self):
        if self.uuid:
            msg = 'Descargar por UUID'
        elif self.hour:
            msg = 'Descargar por HORA'
        elif self.day:
            msg = 'Descargar por DIA'
        else:
            msg = 'Descargar por MES'
        tipo = 'Recibidas'
        if self.emitidas:
            tipo = 'Emitidas'
        if self.uuid:
            return '{} - {} - {}'.format(msg, self.uuid, tipo)
        else:
            return '{} - {} - {} - {}'.format(msg, self.date_from, self.date_to, tipo)
    def _now(self):
        if self.day:
            n = self.date_from
        else:
            last_day = calendar.monthrange(
                self.date_from.year, self.date_from.month)[1]
            n = datetime.datetime(self.date_from.year, self.date_from.month, last_day)
        return n
    def _init_values(self, args):
        #~ print ('ARGS', args)
        status = '-1'
        type_cfdi = args.get('type_cfdi', '-1')
        center_filter = 'RdoFechas'
        if self.uuid:
            center_filter = 'RdoFolioFiscal'
        rfc_receptor = args.get('rfc_emisor', '')
        if self.emitidas:
            rfc_receptor = args.get('rfc_receptor', '')
        script_manager = 'ctl00$MainContent$UpnlBusqueda|ctl00$MainContent$BtnBusqueda'
        self._post = {
            '__ASYNCPOST': 'true',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__VIEWSTATEENCRYPTED': '',
            'ctl00$ScriptManager1': script_manager,
            'ctl00$MainContent$hfInicialBool': 'false',
            'ctl00$MainContent$BtnBusqueda': 'Buscar CFDI',
            'ctl00$MainContent$TxtUUID': self.uuid,
            'ctl00$MainContent$FiltroCentral': center_filter,
            'ctl00$MainContent$TxtRfcReceptor': rfc_receptor,
            'ctl00$MainContent$DdlEstadoComprobante': status,
            'ctl00$MainContent$ddlComplementos': type_cfdi,
        }
        return
    
    def get_post(self):
        start_hour = '0'
        start_minute = '0'
        start_second = '0'
        end_hour = '0'
        end_minute = '0'
        end_second = '0'
        if self.date_from:
            start_hour = str(self.date_from.hour)
            start_minute = str(self.date_from.minute)
            start_second = str(self.date_from.second)
            end_hour = str(self.date_to.hour)
            end_minute = str(self.date_to.minute)
            end_second = str(self.date_to.second)
        if self.emitidas:
            year1 = '0'
            year2 = '0'
            start = ''
            end = ''
            if self.date_from:
                year1 = str(self.date_from.year)
                year2 = str(self.date_to.year)
                start = self.date_from.strftime('%d/%m/%Y')
                end = self.date_to.strftime('%d/%m/%Y')
            data = {
                'ctl00$MainContent$hfInicial': year1,
                'ctl00$MainContent$CldFechaInicial2$Calendario_text': start,
                'ctl00$MainContent$CldFechaInicial2$DdlHora': start_hour,
                'ctl00$MainContent$CldFechaInicial2$DdlMinuto': start_minute,
                'ctl00$MainContent$CldFechaInicial2$DdlSegundo': start_second,
                'ctl00$MainContent$hfFinal': year2,
                'ctl00$MainContent$CldFechaFinal2$Calendario_text': end,
                'ctl00$MainContent$CldFechaFinal2$DdlHora': end_hour,
                'ctl00$MainContent$CldFechaFinal2$DdlMinuto': end_minute,
                'ctl00$MainContent$CldFechaFinal2$DdlSegundo': end_second,
            }
        else:
            year = '0'
            month = '0'
            if self.date_from:
                year = str(self.date_from.year)
                month = str(self.date_from.month)
            day = '00'
            if self.day:
                day = '{:02d}'.format(self.date_from.day)
            data = {
                'ctl00$MainContent$CldFecha$DdlAnio': year,
                'ctl00$MainContent$CldFecha$DdlMes': month,
                'ctl00$MainContent$CldFecha$DdlDia': day,
                'ctl00$MainContent$CldFecha$DdlHora': start_hour,
                'ctl00$MainContent$CldFecha$DdlMinuto': start_minute,
                'ctl00$MainContent$CldFecha$DdlSegundo': start_second,
                'ctl00$MainContent$CldFecha$DdlHoraFin': end_hour,
                'ctl00$MainContent$CldFecha$DdlMinutoFin': end_minute,
                'ctl00$MainContent$CldFecha$DdlSegundoFin': end_second,
            }
        self._post.update(data)
        return self._post


class Invoice(HTMLParser):
    _description = 'Invoice'

    START_PAGE = 'ContenedorDinamico'
    # ~ START_PAGE = 'ctl00_MainContent_ContenedorDinamico'
    URL = 'https://portalcfdi.facturaelectronica.sat.gob.mx/'
    END_PAGE = 'ctl00_MainContent_pageNavPosition'
    LIMIT_RECORDS = 'ctl00_MainContent_PnlLimiteRegistros'
    NOT_RECORDS = 'ctl00_MainContent_PnlNoResultados'
    TEMPLATE_DATE = '%Y-%m-%dT%H:%M:%S'
    def __init__(self):
        super().__init__()
        self._is_div_page = False
        self._col = 0
        self._current_tag = ''
        self._last_link = ''
        self._last_link_pdf = ''
        self._last_uuid = ''
        self._last_status = ''
        self._last_date_cfdi = ''
        self._last_date_timbre = ''
        self._last_pac = ''
        self._last_total = ''
        self._last_type = ''
        self._last_date_cancel = ''
        self._last_emisor_rfc = ''
        self._last_emisor = ''
        self._last_receptor_rfc = ''
        self._last_receptor = ''
        self.invoices = []
        self.not_found = False
        self.limit = False

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        if tag == 'div':
            attrib = dict(attrs)
            if 'id' in attrib and attrib['id'] == self.NOT_RECORDS \
                and 'inline' in attrib['style']:
                self.not_found = True
            elif 'id' in attrib and attrib['id'] == self.LIMIT_RECORDS:
                self.limit = True
            elif 'id' in attrib and attrib['id'] == self.START_PAGE:
                self._is_div_page = True
            elif 'id' in attrib and attrib['id'] == self.END_PAGE:
                self._is_div_page = False
        elif self._is_div_page and tag == 'td':
            self._col +=1
        elif tag == 'span':
            attrib = dict(attrs)
            if attrib.get('id', '') == 'BtnDescarga':
                self._last_link = attrib['onclick'].split("'")[1]

    def handle_endtag(self, tag):
        if self._is_div_page and tag == 'tr':
            if self._last_uuid:
                url_xml = ''
                if self._last_link:
                    url_xml = '{}{}'.format(self.URL, self._last_link)
                    self._last_link = ''
                url_pdf = ''
                if self._last_link_pdf:
                    url_pdf = '{}{}'.format(self.URL, self._last_link_pdf)

                date_cancel = None
                if self._last_date_cancel:
                    date_cancel = datetime.datetime.strptime(
                        self._last_date_cancel, self.TEMPLATE_DATE)
                invoice = (self._last_uuid,
                    {
                        'url': url_xml,
                        'acuse': url_pdf,
                        'estatus': self._last_status,
                        'date_cfdi': datetime.datetime.strptime(
                            self._last_date_cfdi, self.TEMPLATE_DATE),
                        'date_timbre': datetime.datetime.strptime(
                            self._last_date_timbre, self.TEMPLATE_DATE),
                        'date_cancel': date_cancel,
                        'rfc_pac': self._last_pac,
                        'total': float(self._last_total),
                        'tipo': self._last_type,
                        'emisor': self._last_emisor,
                        'rfc_emisor': self._last_emisor_rfc,
                        'receptor': self._last_receptor,
                        'rfc_receptor': self._last_receptor_rfc,
                    }
                )
                self.invoices.append(invoice)
            self._last_link_pdf = ''
            self._last_uuid = ''
            self._last_status = ''
            self._last_date_cancel = ''
            self._last_emisor_rfc = ''
            self._last_emisor = ''
            self._last_receptor_rfc = ''
            self._last_receptor = ''
            self._last_date_cfdi = ''
            self._last_date_timbre = ''
            self._last_pac = ''
            self._last_total = ''
            self._last_type = ''
            self._col = 0

    def handle_data(self, data):
        cv = data.strip()
        if self._is_div_page and self._current_tag == 'span' and cv:
            if self._col == 1:
                try:
                    UUID(cv)
                    self._last_uuid = cv
                except ValueError:
                    pass
            elif self._col == 2:
                self._last_emisor_rfc = cv
            elif self._col == 3:
                self._last_emisor = cv
            elif self._col == 4:
                self._last_receptor_rfc = cv
            elif self._col == 5:
                self._last_receptor = cv
            elif self._col == 6:
                self._last_date_cfdi = cv
            elif self._col == 7:
                self._last_date_timbre = cv
            elif self._col == 8:
                self._last_pac = cv
            elif self._col == 9:
                self._last_total = cv.replace('$', '').replace(',', '')
            elif self._col == 10:
                self._last_type = cv.lower()
            elif self._col == 12:
                self._last_status = cv
            elif self._col == 14:
                self._last_date_cancel = cv


class PortalSAT(object):
    _description = 'PortalSAT'

    URL_MAIN = 'https://portalcfdi.facturaelectronica.sat.gob.mx/'
    HOST = 'cfdiau.sat.gob.mx'
    BROWSER = 'Mozilla/5.0 (X11; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0'
    REFERER = 'https://cfdiau.sat.gob.mx/nidp/app/login?id=SATUPCFDiCon&sid=0&option=credential&sid=0'

    PORTAL = 'portalcfdi.facturaelectronica.sat.gob.mx'
    URL_LOGIN = 'https://{}/nidp/app/login'.format(HOST)
    #~ URL_LOGIN = 'https://{}/nidp/wsfed/ep'.format(HOST)
    URL_FORM = 'https://{}/nidp/app/login?sid=0&sid=0'.format(HOST)
    URL_PORTAL = 'https://portalcfdi.facturaelectronica.sat.gob.mx/'
    URL_CONTROL = 'https://cfdicontribuyentes.accesscontrol.windows.net/v2/wsfederation'
    URL_CONSULTA = URL_PORTAL + 'Consulta.aspx'
    URL_RECEPTOR = URL_PORTAL + 'ConsultaReceptor.aspx'
    URL_EMISOR = URL_PORTAL + 'ConsultaEmisor.aspx'
    URL_LOGOUT = URL_PORTAL + 'logout.aspx?salir=y'
    DIR_EMITIDAS = 'emitidas'
    DIR_RECIBIDAS = 'recibidas'

    def __init__(self, rfc, target, sin):
        self._rfc = rfc
        self.error = ''
        self.is_connect = False
        self.not_network = False
        self.only_search = False
        self.only_test = False
        self.sin_sub = sin
        self._only_status = False
        self._init_values(target)

    def _init_values(self, target):
        self._folder = target
#         if target and not self.sin_sub:
#             self._folder = self._create_folders(target)
        self._emitidas = False
        self._current_year = datetime.datetime.now().year
        self._session = Session()
        a = adapters.HTTPAdapter(pool_connections=512, pool_maxsize=512, max_retries=5)
        self._session.mount('https://', a)
        return

    def _get_post_form_dates(self):
        post = {}
        post['__ASYNCPOST'] = 'true'
        post['__EVENTARGUMENT'] = ''
        post['__EVENTTARGET'] = 'ctl00$MainContent$RdoFechas'
        post['__LASTFOCUS'] = ''
        post['ctl00$MainContent$CldFecha$DdlAnio'] = str(self._current_year)
        post['ctl00$MainContent$CldFecha$DdlDia'] = '0'
        post['ctl00$MainContent$CldFecha$DdlHora'] = '0'
        post['ctl00$MainContent$CldFecha$DdlHoraFin'] = '23'
        post['ctl00$MainContent$CldFecha$DdlMes'] = '1'
        post['ctl00$MainContent$CldFecha$DdlMinuto'] = '0'
        post['ctl00$MainContent$CldFecha$DdlMinutoFin'] = '59'
        post['ctl00$MainContent$CldFecha$DdlSegundo'] = '0'
        post['ctl00$MainContent$CldFecha$DdlSegundoFin'] = '59'
        post['ctl00$MainContent$DdlEstadoComprobante'] = '-1'
        post['ctl00$MainContent$FiltroCentral'] = 'RdoFechas'
        post['ctl00$MainContent$TxtRfcReceptor'] = ''
        post['ctl00$MainContent$TxtUUID'] = ''
        post['ctl00$MainContent$ddlComplementos'] = '-1'
        post['ctl00$MainContent$hfInicialBool'] = 'true'
        post['ctl00$ScriptManager1'] = \
            'ctl00$MainContent$UpnlBusqueda|ctl00$MainContent$RdoFechas'
        return post

    def _response(self, url, method='get', headers={}, data={}):
        try:
            if method == 'get':
                result = self._session.get(url, timeout=TIMEOUT, verify=VERIFY_CERT)
            else:
                result = self._session.post(url, data=data, timeout=TIMEOUT, verify=VERIFY_CERT)
            msg = '{} {} {}'.format(result.status_code, method.upper(), url)
            # ~ log.debug(msg)
            if result.status_code == 200:
                return result.text
            else:
                _logger.error(msg)
                return ''
        except exceptions.Timeout:
            msg = 'Tiempo de espera agotado'
            self.not_network = True
            _logger.error(msg)
            #self.error = msg
            return ''
        except exceptions.ConnectionError:
            msg = 'Revisa la conexión a Internet'
            self.not_network = True
            _logger.error(msg)
            #self.error = msg
            return ''

    def _read_form(self, html, form=''):
        if form == 'login':
            parser = FormLoginValues()
        else:
            parser = FormValues()
        parser.feed(html)
        return parser.values

    def _get_headers(self, host, referer, ajax=False):
        user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:49.0) Gecko/20100101 Firefox/49.0'
        acept = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

        headers = {
            'Accept': acept,
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Host': host,
            'Referer': referer,
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.BROWSER,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        if ajax:
            headers.update({
                'Cache-Control': 'no-cache',
                'X-MicrosoftAjax': 'Delta=true',
                'x-requested-with': 'XMLHttpRequest',
                'Pragma': 'no-cache',
            })
        return headers

    def _get_post_type_search(self, html):
        tipo_busqueda = 'RdoTipoBusquedaReceptor'
        if self._emitidas:
            tipo_busqueda = 'RdoTipoBusquedaEmisor'
        sm = 'ctl00$MainContent$UpnlBusqueda|ctl00$MainContent$BtnBusqueda'
        post = self._read_form(html)
        post['ctl00$MainContent$TipoBusqueda'] = tipo_busqueda
        post['__ASYNCPOST'] = 'true'
        post['__EVENTTARGET'] = ''
        post['__EVENTARGUMENT'] = ''
        post['ctl00$ScriptManager1'] = sm
        return post

    def _get_captcha(self, from_script):
        from .captcha import resolve

        URL_LOGIN = 'https://cfdiau.sat.gob.mx/nidp/wsfed/ep?id=SATUPCFDiCon&sid=0&option=credential&sid=0'
        REFERER = 'https://cfdiau.sat.gob.mx/nidp/wsfed_redir_cont_portalcfdi.jsp?wa=wsignin1.0&wtrealm={}'
        result = self._session.get(self.URL_MAIN)

        url_redirect = result.history[-1].headers['Location']
        self._session.headers['Host'] = self.HOST
        result = self._response(url_redirect)

        self._session.headers['User-Agent'] = self.BROWSER
        self._session.headers['Referer'] = REFERER.format(url_redirect)
        result = self._response(URL_LOGIN, 'post')

        url = 'https://cfdiau.sat.gob.mx/nidp/jcaptcha.jpg'
        result = self._session.get(url, timeout=TIMEOUT)

        return resolve(result.content, from_script)

    def login(self, ciec, from_script):
        HOST = 'cfdicontribuyentes.accesscontrol.windows.net'
        URL_CONTROL1 = 'https://cfdiau.sat.gob.mx/nidp/wsfed/ep?sid=0'
        ERROR = '¡Error de registro!'

        msg = 'Identificandose en el SAT'
        _logger.info(msg)

        captcha = self._get_captcha(from_script)
        if not captcha:
            return False

        data = {
            'option': 'credential',
            'Ecom_User_ID': self._rfc,
            'Ecom_Password': ciec,
            'submit': 'Enviar',
            'jcaptcha': captcha,
        }
        headers = self._get_headers(self.HOST, self.REFERER)
        response = self._response(self.URL_FORM, 'post', headers, data)

        if ERROR in response:
            msg = 'RFC o CIEC no validos o CAPTCHA erroneo'
            self.error = msg
            _logger.error(msg)
            return False

        if self.error:
            return False

        data = self._read_form(response)
        data = self._read_form(self._response(
            'https://cfdiau.sat.gob.mx/nidp/wsfed/ep?sid=0', data=data))
        data = self._read_form(self._response(
            'https://portalcfdi.facturaelectronica.sat.gob.mx/', 'post', data=data))
        data = self._read_form(self._response(
            'https://portalcfdi.facturaelectronica.sat.gob.mx/', data=data))

        # Consulta
        response = self._response(self.URL_CONSULTA, 'post', headers, data)
        msg = 'Se ha identificado en el SAT'
        _logger.info(msg)
        self.is_connect = True
        return True
    

    def _get_data_cert(self, fiel_cert_data):
        cert = crypto.load_certificate(crypto.FILETYPE_ASN1, fiel_cert_data)
        rfc = cert.get_subject().x500UniqueIdentifier.split(' ')[0]
        serie  = '{0:x}'.format(cert.get_serial_number())[1::2]
        fert = cert.get_notAfter().decode()[2:]
        return rfc, serie, fert

    def _sign(self, fiel_pem_data, data):
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, fiel_pem_data)
        sign = base64.b64encode(crypto.sign(key, data, 'sha256'))
        return base64.b64encode(sign).decode('utf-8')

    def _get_token(self, firma, co):
        co = base64.b64encode(co.encode('utf-8')).decode('utf-8')
        data = '{}#{}'.format(co, firma).encode('utf-8')
        token = base64.b64encode(data).decode('utf-8')
        return token

    def _make_data_form(self, fiel_cert_data, fiel_pem_data , values):
        rfc, serie, fert = self._get_data_cert(fiel_cert_data)
        co = '{}|{}|{}'.format(values['tokenuuid'], rfc, serie)
        firma = self._sign(fiel_pem_data, co)
        token = self._get_token(firma, co)
        keys = ('credentialsRequired', 'guid', 'ks', 'urlApplet')
        data = {k: values[k] for k in keys}
        data['fert'] = fert
        data['token'] = token
        data['arc'] = ''
        data['placer'] = ''
        data['secuence'] = ''
        data['seeder'] = ''
        data['tan'] = ''
        return data

    def login_fiel(self, fiel_cert_data, fiel_pem_data):
        HOST = 'cfdicontribuyentes.accesscontrol.windows.net'
        REFERER = 'https://cfdiau.sat.gob.mx/nidp/wsfed/ep?id=SATUPCFDiCon&sid=0&option=credential&sid=0'

        url_login = 'https://cfdiau.sat.gob.mx/nidp/app/login?id=SATx509Custom&sid=0&option=credential&sid=0'
        result = self._session.get(self.URL_MAIN)

        url_redirect = result.history[-1].headers['Location']
        self._session.headers['Host'] = self.HOST
        result = self._response(url_redirect)

        self._session.headers['User-Agent'] = self.BROWSER
        self._session.headers['Referer'] = REFERER.format(url_redirect)
        result = self._response(url_login, 'post')

        values = self._read_form(result, 'login')
        data = self._make_data_form(fiel_cert_data, fiel_pem_data, values)
        headers = self._get_headers(self.HOST, self.REFERER)
        self._session.headers.update(headers)
        result = self._response(url_login, 'post', data=data)
        if not result:
            msg = 'Error al identificarse en el SAT'
            _logger.error(msg)
            return False
        data = self._read_form(result)

        # Inicio
        response = self._response(self.URL_MAIN, 'post', data=data)
        data = self._get_post_type_search(response)
        headers = self._get_headers(self.HOST, self.URL_MAIN)

        # Consulta
        response = self._response(self.URL_CONSULTA, 'post', headers, data)
        msg = 'Se ha identificado en el SAT'
        _logger.info(msg)
        self.is_connect = True
        return True

    def _merge(self, list1, list2):
        result = list1.copy()
        result.update(list2)
        return result

    def _last_day(self, date):
        last_day = calendar.monthrange(date.year, date.month)[1]
        return datetime.datetime(date.year, date.month, last_day)

    def _get_dates(self, d1, d2):
        end = d2
        dates = []
        while True:
            d2 = self._last_day(d1)
            if d2 >= end:
                dates.append((d1, end))
                break
            dates.append((d1, d2))
            d1 = d2 + datetime.timedelta(days=1)
        return dates

    def _get_dates_recibidas(self, d1, d2):
        days = (d2 - d1).days + 1
        return [d1 + datetime.timedelta(days=d) for d in range(days)]

    def _time_delta(self, days):
        now = datetime.datetime.now()
        date_from = now.replace(
            hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days)
        date_to = now.replace(hour=23, minute=59, second=59, microsecond=0)
        return date_from, date_to

    def _time_delta_recibidas(self, days):
        now = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return [now - datetime.timedelta(days=d) for d in range(days)]

    def _get_filters(self, args, emitidas=True):
        filters = []
        data = {}
        data['day'] = bool(args['dia'])
        data['uuid'] = ''
        if args['uuid']:
            data['uuid'] = str(args['uuid'])
        data['emitidas'] = emitidas
        data['rfc_emisor'] = args.get('rfc_emisor', '')
        data['rfc_receptor'] = args.get('rfc_receptor', '')
        data['type_cfdi'] = args.get('tipo_complemento', '-1')

        if args['fecha_inicial'] and args['fecha_final'] and emitidas:
            dates = self._get_dates(args['fecha_inicial'], args['fecha_final'])
            for start, end in dates:
                data['date_from'] = start
                data['date_to'] = end
                filters.append(Filters(data))
        elif args['fecha_inicial'] and args['fecha_final']:
            dates = self._get_dates_recibidas(args['fecha_inicial'], args['fecha_final'])
            is_first_date = False
            for d in dates:
                if not is_first_date:
                    data['date_from'] = d
                    is_first_date = True
                else:
                    d = d.replace(hour=0, minute=0, second=0, microsecond=0)
                    data['date_from'] = d
                data['day'] = True
                filters.append(Filters(data))
        elif args['intervalo_dias'] and emitidas:
            data['date_from'], data['date_to'] = self._time_delta(args['intervalo_dias'])
            filters.append(Filters(data))
        elif args['intervalo_dias']:
            dates = self._time_delta_recibidas(args['intervalo_dias'])
            for d in dates:
                data['date_from'] = d
                data['day'] = True
                filters.append(Filters(data))
        elif args['uuid']:
            data['date_from'] = None
            filters.append(Filters(data))
        else:
            day = args['dia'] or 1
            data['date_from'] = datetime.datetime(args['ano'], args['mes'], day)
            filters.append(Filters(data))

        return tuple(filters)

    def _segment_filter(self, filters):
        new_filters = []
        if filters.stop:
            return new_filters
        date = filters.date_from
        date_to = filters.date_to

        if filters.minute:
            for m in range(10):
                nf = deepcopy(filters)
                nf.stop = True
                nf.date_from = date + datetime.timedelta(minutes=m)
                nf.date_to = date + datetime.timedelta(minutes=m+1)
                new_filters.append(nf)
        elif filters.hour:
            minutes = tuple(range(0, 60, 10)) + (0,)
            minutes = tuple(zip(minutes, minutes[1:]))
            for m in minutes:
                nf = deepcopy(filters)
                nf.minute = True
                nf.date_from = date + datetime.timedelta(minutes=m[0])
                nf.date_to = date + datetime.timedelta(minutes=m[1])
                if m[0] == 50 and nf.date_to.hour == 23:
                    nf.date_to = nf.date_to.replace(
                        hour=nf.date_to.hour, minute=59, second=59)
                elif m[0] == 50 and nf.date_to.hour != 23:
                    nf.date_to = nf.date_to.replace(
                        hour=nf.date_to.hour+1, minute=0, second=0)
                new_filters.append(nf)
        elif filters.day:
            hours = tuple(range(0, 25))
            hours = tuple(zip(hours, hours[1:]))
            for h in hours:
                nf = deepcopy(filters)
                nf.hour = True
                nf.date_from = date + datetime.timedelta(hours=h[0])
                nf.date_to = date + datetime.timedelta(hours=h[1])
                if h[1] == 24:
                    nf.date_to = nf.date_from.replace(
                        minute=59, second=59, microsecond=0)
                new_filters.append(nf)
        else:
            last_day = calendar.monthrange(date.year, date.month)[1]
            for d in range(last_day):
                nf = deepcopy(filters)
                nf.day = True
                nf.date_from = date + datetime.timedelta(days=d)
                nf.date_to = nf.date_from.replace(
                    hour=23, minute=59, second=59, microsecond=0)
                new_filters.append(nf)
                if date_to == nf.date_to:
                    break
        return new_filters

    def _get_post(self, html):
        validos = ('EVENTTARGET', '__EVENTARGUMENT', '__LASTFOCUS', '__VIEWSTATE')
        values = html.split('|')
        post = {v: values[i+1]  for i, v in enumerate(values) if v in validos}
        return post

    def _get_status(self, invoices):
        path = '/tmp/{}.log'
        for doc in invoices:
            uuid = doc[0].upper()
            estatus = doc[1]['estatus']
            path_uuid = path.format(uuid)
            with open(path_uuid, 'w') as f:
                f.write(estatus)
            _logger.info('Estatus {}: {}'.format(estatus, path_uuid))
        return
    
    def _search_by_uuid(self, filters):
        for f in filters:
            _logger.info(str(f))
            url_search = self.URL_RECEPTOR
            folder = self.DIR_RECIBIDAS
            if f.emitidas:
                url_search = self.URL_EMISOR
                folder = self.DIR_EMITIDAS
            
            result = self._response(url_search, 'get')
            post = self._read_form(result)
            post = self._merge(post, f.get_post())
            headers = self._get_headers(self.PORTAL, url_search)
            html = self._response(url_search, 'post', headers, post)
            not_found, limit, invoices = self._get_download_links(html)
            if not_found:
                msg = '\n\tNo se encontraron documentos en el filtro:' \
                    '\n\t{}'.format(str(f))
                _logger.info(msg)
            else:
                if self._only_status:
                    return self._get_status(invoices)                
                return self._download(invoices, folder=folder)
        return {}

    def _change_to_date(self, url_search):
        result = self._response(url_search, 'get')
        values = self._read_form(result)
        post = self._merge(values, self._get_post_form_dates())
        headers = self._get_headers(self.PORTAL, url_search, True)
        result = self._response(url_search, 'post', headers, post)
        post = self._get_post(result)
        return values, post

    def _search_recibidas(self, filters):
        url_search = self.URL_RECEPTOR
        values, post_source = self._change_to_date(url_search)
        invoice_content = {}
        for f in filters:
            #_logger.info(str(f))
            post = self._merge(values, f.get_post())
            post = self._merge(post, post_source)
            headers = self._get_headers(self.PORTAL, url_search, True)
            html = self._response(url_search, 'post', headers, post)
            not_found, limit, invoices = self._get_download_links(html)
            if not_found or not invoices:
                msg = '\n\tNo se encontraron documentos en el filtro:' \
                    '\n\t{}'.format(str(f))
                _logger.info(msg)
            else:
                data = self._download(invoices, limit, f)
                if data and type(data)==dict:
                    invoice_content.update(data)
        return invoice_content

    def _search_emitidas(self, filters):
        url_search = self.URL_EMISOR
        values, post_source = self._change_to_date(url_search)
        invoice_content = {}
        for f in filters:
            _logger.info(str(f))
            post = self._merge(values, f.get_post())
            post = self._merge(post, post_source)
            headers = self._get_headers(self.PORTAL, url_search, True)
            html = self._response(url_search, 'post', headers, post)
            not_found, limit, invoices = self._get_download_links(html)
            if not_found or not invoices:
                msg = '\n\tNo se encontraron documentos en el filtro:' \
                    '\n\t{}'.format(str(f))
                _logger.info(msg)
            else:
                data = self._download(invoices, limit, f, self.DIR_EMITIDAS)
                if data and type(data)==dict:
                    invoice_content.update(data)
        return invoice_content

    def _search_by_uuid_from_file(self, opt):
        path = opt['archivo_uuids']
#         uuids = []
        with open(path) as fh:
            uuids = fh.read().split('\n')
        if not uuids:
            return {}
        t = len(uuids)
        invoice_content = {}
        for i, u in enumerate(uuids):
            msg = 'Descargando UUID {} de {}'.format(i + 1, t)
            _logger.info(msg)
            opt['uuid'] = u
            filters = self._get_filters(opt)
            data = self._search_by_uuid(filters)
            if data and type(data)==dict:
                invoice_content.update(data)
        return invoice_content

    def search(self, opt, download_option='both'):
        filters_e = ()
        filters_r = ()

        self._only_status = opt['estatus']
                
        if opt['archivo_uuids']:
            return self._search_by_uuid_from_file(opt), {}
        if opt['tipo'] == 'e' and not opt['uuid']:
            filters_e = self._get_filters(opt, True)
            return self._search_emitidas(filters_e), {}
            
        if opt['tipo'] == 'e' and opt['uuid']:
            filters_e = self._get_filters(opt, True)
            return self._search_by_uuid(filters_e), {}
            
        elif opt['tipo'] == 'r' and not opt['uuid']:
            filters_r = self._get_filters(opt, False)
            return {}, self._search_recibidas(filters_r)
            
        if opt['tipo'] == 'r' and opt['uuid']:
            filters_r = self._get_filters(opt, False)
            return self._search_by_uuid(filters_r), {}

        #Uncomment if you need to download Receiptor/Customer invoices.
        invoice_content_e, invoice_content_r = {}, {}
        if download_option=='both':
            filters_e = self._get_filters(opt, True)
            invoice_content_e = self._search_emitidas(filters_e)
            filters_r = self._get_filters(opt, False)
            invoice_content_r = self._search_recibidas(filters_r)
        elif download_option=='supplier':
            filters_r = self._get_filters(opt, False)
            invoice_content_r = self._search_recibidas(filters_r)
        elif download_option=='customer':
            filters_e = self._get_filters(opt, True)
            invoice_content_e = self._search_emitidas(filters_e)

        #Uncomment if you need to download Receiptor/Customer invoices.
        #filters_e = self._get_filters(opt, True)
        #filters_r = self._get_filters(opt, False)
        #invoice_content_e = self._search_emitidas(filters_e)
        #invoice_content_r = self._search_recibidas(filters_r)
       # 
        return invoice_content_r, invoice_content_e
    

    def _download(self, invoices, limit=False, filters=None, folder=DIR_RECIBIDAS):
        if not invoices and not limit:
            msg = '\n\tTodos los documentos han sido previamente ' \
                'descargados para el filtro.\n\t{}'.format(str(filters))
            _logger.info(msg)

            return {}
        invoices_content = {}
        if invoices and not self.only_search:
            invoices_content = self._thread_download(invoices, folder, filters)
        if limit:
            sf = self._segment_filter(filters)
            if folder == self.DIR_RECIBIDAS:
                data = self._search_recibidas(sf)
                if data and type(data)==dict:
                    invoices_content.update(data)
            else:
                data = self._search_emitidas(sf)
                if data and type(data)==dict:
                    invoices_content.update(data)
        return invoices_content

    def _thread_download(self, invoices, folder, filters):
#         threads = []
#         paths = {}
        for_download = invoices[:]
        current = 1
        total = len(for_download)
        invoice_content = {}
        for i in range(TRY_COUNT):
            for uuid, values in for_download:
                #~ name = '{}.xml'.format(uuid)
                #~ path_xml = os.path.join(self._folder, folder, name)
                #path_xml = self._make_path_xml(uuid, folder, values['date_cfdi'])
                #paths[uuid] = path_xml
                data = {
                    'url': values['url'],
                    #'path_xml': path_xml,
                    'acuse': values['acuse'],
                }
                content = self._get_xml(uuid, data, current, total)
                if content:
                    invoice_content.update({uuid: [values, content]})
                current += 1

            if len(invoice_content) == len(for_download):
                break
        if total:
            msg = '{} documentos por descargar en: {}'.format(total, str(filters))
            _logger.info(msg)
        return invoice_content

    def _get_xml(self, uuid, values, current, count):
        for i in range(TRY_COUNT):
            try:
                r = self._session.get(values['url'], stream=True, timeout=TIMEOUT)
                if r.status_code == 200:
                    return r.content

            except exceptions.Timeout:
                _logger.debug('Timeout')
                continue
            except Exception as e:
                _logger.error(str(e))
                return
        msg = 'Tiempo de espera agotado para el documento: {}'.format(uuid)
        _logger.error(msg)
        return

    def _get_download_links(self, html):
        parser = Invoice()
        parser.feed(html)
        return parser.not_found, parser.limit, parser.invoices

    def logout(self):
        msg = 'Cerrando sessión en el SAT'
        _logger.debug(msg)
        respuesta = self._response(self.URL_LOGOUT)
        self.is_connect = False
        msg = 'Sesión cerrada en el SAT'
        _logger.info(msg)
        return
