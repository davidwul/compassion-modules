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
from datetime import date, timedelta
from openerp import fields, models, api, _
from openerp.exceptions import Warning

from ..mappings.gift_mapping import CreateGiftMapping
from openerp.addons.sponsorship_compassion.models.product import \
    GIFT_NAMES, GIFT_CATEGORY


class SponsorshipGift(models.Model):
    _name = 'sponsorship.gift'
    _inherit = ['translatable.model', 'mail.thread']
    _description = 'Sponsorship Gift'
    _order = 'gift_date desc,id desc'

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    # Related records
    #################
    sponsorship_id = fields.Many2one(
        'recurring.contract', 'Sponsorship', required=True
    )
    partner_id = fields.Many2one(
        'res.partner', 'Partner', related='sponsorship_id.partner_id',
        store=True
    )
    project_id = fields.Many2one(
        'compassion.project', 'Project',
        related='sponsorship_id.project_id', store=True
    )
    project_suspended = fields.Boolean(
        related='project_id.hold_gifts', track_visibility='onchange'
    )
    child_id = fields.Many2one(
        'compassion.child', 'Child', related='sponsorship_id.child_id',
        store=True
    )
    invoice_line_ids = fields.One2many(
        'account.invoice.line', 'gift_id', string='Invoice lines',
        readonly=True
    )
    payment_id = fields.Many2one(
        'account.move', 'GMC Payment', copy=False
    )
    message_id = fields.Many2one(
        'gmc.message.pool', 'GMC message', copy=False
    )

    # Gift information
    ##################
    name = fields.Char(compute='_compute_name', translate=False)
    gmc_gift_id = fields.Char(readonly=True, copy=False)
    gift_date = fields.Date(
        compute='_compute_invoice_fields',
        inverse=lambda g: True, store=True
    )
    date_partner_paid = fields.Date(
        compute='_compute_invoice_fields',
        inverse=lambda g: True, store=True
    )
    date_sent = fields.Datetime(related='message_id.process_date')
    amount = fields.Float(
        compute='_compute_invoice_fields',
        inverse=lambda g: True, store=True, track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', default=lambda s:
                                  s.env.user.company_id.currency_id)
    currency_usd = fields.Many2one('res.currency', compute='_compute_usd')
    exchange_rate = fields.Float(readonly=True, copy=False)
    amount_us_dollars = fields.Float('Amount due', readonly=True, copy=False)
    instructions = fields.Char()
    gift_type = fields.Selection('get_gift_type_selection', required=True)
    attribution = fields.Selection('get_gift_attributions', required=True)
    sponsorship_gift_type = fields.Selection('get_sponsorship_gifts')
    state = fields.Selection([
        ('draft', _('Draft')),
        ('verify', _('Verify')),
        ('open', _('Pending')),
        ('In Progress', _('In Progress')),
        ('Delivered', _('Delivered')),
        ('Undeliverable', _('Undeliverable')),
    ], default='draft', readonly=True, track_visibility='onchange')
    undeliverable_reason = fields.Selection([
        ('Project Transitioned', 'Project Transitioned'),
        ('Beneficiary Exited', 'Beneficiary Exited'),
        ('Beneficiary Exited More Than 90 Days Ago',
         'Beneficiary Exited More Than 90 Days Ago'),
    ], readonly=True, copy=False)
    threshold_alert = fields.Boolean(
        help='Partner exceeded the maximum gift amount allowed',
        readonly=True, copy=False)
    threshold_alert_type = fields.Char(readonly=True, copy=False)
    field_office_notes = fields.Char(readonly=True, copy=False)
    status_change_date = fields.Datetime(readonly=True)

    ##########################################################################
    #                             FIELDS METHODS                             #
    ##########################################################################
    @api.model
    def get_gift_type_selection(self):
        return [
            ('Project Gift', _('Project Gift')),
            ('Family Gift', _('Family Gift')),
            ('Beneficiary Gift', _('Beneficiary Gift')),
        ]

    @api.model
    def get_gift_attributions(self):
        return [
            ('Center Based Programming', 'CDSP'),
            ('Home Based Programming (Survival & Early Childhood)', 'CSP'),
            ('Sponsored Child Family', _('Sponsored Child Family')),
            ('Sponsorship', _('Sponsorship')),
            ('Survival', _('Survival')),
            ('Survival Neediest Families', _('Neediest Families')),
            ('Survival Neediest Families - Split', _(
                'Neediest Families Split')),
        ]

    @api.model
    def get_sponsorship_gifts(self):
        return [
            ('Birthday', _('Birthday')),
            ('General', _('General')),
            ('Graduation/Final', _('Graduation/Final')),
        ]

    @api.depends('invoice_line_ids')
    def _compute_invoice_fields(self):
        for gift in self.filtered('invoice_line_ids'):
            pay_dates = gift.invoice_line_ids.filtered('last_payment').mapped(
                'last_payment') or [gift.invoice_line_ids[0].last_payment]
            inv_dates = gift.invoice_line_ids.mapped('due_date')
            amounts = gift.mapped('invoice_line_ids.price_subtotal')
            gift.date_partner_paid = fields.Date.to_string(max(
                map(lambda d: fields.Date.from_string(d), pay_dates)))
            gift.gift_date = fields.Date.to_string(max(
                map(lambda d: fields.Date.from_string(d), inv_dates)))
            gift.amount = sum(amounts)

    def _compute_name(self):
        for gift in self:
            if gift.gift_type != 'Beneficiary Gift':
                name = gift.translate('gift_type')
            else:
                name = gift.translate('sponsorship_gift_type') + ' ' + _(
                    'Gift')
            name += ' [' + gift.sponsorship_id.name + ']'
            gift.name = name

    def _compute_usd(self):
        for gift in self:
            gift.currency_usd = self.env.ref('base.USD')

    ##########################################################################
    #                              ORM METHODS                               #
    ##########################################################################
    @api.model
    def create(self, vals):
        """ Try to find existing gifts before creating a new one. """
        gift = self.search([
            ('sponsorship_id', '=', vals['sponsorship_id']),
            ('gift_type', '=', vals['gift_type']),
            ('attribution', '=', vals['attribution']),
            ('sponsorship_gift_type', '=', vals.get('sponsorship_gift_type')),
            ('state', 'in', ['draft', 'verify', 'error'])
        ], limit=1)
        if gift:
            # Update gift invoice lines
            invl_write = list()
            for line_write in vals.get('invoice_line_ids', []):
                if line_write[0] == 6:
                    # Avoid replacing all line_ids => change (6, 0, ids) to
                    # [(4, id), (4, id), ...]
                    invl_write.extend([(4, id) for id in line_write[2]])
                else:
                    invl_write.append(line_write)
            if invl_write:
                gift.write({'invoice_line_ids': invl_write})

        else:
            # If a gift for the same partner is to verify, put as well
            # the new one to verify.
            partner_id = self.env['recurring.contract'].browse(
                vals['sponsorship_id']).partner_id.id
            gift_to_verify = self.search_count([
                ('partner_id', '=', partner_id),
                ('state', '=', 'verify')
            ])
            if gift_to_verify:
                vals['state'] = 'verify'
            gift = super(SponsorshipGift, self).create(vals)
            gift.invoice_line_ids.write({'gift_id': gift.id})
            gift._create_gift_message()

        return gift

    @api.multi
    def unlink(self):
        # Cancel gmc messages
        self.mapped('message_id').unlink()
        to_remove = self.filtered(lambda g: g.state != 'Undeliverable')
        for gift in to_remove:
            if gift.gmc_gift_id:
                raise Warning(
                    _("You cannot delete the %s."
                      "It is already sent to GMC.")
                    % gift.name
                )
        return super(SponsorshipGift, to_remove).unlink()

    ##########################################################################
    #                             PUBLIC METHODS                             #
    ##########################################################################
    @api.model
    def create_from_invoice_line(self, invoice_line):
        """
        Creates a sponsorship.gift record from an invoice_line
        :param invoice_line: account.invoice.line record
        :return: sponsorship.gift record
        """

        gift_vals = self.get_gift_values_from_product(invoice_line)
        if not gift_vals:
            return False

        gift = self.create(gift_vals)
        if not gift.is_eligible():
            gift.state = 'verify'
            gift.message_id.state = 'postponed'
        return gift

    @api.model
    def get_gift_values_from_product(self, invoice_line):
        """
        Converts a product into sponsorship.gift values
        :param: invoice_line: account.invoice.line record
        :return: dictionary of sponsorship.gift values
        """
        instructions = False
        product = invoice_line.product_id
        sponsorship = invoice_line.contract_id
        if not product.categ_name == GIFT_CATEGORY:
            return False

        if _(product.with_context(lang=invoice_line.create_uid.lang)
                .name).lower() not in invoice_line.name.lower():
            instructions = invoice_line.name

        gift_vals = self.get_gift_types(product)
        if gift_vals:
            gift_vals.update({
                'sponsorship_id': sponsorship.id,
                'invoice_line_ids': [(4, invoice_line.id)],
                'instructions': instructions,
            })

        return gift_vals

    @api.multi
    def is_eligible(self):
        """ Verifies the amount is within the thresholds and that the ICP
        is currently accepting gifts.
        """
        self.ensure_one()
        sponsorship = self.sponsorship_id
        if sponsorship.project_id.hold_gifts:
            return False

        threshold_rule = self.env['gift.threshold.settings'].search([
            ('gift_type', '=', self.gift_type),
            ('gift_attribution', '=', self.attribution),
            ('sponsorship_gift_type', '=', self.sponsorship_gift_type),
        ], limit=1)
        if threshold_rule:
            current_rate = threshold_rule.currency_id.rate_silent or 1.0
            minimum_amount = threshold_rule.min_amount
            maximum_amount = threshold_rule.max_amount

            this_amount = self.amount * current_rate
            if this_amount < minimum_amount or this_amount > maximum_amount:
                return False

            if threshold_rule.yearly_threshold:
                # search other gifts for the same sponsorship.
                # we will compare the date with the first january of the
                # current year
                next_year = fields.Date.to_string(
                    (date.today() + timedelta(days=365)).replace(month=1,
                                                                 day=1))
                firstJanuaryOfThisYear = fields.Date.today()[0:4] + '-01-01'

                other_gifts = self.search([
                    ('sponsorship_id', '=', sponsorship.id),
                    ('gift_type', '=', self.gift_type),
                    ('attribution', '=', self.attribution),
                    ('sponsorship_gift_type', '=', self.sponsorship_gift_type),
                    ('gift_date', '>=', firstJanuaryOfThisYear),
                    ('gift_date', '<', next_year),
                ])

                total_amount = this_amount
                if other_gifts:
                    total_amount += sum(other_gifts.mapped(
                        lambda gift: gift.amount_us_dollars or
                        gift.amount * current_rate))

                return total_amount < (maximum_amount *
                                       threshold_rule.gift_frequency)

        return True

    @api.model
    def get_gift_types(self, product):
        """ Given a product, returns the correct values
        of a gift for GMC.

        :return: dictionary of sponsorship.gift values
        """
        gift_type_vals = dict()
        product = product.with_context(lang='en_US')
        if product.name == GIFT_NAMES[0]:
            gift_type_vals.update({
                'gift_type': 'Beneficiary Gift',
                'attribution': 'Sponsorship',
                'sponsorship_gift_type': 'Birthday',
            })
        elif product.name == GIFT_NAMES[1]:
            gift_type_vals.update({
                'gift_type': 'Beneficiary Gift',
                'attribution': 'Sponsorship',
                'sponsorship_gift_type': 'General',
            })
        elif product.name == GIFT_NAMES[2]:
            gift_type_vals.update({
                'gift_type': 'Family Gift',
                'attribution': 'Sponsored Child Family',
            })
        elif product.name == GIFT_NAMES[3]:
            gift_type_vals.update({
                'gift_type': 'Project Gift',
                'attribution': 'Center Based Programming',
            })
        elif product.name == GIFT_NAMES[4]:
            gift_type_vals.update({
                'gift_type': 'Beneficiary Gift',
                'attribution': 'Sponsorship',
                'sponsorship_gift_type': 'Graduation/Final',
            })

        return gift_type_vals

    def on_send_to_connect(self):
        self.write({'state': 'open'})

    @api.multi
    def on_gift_sent(self, data):
        self.ensure_one()
        try:
            exchange_rate = float(data.get('exchange_rate'))
        except ValueError:
            exchange_rate = self.env.ref('base.USD').rate_silent or 1.0
        data.update({
            'state': 'In Progress',
            'amount_us_dollars': exchange_rate * self.amount
        })
        self.write(data)

    @api.model
    def process_commkit(self, commkit_data):
        """"
        This function is automatically executed when an Update Gift
        Message is received. It will convert the message from json to odoo
        format and then update the concerned records

        :param commkit_data contains the data of the message (json)
        :return list of gift ids which are concerned by the message
        """
        gift_update_mapping = CreateGiftMapping(self.env)

        # actually commkit_data is a dictionary with a single entry which
        # value is a list of dictionary (for each record)
        gifts_data = commkit_data['GiftUpdatesRequest'][
            'GiftUpdateRequestList']
        gift_ids = []
        changed_gifts = self
        # For each dictionary, we update the corresponding record
        for gift_data in gifts_data:
            vals = gift_update_mapping.get_vals_from_connect(gift_data)
            gift_id = vals['id']
            gift_ids.append(gift_id)
            gift = self.env['sponsorship.gift'].browse([gift_id])
            if vals.get('state', gift.state) != gift.state:
                changed_gifts += gift
            gift.write(vals)

        changed_gifts.filtered(lambda g: g.state == 'Delivered').\
            _gift_delivered()
        changed_gifts.filtered(lambda g: g.state == 'Undeliverable').\
            _gift_undeliverable()

        return gift_ids

    ##########################################################################
    #                             VIEW CALLBACKS                             #
    ##########################################################################
    @api.multi
    def view_invoices(self):
        return {
            'name': _("Invoices"),
            'domain': [('id', 'in', self.invoice_line_ids.mapped(
                'invoice_id').ids)],
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'target': 'current',
            'context': self.with_context({
                'form_view_ref': 'account.invoice_form',
            }).env.context
        }

    @api.multi
    def action_ok(self):
        self.write({'state': 'draft'})
        self.mapped('message_id').write({'state': 'new'})
        return True

    @api.multi
    def action_send(self):
        self.mapped('message_id').process_messages()
        return True

    @api.multi
    def action_verify(self):
        self.write({'state': 'verify'})
        self.mapped('message_id').write({'state': 'postponed'})
        return True

    @api.multi
    def action_cancel(self):
        """ Cancel Invoices and delete Gifts. """
        invoices = self.mapped('invoice_line_ids.invoice_id')
        self.env['account.move.line']._remove_move_reconcile(
            invoices.mapped('payment_ids.reconcile_id.line_id.id'))
        invoices.signal_workflow('invoice_cancel')
        self.mapped('message_id').unlink()
        return self.unlink()

    @api.onchange('gift_type')
    def onchange_gift_type(self):
        if self.gift_type == 'Beneficiary Gift':
            self.attribution = 'Sponsorship'
        elif self.gift_type == 'Family Gift':
            self.attribution = 'Sponsored Child Family'
            self.sponsorship_gift_type = False
        elif self.gift_type == 'Project Gift':
            self.attribution = 'Center Based Programming'
            self.sponsorship_gift_type = False

    @api.multi
    def mark_sent(self):
        self.mapped('message_id').unlink()
        return self.write({
            'state': 'Delivered',
            'status_change_date': fields.Datetime.now(),
        })

    ##########################################################################
    #                             PRIVATE METHODS                            #
    ##########################################################################
    @api.multi
    def _create_gift_message(self):
        # today = date.today()
        for gift in self:
            # message_center_compassion/models/gmc_messages
            message_obj = self.env['gmc.message.pool']

            action_id = self.env.ref(
                'gift_compassion.create_gift').id

            message_vals = {
                'action_id': action_id,
                'object_id': gift.id,
                'partner_id': gift.partner_id.id,
                'child_id': gift.child_id.id,
                'state': 'new' if gift.state != 'verify' else 'postponed',
            }
            gift.message_id = message_obj.create(message_vals)
            # TODO Activate auto processing after go-live
            # gift_date = fields.Date.from_string(gift.gift_date)
            # if gift.state == 'draft' and gift_date <= today:
            #     gift.message_id.process_messages()

    @api.multi
    def _gift_delivered(self):
        """
        Called when gifts delivered notification is received from GMC.
        Create a move record in the GMC Gift Due Account.
        :return:
        """
        account_credit = self.env.ref('gift_compassion.comp_2002_2')
        account_debit = self.env['account.account'].search([
            ('code', '=', '5003')])
        journal = self.env['account.journal'].search([
            ('code', '=', 'OD')])
        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'ref': 'Gift payment to GMC'
        })
        today = fields.Date.today()
        analytic = self.env.ref(
            'account_analytic_attribution.account_attribution_CD')
        mvl_obj = self.env['account.move.line']
        for gift in self:
            # Create the debit lines from the Gift Account
            if gift.invoice_line_ids:
                for invl in gift.invoice_line_ids:
                    mvl_obj.create({
                        'move_id': move.id,
                        'partner_id': invl.partner_id.id,
                        'account_id': account_debit.id,
                        'name': invl.name,
                        'debit': invl.price_subtotal,
                        'credit': 0.0,
                        'analytic_account_id': analytic.id,
                        'date_maturity': today,
                        'currency_id': gift.currency_usd.id,
                        'amount_currency': invl.price_subtotal *
                        gift.exchange_rate
                    })
            else:
                mvl_obj.create({
                    'move_id': move.id,
                    'partner_id': gift.partner_id.id,
                    'account_id': account_debit.id,
                    'name': gift.name,
                    'debit': gift.amount,
                    'analytic_account_id': analytic.id,
                    'date_maturity': today,
                    'currency_id': gift.currency_usd.id,
                    'amount_currency': gift.amount_us_dollars
                })

            # Create the credit line in the GMC Gift Due Account
            mvl_obj.create({
                'move_id': move.id,
                'partner_id': gift.partner_id.id,
                'account_id': account_credit.id,
                'name': gift.name,
                'date_maturity': today,
                'currency_id': gift.currency_usd.id,
                'amount_currency': gift.amount * gift.exchange_rate * -1
            })

        move.button_validate()
        self.write({'payment_id': move.id})

    @api.multi
    def _gift_undeliverable(self):
        """ Notify users defined in settings. """
        notify_ids = self.env['staff.notification.settings'].get_param(
            'gift_notify_ids')
        if notify_ids:
            for gift in self:
                partner = gift.partner_id
                child = gift.child_id
                values = {
                    'name': partner.name,
                    'ref': partner.ref,
                    'child_name': child.name,
                    'child_code': child.local_id,
                    'reason': gift.undeliverable_reason
                }
                body = (
                    "{name} ({ref}) made a gift to {child_name}"
                    " ({child_code}) which is undeliverable because {reason}."
                    "\nPlease inform the sponsor about it."
                ).format(**values)
                gift.message_post(
                    body=body,
                    subject="Gift Undeliverable Notification",
                    partner_ids=notify_ids,
                    type='comment',
                    subtype='mail.mt_comment',
                    content_subtype='plaintext'
                )
