from odoo import models
from odoo.tools.mail import html2plaintext


class PartnerCommunication(models.Model):
    _inherit = ["partner.communication.job", "interaction.source"]
    _name = "partner.communication.job"

    COMMUNICATION_TYPE_MAPPING = {
        "digital": "Email",
        "physical": "Paper",
        "sms": "SMS",
    }

    def _get_interaction_partner_domain(self, partner):
        domain = super()._get_interaction_partner_domain(partner)
        return domain + [("state", "=", "done")]

    def _get_interaction_data(self, partner_id):
        default_comm = self.env.ref("partner_communication.default_communication")
        return [
            {
                "partner_id": partner_id,
                "res_model": self._name,
                "res_id": rec.id,
                "direction": "out",
                "date": rec.sent_date,
                "email": rec.partner_id.email,
                "communication_type": self.COMMUNICATION_TYPE_MAPPING.get(
                    rec.send_mode, "Other"
                ),
                "subject": rec.config_id.name
                if rec.config_id != default_comm or not rec.subject
                else rec.subject,
                "body": html2plaintext(rec.body_html).replace("\n\n", "\n"),
                "has_attachment": bool(rec.attachment_ids),
                "tracking_status": rec.email_id.mail_tracking_ids[:1].state or "sent",
            }
            for rec in self
        ]

    def send(self):
        res = super().send()
        # Refresh the interactions after sending the communication
        self.mapped("partner_id").with_delay().fetch_interactions()
        return res
