##############################################################################
#
#    Copyright (C) 2019 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Jonathan Tarabbia
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging
from datetime import datetime

from odoo import _, api, fields, models

logger = logging.getLogger(__name__)


class MobileFeedback(models.Model):
    _name = "mobile.app.feedback"
    _inherit = "mail.activity.mixin"
    _description = "Mobile App Feedback"
    _order = "id desc"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    name = fields.Char("What did you like", readonly=True)
    partner_id = fields.Many2one("res.partner", "Partner", readonly=True)
    language = fields.Selection("_get_lang")
    improve_app = fields.Char("How can we improve the app", readonly=True)
    source = fields.Selection([("Android", "Android"), ("iOS", "iOS")], readonly=True)
    star = fields.Selection(
        [
            ("0.0", "None"),
            ("1.0", "Disappointing"),
            ("2.0", "Well"),
            ("3.0", "Very well"),
            ("4.0", "Great"),
            ("5.0", "Extraordinary"),
        ],
        readonly=True,
    )
    create_date = fields.Datetime(
        string="Creation Date",
        readonly=True,
        default=datetime.today(),
    )
    state = fields.Selection(
        [
            ("unread", "Unread"),
            ("read", "Read"),
            ("replied", "Replied"),
        ],
        default="unread",
    )
    crm_claim_id = fields.Many2one("crm.claim", "Answer to feedback", readonly=False)

    @api.model
    def _get_lang(self):
        langs = self.env["res.lang"].search([])
        return [(lang.code, lang.name) for lang in langs]

    def mobile_feedback(self, data=None, **parameters):
        star = str(float(parameters.get("star", 3.0)))
        what_did_u_like = parameters.get("Whatdidulike", "")
        # source parameter is not defined in ios application
        source = parameters.get("source", "iOS")
        improve_app = parameters.get("Improveapp", "")
        record = self.create(
            {
                "name": what_did_u_like,
                "partner_id": self.env.user.partner_id.id,
                "source": source,
                "improve_app": improve_app,
                "star": star,
            }
        )
        if "lang" in self.env.context:
            record["language"] = self.env.context["lang"]

        return record.id

    def mark_read(self):
        return self.write({"state": "read"})

    def create_crm_claim(self):
        self.ensure_one()
        return self.with_context(lang=self.language)._create_claim()

    def _create_claim(self):
        def html_paragraph(text):
            return f"<p>{text}</p>"

        def html_bold(text):
            return f"<p><b>{text}</b></p>"

        body = html_bold(_("Your feedback from the app"))
        if self.name:
            body += html_bold(_("What did you like") + "?")
            body += html_paragraph(self.name)
        if self.improve_app:
            body += html_bold(_("How can we improve the app") + "?")
            body += html_paragraph(self.improve_app)

        partner = self.partner_id
        claim = self.env["crm.claim"].create(
            {
                "email_from": self.partner_id.email,
                "subject": _("Mobile App Feedback"),
                "name": body,
                "categ_id": self.env["crm.claim.category"]
                .search([("name", "=", self.source)])
                .id,
                "claim_category": self.env.ref(
                    "mobile_app_connector.claim_cat_feedback"
                ).id,
                "partner_id": partner.id,
                "language": self.language,
                "date": self.create_date,
                "description": body,
            }
        )
        claim.message_post(
            body=body, subject=_("Your Mobile App Feedback"), author_id=partner.id
        )

        self.state = "replied"
        self.crm_claim_id = claim

        return {
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "crm.claim",
            "target": "current",
            "res_id": claim.id,
        }

    @api.model
    def _needaction_domain_get(self):
        """
        Used to display a count icon in the menu
        :return: domain of jobs counted
        """
        return [("state", "=", "unread")]
