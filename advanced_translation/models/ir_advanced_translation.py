# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __openerp__.py
#
##############################################################################

import logging
import re
import sys
import threading
import locale

from contextlib import contextmanager

from openerp import models, fields, api, _

logger = logging.getLogger(__name__)

LOCALE_LOCK = threading.Lock()


@contextmanager
def setlocale(name):
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, (name, 'UTF-8'))
        finally:
            locale.setlocale(locale.LC_ALL, saved)


class IrAdvancedTranslation(models.Model):
    """ Used to translate terms in context of a subject that can be
    male / female and singular / plural.
    """
    _name = 'ir.advanced.translation'
    _description = 'Advanced translation terms'

    src = fields.Text(required=True, translate=False)
    lang = fields.Selection('_get_lang', required=True)
    group = fields.Char()
    male_singular = fields.Text(translate=False)
    male_plural = fields.Text(translate=False)
    female_singular = fields.Text(translate=False)
    female_plural = fields.Text(translate=False)

    _sql_constraints = [
        ('unique_term', "unique(src, lang)", "The term already exists")
    ]

    @api.model
    def _get_lang(self):
        langs = self.env['res.lang'].search([])
        return [(l.code, l.name) for l in langs]

    @api.model
    def get(self, src, female=False, plural=False):
        """ Returns the translation term. """
        term = self.search([
            ('src', '=', src),
            ('lang', '=', self.env.lang)])
        if not term:
            return _(src)
        if female and plural:
            return term.female_plural or ''
        if female:
            return term.female_singular or ''
        if plural:
            return term.male_plural or ''
        return term.male_singular


class AdvancedTranslatable(models.AbstractModel):
    """ Inherit this class in order to let your model fetch keywords
    based on the source recordset and a gender field in the model.
    """
    _name = 'translatable.model'

    gender = fields.Selection([
        ('M', 'Male'),
        ('F', 'Female'),
    ], default='M')

    @api.multi
    def get(self, keyword):
        plural = len(self) > 1
        male = self.filtered(lambda c: c.gender == 'M')
        female = self.filtered(lambda c: c.gender == 'F')
        advanced_translation = self.env['ir.advanced.translation']
        if plural and female and not male:
            return advanced_translation.get(keyword, True, True)
        elif plural:
            return advanced_translation.get(keyword, plural=True)
        elif female and not male:
            return advanced_translation.get(keyword, female=True)
        else:
            return advanced_translation.get(keyword)

    @api.multi
    def translate(self, field):
        """ helps getting the translated value of a
        char/selection field by adding a translate function.
        """
        pattern_keyword = re.compile("(\\{)(.*)(\\})")

        def _replace_keyword(match):
            return self.get(match.group(2))

        res = list()
        field_path = field.split('.')
        definition = self.fields_get([field_path[0]]).get(field_path[0])
        if definition:
            for record in self:
                raw_value = record
                for field_traversal in field_path:
                    raw_value = getattr(raw_value, field_traversal, False)
                if raw_value:
                    val = False
                    if definition['type'] in ('char', 'text') or isinstance(
                            raw_value, basestring) and definition['type'] !=\
                            'selection':
                        val = _(raw_value)
                    elif definition['type'] == 'selection':
                        val = _(dict(definition['selection'])[raw_value])
                    if val:
                        val = pattern_keyword.sub(_replace_keyword, val)
                        res.append(val)
        if len(res) == 1:
            res = res[0]
        return res or ''

    @api.multi
    def get_list(self, field, max=sys.maxint, substitution=None):
        """
        Get a list of values, separated with commas. (last separator 'and')
        :param field: the field values to retrieve from the recordset
        :param max: optional max number of values to be displayed
        :param substitution: optional substitution text, if number of values is
                             greater than max number provided
        :return: string of comma separated values
        """
        values = self.translate(field)
        if isinstance(values, list):
            values = list(set(values))
            if len(values) > max:
                if substitution:
                    return substitution
                values = values[:max]
            if len(values) > 1:
                res_string = ', '.join(values[:-1])
                res_string += ' ' + _('and') + ' ' + values[-1]
            else:
                res_string = values[0]
            values = res_string
        return values

    @api.multi
    def get_date(self, field, date_type='date_short'):
        """
        Useful to format a date field in a given language
        :param field: the date field inside the model
        :param date_type: a valid src of a ir.advanced.translation date format
        :return: the formatted dates
        """
        _format = self.env['ir.advanced.translation'].get(date_type).encode(
            'utf-8')
        dates = map(fields.Date.from_string, self.mapped(field))
        with setlocale(self.env.lang):
            dates_string = list(set([
                d.strftime(_format).decode('utf-8') for d in dates
            ]))
        if len(dates_string) > 1:
            res_string = ', '.join(dates_string[:-1])
            res_string += ' ' + _('and') + ' ' + dates_string[-1]
        else:
            res_string = dates_string[0]
        return res_string
