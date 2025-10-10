# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    """
    Inherit the product.product model to add dimension fields
    required for shipping calculations.
    """
    _inherit = 'product.product'

    length_cm = fields.Float(
        string='Length (cm)', 
        help="The length of the product in centimeters.", 
        default=10.0,
        digits=(10, 2)
    )
    width_cm = fields.Float(
        string='Width (cm)', 
        help="The width of the product in centimeters.", 
        default=10.0,
        digits=(10, 2)
    )
    height_cm = fields.Float(
        string='Height (cm)', 
        help="The height of the product in centimeters.", 
        default=10.0,
        digits=(10, 2)
    )

    @api.constrains('length_cm', 'width_cm', 'height_cm')
    def _check_dimensions(self):
        """Validate that dimensions are positive numbers."""
        for product in self:
            if product.length_cm < 0:
                raise ValidationError(_("Product length cannot be negative."))
            if product.width_cm < 0:
                raise ValidationError(_("Product width cannot be negative."))
            if product.height_cm < 0:
                raise ValidationError(_("Product height cannot be negative."))
            if product.length_cm == 0 and product.width_cm == 0 and product.height_cm == 0:
                raise ValidationError(_("Product dimensions cannot all be zero."))

    def get_shipping_volume(self):
        """Calculate shipping volume in cubic centimeters."""
        self.ensure_one()
        return self.length_cm * self.width_cm * self.height_cm