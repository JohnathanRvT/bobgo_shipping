# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class ChooseBobgoRate(models.TransientModel):
    _name = 'choose.bobgo.rate'
    _description = 'Choose a Bobgo Shipping Rate'

    order_id = fields.Many2one(
        'sale.order', 
        string="Sales Order", 
        required=True, 
        readonly=True,
        ondelete='cascade'
    )
    carrier_id = fields.Many2one(
        'delivery.carrier', 
        string="Carrier", 
        required=True, 
        readonly=True,
        ondelete='cascade'
    )
    line_ids = fields.One2many(
        'choose.bobgo.rate.line', 
        'wizard_id', 
        string="Available Rates"
    )
    
    @api.constrains('line_ids')
    def _check_has_rates(self):
        """Ensure there are rates to choose from."""
        for wizard in self:
            if not wizard.line_ids:
                raise ValidationError(_("No shipping rates available to choose from."))

class ChooseBobgoRateLine(models.TransientModel):
    _name = 'choose.bobgo.rate.line'
    _description = 'Line item for a Bobgo Shipping Rate'
    _order = 'total_price asc'  # Sort by price ascending

    wizard_id = fields.Many2one(
        'choose.bobgo.rate', 
        string="Wizard", 
        required=True, 
        ondelete='cascade',
        readonly=True
    )
    service_name = fields.Char(
        string="Service",
        required=True,
        readonly=True
    )
    service_code = fields.Char(
        string="Service Code",
        readonly=True
    )
    provider_slug = fields.Char(
        string="Provider Code",
        readonly=True
    )
    total_price = fields.Float(
        string="Price",
        required=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.order_id.currency_id',
        readonly=True
    )
    delivery_date_min = fields.Char(
        string="Est. Delivery (Min)",
        readonly=True
    )
    delivery_date_max = fields.Char(
        string="Est. Delivery (Max)", 
        readonly=True
    )
    description = fields.Char(
        string="Description",
        readonly=True,
        help="Additional details about the shipping service"
    )

    def action_apply_rate(self):
        """Apply the selected shipping rate to the sales order."""
        self.ensure_one()
        wizard = self.wizard_id
        
        if not wizard.order_id or not wizard.carrier_id:
            raise UserError(_("Invalid rate selection data."))
        
        try:
            # Set delivery line using Odoo's standard method
            success = wizard.order_id.set_delivery_line(wizard.carrier_id, self.total_price)
            
            if not success:
                raise UserError(_("Failed to apply shipping rate to the order."))
            
            # Update delivery line description to be more specific
            delivery_line = wizard.order_id.order_line.filtered(lambda l: l.is_delivery)
            if delivery_line:
                service_description = f"{wizard.carrier_id.name}"
                if self.service_name and self.service_name != "Unknown Service":
                    service_description += f" - {self.service_name}"
                
                delivery_line.write({
                    'name': service_description,
                    'price_unit': self.total_price,
                })
                
            # Log the rate selection
            self.env['ir.logging'].create({
                'name': 'Bobgo Rate Selected',
                'type': 'server',
                'dbname': self.env.cr.dbname,
                'level': 'INFO',
                'message': f"Selected Bobgo rate for order {wizard.order_id.name}: {self.service_name} - {self.total_price}",
                'path': 'bobgo_shipping',
                'func': 'action_apply_rate',
                'line': 1,
            })
            
            return {'type': 'ir.actions.act_window_close'}
            
        except Exception as e:
            raise UserError(_("Error applying shipping rate: %s") % str(e))

    def action_view_service_details(self):
        """Display detailed information about the selected service."""
        self.ensure_one()
        
        message = f"""
        <b>Service Details:</b><br/>
        <b>Service:</b> {self.service_name or 'N/A'}<br/>
        <b>Description:</b> {self.description or 'N/A'}<br/>
        <b>Price:</b> {self.total_price} {self.currency_id.symbol or ''}<br/>
        <b>Estimated Delivery:</b> {self.delivery_date_min or 'N/A'} to {self.delivery_date_max or 'N/A'}<br/>
        <b>Provider:</b> {self.provider_slug or 'N/A'}<br/>
        """
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Service Details'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }