# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>, Philippe Heer
#
#    The licence is in the file __openerp__.py
#
##############################################################################
from openerp.addons.message_center_compassion.mappings.base_mapping import \
    OnrampMapping


class ICPLifecycleMapping(OnrampMapping):
    ODOO_MODEL = 'compassion.project.ile'
    MAPPING_NAME = "new_project_lifecyle"

    CONNECT_MAPPING = {
        "ActionPlanGPAUse": "action_plan",
        "ActualSuspensionEndDate": "suspension_end_date",
        "ActualTransitionDate": "date",
        "FutureInvolvement": ("future_involvement_ids.name",
                              "icp.involvement"),
        "ICPImprovementDescription": "icp_improvement_desc",
        "ICPLifecycleEventType": "type",
        "IsBeneficiaryInformationUpdatesWithheld":
            "is_beneficiary_information_updates_withheld",
        "IsBeneficiaryToSupporterLettersWithheld": "hold_b2s_letters",
        "IsGiftsWithheld": "hold_gifts",
        "IsSponsorshipFundsWithheld": "hold_cdsp_funds",
        "IsSuporterToBeneficiaryLettersWithheld": "hold_s2b_letters",
        "IsSurvivalFundsWithheld": "hold_csp_funds",
        "IsSuspensionExtendedAdditionalThirtyDays": "extension_2",
        "IsSuspensionExtendedThirtyDays": "extension_1",
        "IsTransitionComplete": "transition_complete",
        "Name": "name",
        "ProjectedTransitionDate": "projected_transition_date",
        "ReactivationDate": "reactivation_date",
        "ReasonForFirstExtension": "extension_1_reason",
        "ReasonforSecondExtension": "extension_2_reason",
        "SuspensionDetailsGPAUse": "suspension_detail",
        "SuspensionReason": ("suspension_reason_ids.name",
                             "icp.lifecycle.reason"),
        "SuspensionStartDate": "suspension_start_date",
        "TransitionDetailsGPAUse": "details",
        "TransitionReason": ("transition_reason_ids.name",
                             "icp.lifecycle.reason"),
        "TranslationStatus": "translation_status",
        "ICPStatus": "project_status",
        "ICP_ID": ('project_id.icp_id', 'compassion.project'),

        # Not used in Odoo
        'SourceKitName': None,
        "TranslationCompletedFields": None,
        "TranslationRequiredFields": None,
    }

    FIELDS_TO_SUBMIT = {
        'gpid': None,
    }

    CONSTANTS = {

    }
