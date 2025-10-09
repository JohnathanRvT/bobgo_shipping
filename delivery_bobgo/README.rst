==========================
Bobgo Odoo Shipping Connector
==========================

.. image:: https://img.shields.io/badge/license-LGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

.. image:: https://img.shields.io/badge/author-JRVT%20(Pty)%20Ltd-lightgray.svg
    :target: https://jrvt.co.za
    :alt: Author: JRVT (Pty) Ltd

This module integrates the Bobgo shipping aggregator service with Odoo 19, allowing for a streamlined shipping and fulfillment process directly within the Odoo environment.

Key Features
============

*   **Real-Time Rate Fetching:** Get live shipping quotes from multiple South African carriers on sales orders.
*   **Shipment Booking:** Automatically book shipments and generate waybills when delivery orders are validated.
*   **Shipment Tracking:** Retrieve and store tracking numbers, providing a tracking link for customers.
*   **Multi-Carrier Support:** Access all carriers configured in your Bobgo account (The Courier Guy, RAM, Pargo, etc.).

Configuration
=============

To configure this module, you need to:

1.  Install the module.
2.  Ensure you have an active Bobgo account with API access enabled.
3.  Go to **Inventory > Configuration > Delivery > Delivery Methods**.
4.  Create a new Delivery Method or edit an existing one.
5.  Set the **Provider** to "Bobgo".
6.  In the Bobgo Configuration tab, enter your **Bobgo API Key** (Bearer Token).
7.  Save the delivery method.

Usage
=====

1.  **To Get a Rate:** On a Sales Order, select the configured Bobgo delivery method and click the "Get Rate" button. The shipping cost will be added as a new line on the order.
2.  **To Book a Shipment:** When a Sales Order is confirmed and a Delivery Order is created, validating the delivery order will automatically trigger the shipment booking process with Bobgo. The tracking number will be saved in the "Carrier Tracking Ref" field on the picking.

Bug Tracker
===========

Bugs are tracked on GitHub Issues. In case of trouble, please check there if your issue has already been reported. If you spotted it first, help us smash it by providing a detailed and welcomed feedback.

Do not contact contributors directly about support or help with technical issues.

Maintainer
==========

This module is maintained by JRVT (Pty) Ltd.

*   Website: https://jrvt.co.za
*   Support: info@jrvt.co.za