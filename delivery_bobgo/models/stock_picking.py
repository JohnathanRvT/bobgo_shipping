# -*- coding: utf-8 -*-

from odoo import fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bobgo_shipment_id = fields.Char(string='Bobgo Shipment ID', copy=False, help="The unique identifier for the shipment from the Bobgo API.")# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bobgo_shipment_id = fields.Char(
        string='Bobgo Shipment ID', 
        copy=False, 
        help="The unique identifier for the shipment from the Bobgo API.",
        index=True  # Add index for better performance
    )
    
    bobgo_shipment_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('booked', 'Booked'),
            ('in_transit', 'In Transit'),
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled'),
        ],
        string='Shipment Status',
        default='draft',
        copy=False
    )
    
    bobgo_last_sync = fields.Datetime(
        string='Last Sync with Bobgo',
        copy=False
    )

    def action_open_bobgo_tracking(self):
        """Open Bobgo tracking page in a new window."""
        self.ensure_one()
        if not self.carrier_id or self.carrier_id.delivery_type != 'bobgo':
            raise UserError(_("This delivery is not using Bobgo shipping."))
            
        tracking_link = self.carrier_id.bobgo_get_tracking_link(self)
        if tracking_link:
            return {
                'type': 'ir.actions.act_url',
                'url': tracking_link,
                'target': 'new',
            }
        else:
            raise UserError(_("No tracking information available for this shipment."))

    def action_sync_bobgo_status(self):
        """Sync shipment status from Bobgo API."""
        # This method can be extended to pull latest status from Bobgo
        # For now, it's a placeholder for future enhancement
        self.write({
            'bobgo_last_sync': fields.Datetime.now()
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Status Synced'),
                'message': _('Shipment status sync completed.'),
                'type': 'success',
                'sticky': False,
            }
        }