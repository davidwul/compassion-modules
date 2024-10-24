import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class CommunicationConfig(models.Model):
    _inherit = "partner.communication.config"

    mobile_notification_send = fields.Boolean("Send mobile notification", default=False)

    mobile_notification_auto_send = fields.Boolean("Auto send", default=False)

    mobile_notification_title = fields.Text("Title", translate=True)

    mobile_notification_body = fields.Text("Body", translate=True)

    mobile_notification_destination = fields.Selection(
        [
            ("MyHub", "My Hub"),
            ("Letter", "Letter"),
            ("Donation", "Donation"),
            ("Prayer", "Prayer"),
        ],
        "Destination",
        default="MyHub",
    )

    mobile_notification_topic = fields.Selection(
        [
            ("general_notification", "General channel"),
            ("child_notification", "Child channel"),
            ("spam", "None (bypass user's preferences)"),
        ],
        "Topic",
        default="general_notification",
    )
