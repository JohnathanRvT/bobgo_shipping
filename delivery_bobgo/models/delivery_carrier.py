from odoo import fields, models
from odoo.exceptions import UserError

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # Add 'bobgo' as a new provider option in the dropdown list.
    delivery_type = fields.Selection(
        selection_add=[('bobgo', 'Bobgo')],
        ondelete={'bobgo': 'set default'}
    )

    # Add a field to store the Bobgo API Key (Bearer Token).
    # This will be shown on the delivery method form.
    bobgo_api_key = fields.Char(
        string="Bobgo API Key",
        copy=False, # API keys should not be copied when duplicating records
        help="The Bearer Token for authenticating with the Bobgo API."
    )
    
    # --- PLACEHOLDER METHODS ---
    # These methods are required by Odoo for a delivery provider.
    # We will fill them with real API calls later.

    def bobgo_rate_shipment(self, order):
        """Gets shipping rates from the Bobgo API."""
        # TODO: Implement the actual API call to POST /rates
        return {
            'success': True,
            'price': 123.45,  # Dummy price for now
            'error_message': False,
            'warning_message': False,
        }

    def bobgo_send_shipping(self, pickings):
        """Books the shipment with the Bobgo API."""
        # TODO: Implement the actual API call to POST /shipments
        return [{
            'exact_price': 123.45,
            'tracking_number': 'DUMMY-BOBGO-12345',
        }]

    def bobgo_get_tracking_link(self, picking):
        """Returns the tracking link for a given shipment."""
        # The tracking_reference is stored in the 'carrier_tracking_ref' field
        tracking_ref = picking.carrier_tracking_ref
        return f"https://track.bobgo.co.za/results/{tracking_ref}"

    def bobgo_cancel_shipment(self, picking):
        """Cancels a shipment via the Bobgo API."""
        # TODO: Implement the actual API call to POST /shipments/cancel
        raise UserError("Shipment cancellation with Bobgo is not yet implemented.")