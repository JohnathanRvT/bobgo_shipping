{
    'name': 'Bobgo Shipping Connector',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Delivery, Third Party Integrations',
    'summary': 'Integrate Bobgo shipping for rates, booking, and tracking.',
    'description': """
This module provides a seamless integration with the Bobgo shipping aggregator, empowering Odoo users with the following capabilities:

- **Real-time Rate Fetching:** Instantly get shipping quotes from a variety of carriers supported by Bobgo directly within your Odoo sales orders and delivery orders.
- **Effortless Shipment Booking:** Book shipments and generate professional shipping labels without leaving the Odoo interface.
- **Live Parcel Tracking:** Keep your customers informed with real-time tracking updates for all your shipments.
- **Simplified Logistics:** Streamline your entire shipping process from a single platform.

This connector is designed to save you time and money by automating your shipping workflow and providing access to competitive shipping rates.
    """,
    'website': 'https://jrvt.co.za',
    'author': 'JRVT (Pty) Ltd',
    'maintainer': 'JRVT (Pty) Ltd',
    'license': 'LGPL-3',
    'support': 'info@jrvt.co.za',
    'live_test_url': 'https://odoo.jrvt.co.za/web/login',
    'depends': [
        'delivery', # Base module for delivery carrier integration
    ],
    'data': [
        'views/delivery_carrier_views.xml',
    ],
    'installable': True,
    'application': True,
    'images': [
        'static/description/banner.gif',
        'static/description/bobgo_hero.png',
        'static/description/bobgo_tracking_ref.png',
        'static/description/bobgo_waybill.png',
        'static/description/bobgo_customer_portal.png',
    ],
}