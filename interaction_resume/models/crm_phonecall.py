from odoo import models

TRACKING_STATUS_MAPPING = {
    "open": "sent",
    "cancel": "canceled",
    "pending": "outgoing",
    "done": "delivered",
}


class CrmPhonecall(models.Model):
    _inherit = ["crm.phonecall", "interaction.source"]
    _name = "crm.phonecall"

    def _get_interaction_partner_domain(self, partner):
        domain = super()._get_interaction_partner_domain(partner)
        return domain + [("state", "=", "done")]

    def _get_interaction_data(self, partner_id):
        direction_mapping = {"inbound": "in", "outbound": "out"}
        return [
            {
                "partner_id": partner_id,
                "res_model": self._name,
                "res_id": rec.id,
                "direction": direction_mapping.get(rec.direction, rec.direction),
                "date": rec.date,
                "communication_type": "Phone",
                "subject": rec.name,
                "body": rec.description or rec.name,
                "tracking_status": TRACKING_STATUS_MAPPING.get(rec.state),
            }
            for rec in self
        ]
