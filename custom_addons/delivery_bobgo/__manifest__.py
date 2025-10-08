{
    'name': 'Bobgo Shipping Connector',
    'version': '19.0.1.0.0',
    'summary': 'Integrate Bobgo shipping services with Odoo',
    'description': """
        This module provides an integration with the Bobgo shipping aggregator,
        allowing users to fetch rates, book shipments, and track parcels
        directly from Odoo.
    """,
    'author': 'Your Name',  # Replace with your name or company
    'website': 'https://yourwebsite.com',  # Optional
    'category': 'Inventory/Delivery',
    'depends': [
        'delivery',  # Our module depends on the base 'delivery' module
    ],
    'data': [
        # XML files for the user interface are listed here.
        'views/delivery_carrier_views.xml',
    ],
    'installable': True,
    'application': True, # Set to True to make it easily searchable as an app
    'license': 'LGPL-3',
}