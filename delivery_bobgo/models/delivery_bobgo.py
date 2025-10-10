# -*- coding: utf-8 -*-
import json
import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from urllib.parse import urljoin
import time

_logger = logging.getLogger(__name__)

# Constants for better maintainability
BOBGO_API_TIMEOUT = 30
BOBGO_CACHE_DURATION = 300  # 5 minutes cache for rates

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('bobgo', 'Bobgo')],  # Fixed typo: 'Bob Go' -> 'Bobgo'
        ondelete={'bobgo': 'set default'}
    )
    bobgo_api_key = fields.Char(
        string='Bobgo API Key',
        required=True,
        help="API Key in format: Bearer your_token_here",
        groups="base.group_system"
    )
    bobgo_test_mode = fields.Boolean(
        string='Use Sandbox', 
        default=True,
        help="Use sandbox environment for testing"
    )
    bobgo_handling_time = fields.Integer(
        string='Handling Time (Days)', 
        default=1, 
        help="Handling time for the shipment in business days."
    )
    bobgo_last_connection_test = fields.Datetime(
        string='Last Connection Test'
    )
    bobgo_connection_status = fields.Boolean(
        string='Connection Status'
    )

    @api.constrains('bobgo_api_key')
    def _check_bobgo_api_key(self):
        """Validate API key format."""
        for carrier in self:
            if carrier.delivery_type == 'bobgo' and carrier.bobgo_api_key:
                if len(carrier.bobgo_api_key.strip()) < 20:
                    raise ValidationError(_("API Key seems too short. Please check your Bobgo API key."))

    @api.constrains('bobgo_handling_time')
    def _check_handling_time(self):
        """Validate handling time is reasonable."""
        for carrier in self:
            if carrier.delivery_type == 'bobgo' and carrier.bobgo_handling_time < 0:
                raise ValidationError(_("Handling time cannot be negative."))

    def bobgo_get_api_base_url(self):
        """Return the correct Bobgo API base URL."""
        self.ensure_one()
        if self.bobgo_test_mode:
            return "https://api.sandbox.bobgo.co.za/v2"
        return "https://api.bobgo.co.za/v2"

    def bobgo_validate_configuration(self):
        """Validate Bobgo configuration before making API calls."""
        self.ensure_one()
        
        if not self.bobgo_api_key:
            raise UserError(_("Bobgo API Key is not configured. Please set it in the delivery method configuration."))
        
        # Auto-format API key if needed
        if not self.bobgo_api_key.startswith('Bearer ') and len(self.bobgo_api_key.strip()) > 10:
            self.bobgo_api_key = f"Bearer {self.bobgo_api_key.strip()}"
            _logger.info("Auto-formatted API key with Bearer prefix for carrier %s", self.id)
        
        _logger.info("Bobgo configuration validated: Test Mode=%s, Handling Time=%s", 
                    self.bobgo_test_mode, self.bobgo_handling_time)
        return True

    def bobgo_test_connection(self):
        """Test connection to Bobgo API with comprehensive error handling."""
        self.ensure_one()
        
        try:
            self.bobgo_validate_configuration()
            
            test_payload = {
                "collection_address": {
                    "company": "Test Company",
                    "street_address": "125 Dallas Avenue",
                    "local_area": "Newlands",
                    "city": "Pretoria",
                    "zone": "GP",
                    "country": "ZA",
                    "code": "0181"
                },
                "delivery_address": {
                    "company": "Test Company",
                    "street_address": "125 Dallas Avenue", 
                    "local_area": "Newlands",
                    "city": "Pretoria",
                    "zone": "GP",
                    "country": "ZA",
                    "code": "0181"
                },
                "items": [
                    {
                        "description": "Test Product",
                        "price": 200,
                        "quantity": 1,
                        "length_cm": 17,
                        "width_cm": 8,
                        "height_cm": 5,
                        "weight_kg": 0.5
                    }
                ],
                "declared_value": 200,
                "handling_time": 1
            }
            
            base_url = self.bobgo_get_api_base_url()
            url = urljoin(base_url, "/rates-at-checkout")
            headers = {
                "Authorization": self.bobgo_api_key,
                "Content-Type": "application/json",
                "User-Agent": "Odoo-Bobgo-Connector/19.0"
            }
            
            _logger.info("Testing Bobgo API connection to: %s", url)
            
            start_time = time.time()
            response = requests.post(
                url, 
                headers=headers, 
                json=test_payload,  # Use json parameter for automatic serialization
                timeout=BOBGO_API_TIMEOUT
            )
            response_time = time.time() - start_time
            
            _logger.info("Connection test completed in %.2fs - Status: %s", response_time, response.status_code)
            
            if response.status_code == 200:
                # Update connection status
                self.write({
                    'bobgo_last_connection_test': fields.Datetime.now(),
                    'bobgo_connection_status': True
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Connection Successful"),
                        'message': _("Bobgo API connection test passed successfully! Response time: %.2fs") % response_time,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                self.write({
                    'bobgo_last_connection_test': fields.Datetime.now(),
                    'bobgo_connection_status': False
                })
                error_detail = self._extract_error_detail(response)
                _logger.error("Connection test failed: %s", error_detail)
                raise UserError(_("Connection test failed (HTTP %s): %s") % (response.status_code, error_detail))
                
        except requests.exceptions.Timeout:
            self.write({
                'bobgo_last_connection_test': fields.Datetime.now(),
                'bobgo_connection_status': False
            })
            _logger.error("Bobgo connection test timed out after %s seconds", BOBGO_API_TIMEOUT)
            raise UserError(_("Connection test timed out after %s seconds. Please try again.") % BOBGO_API_TIMEOUT)
        except Exception as e:
            self.write({
                'bobgo_last_connection_test': fields.Datetime.now(),
                'bobgo_connection_status': False
            })
            _logger.exception("Bobgo connection test failed with unexpected error")
            raise UserError(_("Connection test failed: %s") % str(e))

    def rate_shipment(self, order):
        """Odoo standard entry point to get rates for a sales order."""
        self.ensure_one()

        if self.delivery_type != 'bobgo':
            return super(DeliveryCarrier, self).rate_shipment(order)

        _logger.info("Starting Bobgo rate shipment for order: %s", order.name)
        
        try:
            self.bobgo_validate_configuration()
            
            # Check cache first
            cache_key = f"bobgo_rates_{order.id}_{self.id}"
            cached_rates = self.env.cache.get(cache_key)
            if cached_rates:
                _logger.info("Using cached rates for order %s", order.name)
                return cached_rates
            
            response = self.bobgo_rate_shipment(order)
            
            # Cache the response
            self.env.cache.set(cache_key, response, BOBGO_CACHE_DURATION)
            
            _logger.info("Successfully completed Bobgo rate shipment for order: %s", order.name)
            return response
            
        except UserError:
            raise
        except Exception as e:
            _logger.exception("Unexpected error in Bobgo rating for order %s", order.name)
            return {
                'success': False,
                'price': 0.0,
                'error_message': _("Unexpected error while fetching shipping rates. Please try again."),
                'warning_message': False,
            }

    def bobgo_rate_shipment(self, order):
        """Get Bobgo checkout rates for the given sale order."""
        self.ensure_one()

        _logger.info("Processing Bobgo rate request for order ID: %s", order.id)

        # Validate order data
        if not order.order_line:
            raise UserError(_("Cannot calculate shipping for empty order."))

        # Build addresses with validation
        collection = self._prepare_collection_address(order)
        delivery = self._prepare_delivery_address(order)

        _logger.debug("Collection address: %s", collection)
        _logger.debug("Delivery address: %s", delivery)

        # Prepare items with validation
        items, declared_value = self._prepare_order_items(order)
        
        if not items:
            raise UserError(_("No shippable items found in the order."))

        payload = {
            "collection_address": collection,
            "delivery_address": delivery,
            "items": items,
            "declared_value": declared_value,
            "handling_time": max(0, int(self.bobgo_handling_time)),
        }

        base_url = self.bobgo_get_api_base_url()
        url = urljoin(base_url, "/rates-at-checkout")
        headers = {
            "Authorization": self.bobgo_api_key,
            "Content-Type": "application/json",
            "User-Agent": "Odoo-Bobgo-Connector/19.0"
        }

        _logger.info("=== BOBGO API REQUEST ===")
        _logger.info("URL: %s", url)
        _logger.info("Request Payload: %s", json.dumps(payload, indent=2))

        try:
            start_time = time.time()
            response = requests.post(url, headers=headers, json=payload, timeout=BOBGO_API_TIMEOUT)
            response_time = time.time() - start_time
            
            _logger.info("=== BOBGO API RESPONSE ===")
            _logger.info("Status Code: %s", response.status_code)
            _logger.info("Response Time: %.2fs", response_time)
            _logger.debug("Response Body: %s", response.text)

            response.raise_for_status()
            
            data = response.json()
            _logger.info("Successfully parsed API response with %d rates", len(data.get("rates", [])))

            if not data.get("rates"):
                _logger.warning("No rates found in API response")
                raise UserError(_("No shipping rates available for the given addresses. Please check the addresses or try again later."))

            rates = data["rates"]
            _logger.info("Found %d available rates", len(rates))
            
            # Create wizard for rate selection
            return self._create_rate_selection_wizard(order, rates)

        except requests.exceptions.Timeout:
            _logger.error("Bobgo API request timed out after %s seconds", BOBGO_API_TIMEOUT)
            raise UserError(_("Shipping rate request timed out. Please try again."))
        except requests.exceptions.ConnectionError:
            _logger.error("Connection error to Bobgo API")
            raise UserError(_("Cannot connect to Bobgo API. Please check your internet connection and try again."))
        except requests.exceptions.HTTPError as e:
            error_detail = self._extract_error_detail(e.response)
            _logger.error("Bobgo API HTTP error: %s", error_detail)
            raise UserError(self._format_http_error(e.response.status_code, error_detail))
        except requests.exceptions.RequestException as e:
            _logger.error("Bobgo API request failed: %s", e)
            raise UserError(_("Bobgo API connection failed: %s") % str(e))
        except ValueError as e:
            _logger.error("Failed to parse Bobgo API response: %s", e)
            raise UserError(_("Invalid response from Bobgo API. Please try again."))

    def _prepare_collection_address(self, order):
        """Prepare collection address with validation."""
        warehouse_partner = order.warehouse_id.partner_id
        if not warehouse_partner:
            raise UserError(_("No warehouse configured for this order."))
        
        return {
            "company": warehouse_partner.name or "Warehouse",
            "street_address": warehouse_partner.street or "",
            "local_area": warehouse_partner.street2 or "",
            "city": warehouse_partner.city or "",
            "zone": warehouse_partner.state_id.code or "",
            "country": warehouse_partner.country_id.code or "ZA",
            "code": warehouse_partner.zip or "",
        }

    def _prepare_delivery_address(self, order):
        """Prepare delivery address with validation."""
        shipping_partner = order.partner_shipping_id
        if not shipping_partner:
            raise UserError(_("No shipping address configured for this order."))
        
        return {
            "company": shipping_partner.name or "",
            "street_address": shipping_partner.street or "",
            "local_area": shipping_partner.street2 or "",
            "city": shipping_partner.city or "",
            "zone": shipping_partner.state_id.code or "",
            "country": shipping_partner.country_id.code or "ZA",
            "code": shipping_partner.zip or "",
        }

    def _prepare_order_items(self, order):
        """Prepare order items for shipping calculation."""
        items = []
        declared_value = 0.0
        
        for line in order.order_line.filtered(lambda l: not l.is_delivery and l.product_id):
            product = line.product_id
            
            # Use safe conversion with validation
            length_cm = self._safe_float(product.length_cm, 10.0, "length_cm")
            width_cm = self._safe_float(product.width_cm, 10.0, "width_cm") 
            height_cm = self._safe_float(product.height_cm, 10.0, "height_cm")
            weight_kg = self._safe_float(product.weight, 0.2, "weight")
            price = self._safe_float(line.price_unit, 0.0, "price")
            quantity = self._safe_float(line.product_uom_qty, 1.0, "quantity")
            
            item_data = {
                "description": (product.display_name or "Product")[:100],  # Limit length
                "price": price,
                "quantity": max(1, int(quantity)),
                "length_cm": max(0.1, length_cm),
                "width_cm": max(0.1, width_cm),
                "height_cm": max(0.1, height_cm),
                "weight_kg": max(0.01, weight_kg),
            }
            
            items.append(item_data)
            declared_value += float(price * quantity)
            
            _logger.debug("Added item: %s", item_data)

        return items, declared_value

    def _create_rate_selection_wizard(self, order, rates):
        """Create wizard for rate selection."""
        wizard = self.env["choose.bobgo.rate"].create({
            "order_id": order.id,
            "carrier_id": self.id,
            "line_ids": [
                (0, 0, {
                    "service_name": r.get("service_name", "Unknown Service"),
                    "description": r.get("description", ""),
                    "total_price": float(r.get("total_price", 0.0)),
                    "delivery_date_min": r.get("min_delivery_date"),
                    "delivery_date_max": r.get("max_delivery_date"),
                    "service_code": r.get("service_code"),
                    "provider_slug": r.get("provider_slug"),
                    "currency_id": self.env.ref("base.ZAR").id,
                })
                for r in rates
            ]
        })

        _logger.info("Created rate selection wizard with ID: %s", wizard.id)

        return {
            "type": "ir.actions.act_window",
            "name": _("Choose a Shipping Rate"),
            "res_model": "choose.bobgo.rate",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "context": self.env.context,
        }

    def _safe_float(self, value, default, field_name=""):
        """Safely convert value to float with validation and logging."""
        try:
            if value is None:
                return default
            result = float(value)
            if result <= 0:
                _logger.warning("Invalid %s value: %s, using default: %s", field_name, value, default)
                return default
            return result
        except (TypeError, ValueError):
            _logger.warning("Cannot convert %s value '%s' to float, using default: %s", field_name, value, default)
            return default

    def _extract_error_detail(self, response):
        """Extract error details from API response safely."""
        try:
            error_data = response.json()
            for field in ['detail', 'error', 'message', 'description']:
                if field in error_data:
                    return str(error_data[field])
            return str(error_data)
        except (ValueError, AttributeError):
            return response.text or "No error details available"

    def _format_http_error(self, status_code, error_detail):
        """Format user-friendly error messages based on HTTP status."""
        error_messages = {
            400: _("Bad request to Bobgo API: %s"),
            401: _("Authentication failed. Please check your Bobgo API key."),
            403: _("Access forbidden. Your API key may not have the required permissions."),
            429: _("Rate limit exceeded. Please try again later."),
            500: _("Bobgo API server error. Please try again later."),
            502: _("Bobgo API is temporarily unavailable. Please try again later."),
            503: _("Bobgo API service is temporarily overloaded. Please try again later."),
        }
        
        return error_messages.get(status_code, _("Bobgo API returned error (HTTP %s): %s")) % (status_code, error_detail)

    def bobgo_send_shipping(self, pickings):
        """Book shipments through Bobgo API with comprehensive error handling."""
        res = []
        _logger.info("Starting Bobgo shipment booking for %d pickings", len(pickings))
        
        for picking in pickings:
            try:
                _logger.info("Processing picking: %s", picking.name)
                
                self.bobgo_validate_configuration()
                
                # Get shipment rates
                rate_payload = self._prepare_shipment_rate_payload(picking)
                base_url = self.bobgo_get_api_base_url()
                rate_url = urljoin(base_url, "/rates")
                
                headers = {
                    "Authorization": self.bobgo_api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "Odoo-Bobgo-Connector/19.0"
                }
                
                _logger.info("Getting shipment rates for picking %s", picking.name)
                rate_response = requests.post(rate_url, headers=headers, json=rate_payload, timeout=BOBGO_API_TIMEOUT)
                rate_response.raise_for_status()
                
                rates_data = rate_response.json()
                _logger.info("Received %d shipment rates", len(rates_data.get('rates', [])))
                
                if not rates_data.get('rates'):
                    raise UserError(_("No shipment rates available for this delivery."))
                
                # Use the first rate (could be enhanced to let user choose)
                selected_rate = rates_data['rates'][0]
                _logger.info("Selected rate: %s (%s)", selected_rate.get('service_name'), selected_rate.get('total_price'))
                
                # Create shipment
                shipment_payload = self._prepare_shipment_payload(picking, selected_rate)
                shipment_url = urljoin(base_url, "/shipments")
                
                _logger.info("Creating shipment for picking %s", picking.name)
                shipment_response = requests.post(shipment_url, headers=headers, json=shipment_payload, timeout=BOBGO_API_TIMEOUT)
                shipment_response.raise_for_status()
                
                shipment_data = shipment_response.json()
                tracking_reference = shipment_data.get('tracking_reference')
                _logger.info("Shipment created successfully: %s", shipment_data.get('id'))
                
                # Update picking with shipment information
                picking.write({
                    'bobgo_shipment_id': shipment_data.get('id'),
                    'carrier_tracking_ref': tracking_reference,
                })
                
                # Prepare result for Odoo
                res.append({
                    'exact_price': float(selected_rate.get('total_price', 0.0)),
                    'tracking_number': tracking_reference,
                })
                
                _logger.info("Successfully booked shipment for picking %s with tracking: %s", 
                            picking.name, tracking_reference)
                
            except Exception as e:
                _logger.exception("Bobgo shipment booking failed for picking %s", picking.name)
                raise UserError(_("Failed to book shipment for %s: %s") % (picking.name, str(e)))
        
        return res

    def _prepare_shipment_rate_payload(self, picking):
        """Prepare payload for shipment rate request with validation."""
        # Collection address from warehouse
        warehouse_partner = picking.picking_type_id.warehouse_id.partner_id
        if not warehouse_partner:
            raise UserError(_("No warehouse partner configured for this picking."))
            
        collection = {
            "company": warehouse_partner.name or "Warehouse",
            "street_address": warehouse_partner.street or "",
            "local_area": warehouse_partner.street2 or "",
            "city": warehouse_partner.city or "",
            "zone": warehouse_partner.state_id.code or "",
            "country": warehouse_partner.country_id.code or "ZA",
            "code": warehouse_partner.zip or "",
        }

        # Delivery address
        if not picking.partner_id:
            raise UserError(_("No delivery partner configured for this picking."))
            
        delivery = {
            "company": picking.partner_id.name or "",
            "street_address": picking.partner_id.street or "",
            "local_area": picking.partner_id.street2 or "",
            "city": picking.partner_id.city or "",
            "zone": picking.partner_id.state_id.code or "",
            "country": picking.partner_id.country_id.code or "ZA",
            "code": picking.partner_id.zip or "",
        }

        # Prepare parcels
        parcels = []
        for move in picking.move_ids.filtered(lambda m: m.product_id):
            product = move.product_id
            parcels.append({
                "description": product.display_name[:100],
                "submitted_length_cm": product.length_cm or 10,
                "submitted_width_cm": product.width_cm or 10,
                "submitted_height_cm": product.height_cm or 10,
                "submitted_weight_kg": product.weight or 0.2,
            })

        if not parcels:
            parcels.append({
                "description": "Default Package",
                "submitted_length_cm": 10,
                "submitted_width_cm": 10,
                "submitted_height_cm": 10,
                "submitted_weight_kg": 0.2,
            })

        # Get contact information
        collection_contact = self._get_collection_contact(picking)
        delivery_contact = self._get_delivery_contact(picking)

        return {
            "collection_address": collection,
            "delivery_address": delivery,
            "parcels": parcels,
            "declared_value": sum(move.sale_line_id.price_total for move in picking.move_ids if move.sale_line_id) or 0,
            "collection_contact_mobile_number": collection_contact.get('phone'),
            "collection_contact_email": collection_contact.get('email'),
            "collection_contact_full_name": collection_contact.get('name'),
            "delivery_contact_mobile_number": delivery_contact.get('phone'),
            "delivery_contact_email": delivery_contact.get('email'),
            "delivery_contact_full_name": delivery_contact.get('name'),
            "timeout": 10000,
        }

    def _prepare_shipment_payload(self, picking, rate):
        """Prepare payload for shipment creation."""
        # Reuse the same address preparation as rates
        rate_payload = self._prepare_shipment_rate_payload(picking)
        
        # Add rate-specific information
        shipment_payload = {
            "collection_address": rate_payload["collection_address"],
            "collection_contact_name": rate_payload["collection_contact_full_name"],
            "collection_contact_mobile_number": rate_payload["collection_contact_mobile_number"],
            "collection_contact_email": rate_payload["collection_contact_email"],
            "delivery_address": rate_payload["delivery_address"],
            "delivery_contact_name": rate_payload["delivery_contact_full_name"],
            "delivery_contact_mobile_number": rate_payload["delivery_contact_mobile_number"],
            "delivery_contact_email": rate_payload["delivery_contact_email"],
            "parcels": rate_payload["parcels"],
            "declared_value": rate_payload["declared_value"],
            "timeout": 20000,
            "service_level_code": rate.get('service_level_code'),
            "provider_slug": rate.get('provider_slug'),
        }
        
        return shipment_payload

    def _get_collection_contact(self, picking):
        """Get collection contact information from warehouse partner."""
        partner = picking.picking_type_id.warehouse_id.partner_id
        return {
            'name': partner.name or '',
            'phone': partner.mobile or partner.phone or '',
            'email': partner.email or '',
        }

    def _get_delivery_contact(self, picking):
        """Get delivery contact information from destination partner."""
        partner = picking.partner_id
        return {
            'name': partner.name or '',
            'phone': partner.mobile or partner.phone or '',
            'email': partner.email or '',
        }

    def bobgo_cancel_shipment(self, pickings):
        """Cancel shipments through Bobgo API with proper error handling."""
        _logger.info("Cancelling %d Bobgo shipments", len(pickings))
        
        successful_cancellations = []
        failed_cancellations = []
        
        for picking in pickings:
            if not picking.carrier_tracking_ref:
                _logger.warning("No tracking reference found for picking %s", picking.name)
                failed_cancellations.append(picking.name)
                continue
                
            try:
                _logger.info("Cancelling shipment with tracking: %s", picking.carrier_tracking_ref)
                
                base_url = self.bobgo_get_api_base_url()
                url = urljoin(base_url, "/shipments/cancel")
                headers = {
                    "Authorization": self.bobgo_api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "Odoo-Bobgo-Connector/19.0"
                }
                
                payload = {
                    "tracking_reference": picking.carrier_tracking_ref
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=BOBGO_API_TIMEOUT)
                
                if response.status_code == 200:
                    # Clear tracking reference if cancellation successful
                    picking.write({
                        'carrier_tracking_ref': False,
                        'bobgo_shipment_id': False,
                    })
                    successful_cancellations.append(picking.name)
                    _logger.info("Successfully cancelled shipment: %s", picking.carrier_tracking_ref)
                else:
                    _logger.warning("Failed to cancel shipment %s: %s", picking.carrier_tracking_ref, response.text)
                    failed_cancellations.append(picking.name)
                    
            except Exception as e:
                _logger.exception("Failed to cancel Bobgo shipment %s", picking.carrier_tracking_ref)
                failed_cancellations.append(picking.name)
        
        # Log summary
        if successful_cancellations:
            _logger.info("Successfully cancelled %d shipments", len(successful_cancellations))
        if failed_cancellations:
            _logger.warning("Failed to cancel %d shipments", len(failed_cancellations))
            
        return len(failed_cancellations) == 0

    def bobgo_get_tracking_link(self, picking):
        """Return Bobgo tracking link with validation."""
        if picking.carrier_tracking_ref:
            base_url = "sandbox.bobgo.co.za" if self.bobgo_test_mode else "bobgo.co.za"
            tracking_link = f"https://{base_url}/tracking/{picking.carrier_tracking_ref}"
            _logger.debug("Generated tracking link: %s", tracking_link)
            return tracking_link
        _logger.warning("No tracking reference available for picking %s", picking.name)
        return False

    @api.model
    def _init_bobgo_defaults(self):
        """Initialize default values for Bobgo carriers."""
        _logger.info("Initializing Bobgo shipping connector defaults")