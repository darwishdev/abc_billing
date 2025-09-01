import json
import frappe
from frappe.utils import now

@frappe.whitelist(allow_guest=False, methods=["POST"])
def folio_window_upsert(folio_id: str, window_code: str, window_label: str = None, remarks: str = None):
   """
   Create or update a Folio Window record.
   """
   try:
       # Check if window already exists
       existing = frappe.db.get_value("Folio Window",
           {"parent": folio_id, "window_code": window_code}, "name")

       if existing:
           # Update existing
           doc = frappe.get_doc("Folio Window", existing)
           if window_label:
               doc.window_label = window_label
           if remarks:
               doc.remarks = remarks
           doc.save(ignore_permissions=True)
       else:
           # Create new
           doc = frappe.new_doc("Folio Window")
           doc.parent = folio_id
           doc.parenttype = "Folio"
           doc.parentfield = "folio_windows"
           doc.window_code = window_code
           doc.window_label = window_label or ""
           doc.remarks = remarks or ""
           doc.total_charges = 0.0
           doc.total_payments = 0.0
           doc.balance = 0.0
           doc.insert(ignore_permissions=True)

       frappe.db.commit()

       return {
           "ok": True,
           "folio_window_id": doc.name,
           "action": "updated" if existing else "created"
       }

   except Exception as e:
       frappe.db.rollback()
       frappe.throw(f"Error upserting folio window: {str(e)}")
@frappe.whitelist(allow_guest=False, methods=["GET"])
def folio_list(status=None):
    filters = {}
    if status is not None and status != "":
        filters['folio_status'] = status
    return frappe.get_all("Folio" , filters , [
       'name',
       'linked_reservation',
       'guest',
       'folio_status',
       'check_in_date',
       'check_out_date',
       'cashier',
       'total_charges',
       'total_payments',
       'balance'])

@frappe.whitelist(allow_guest=False, methods=["GET"])
def folio_find(folio_name=str):
    try:
        result = frappe.db.sql("""
            SELECT
                JSON_OBJECT(
                    'folio_name', f.name,
                    'reservation_id', f.linked_reservation,
                    'customer', f.guest,
                    'folio_status', f.folio_status,
                    'check_in_date', f.check_in_date,
                    'check_out_date', f.check_out_date,
                    'invoice',
                    (
                        SELECT
                            JSON_OBJECT(
                                'pos_invoice_id', i.name,
                                'invoice_date', i.posting_date,
                                'folio_windows',
                                (
                                    SELECT
                                        JSON_ARRAYAGG(
                                            JSON_OBJECT(
                                                'folio_window', fw.name,
                                                'window_code', fw.window_code,

                                                -- Items per window
                                                'items',
                                                (
                                                    SELECT
                                                        COALESCE(
                                                            JSON_ARRAYAGG(
                                                                JSON_OBJECT(
                                                                    'name', ii.name,
                                                                    'item_code', ii.item_code,
                                                                    'item_name', ii.item_name,
                                                                    'item_amount', ii.base_amount,
                                                                    'qty', ii.qty,
                                                                    'rate', ii.rate
                                                                )
                                                            ), JSON_ARRAY()
                                                        )
                                                    FROM `tabPOS Invoice Item` ii
                                                    WHERE ii.parent = i.name
                                                      AND ii.folio_window = fw.name
                                                ),

                                                -- Total amount per window
                                                'total_amount',
                                                (
                                                    SELECT COALESCE(SUM(ii.base_amount), 0)
                                                    FROM `tabPOS Invoice Item` ii
                                                    WHERE ii.parent = i.name
                                                      AND ii.folio_window = fw.name
                                                ),

                                                -- Total paid per window
                                                'total_paid',
                                                (
                                                    SELECT COALESCE(SUM(p.amount), 0)
                                                    FROM `tabSales Invoice Payment` p
                                                    WHERE p.parent = i.name
                                                      AND p.folio_window = fw.name
                                                )
                                            )
                                        )
                                    FROM `tabFolio Window` fw
                                    WHERE fw.parent = f.name
                                )
                            )
                        FROM `tabPOS Invoice` i
                        WHERE i.folio = f.name
                        LIMIT 1
                    )
                ) AS folio_details
            FROM `tabFolio` f
            WHERE f.name = %s;
        """, (folio_name,), as_dict=True)

        if result:
            return json.loads(result[0]['folio_details'])
        else:
            return None

    except Exception as e:
        frappe.log_error(f"Error fetching folio details: {str(e)}")
        raise
#
# # Alternative approach using Python aggregation for better control
# @frappe.whitelist(allow_guest=False, methods=["GET"])
# def folio_find(folio_name=str):
#     try:
#         # Get folio basic info
#         folio = frappe.db.get_value(
#             "Folio",
#             folio_name,
#             ["name", "linked_reservation", "guest", "folio_status", "check_in_date", "check_out_date"],
#             as_dict=True
#         )
#
#         if not folio:
#             return None
#
#         # Get all invoices for this folio
#         invoices = frappe.db.get_all(
#             "POS Invoice",
#             filters={"folio": folio_name},
#             fields=["name", "posting_date"]
#         )
#
#         invoice_list = []
#         for invoice in invoices:
#             # Get folio windows that have items in this invoice
#             windows_with_items = frappe.db.sql("""
#                 SELECT DISTINCT fw.name as folio_window
#                 FROM `tabFolio Window` fw
#                 JOIN `tabPOS Invoice Item` ii ON ii.folio_window = fw.name
#                 WHERE fw.parent = %s AND ii.parent = %s
#             """, (folio_name, invoice.name), as_dict=True)
#
#             folio_windows = []
#             for window in windows_with_items:
#                 # Get items for this window in this invoice
#                 items = frappe.db.get_all(
#                     "POS Invoice Item",
#                     filters={
#                         "parent": invoice.name,
#                         "folio_window": window.folio_window
#                     },
#                     fields=["name", "item_code", "item_name", "base_amount", "qty", "rate"]
#                 )
#
#                 folio_windows.append({
#                     "folio_window": window.folio_window,
#                     "items": [
#                         {
#                             "name": item.name,
#                             "item_code": item.item_code,
#                             "item_name": item.item_name,
#                             "item_amount": item.base_amount,
#                             "qty": item.qty,
#                             "rate": item.rate
#                         }
#                         for item in items
#                     ]
#                 })
#
#             invoice_list.append({
#                 "pos_invoice_id": invoice.name,
#                 "invoice_date": invoice.posting_date,
#                 "folio_windows": folio_windows
#             })
#
#         return {
#             "folio_name": folio.name,
#             "reservation_id": folio.linked_reservation,
#             "customer": folio.guest,
#             "folio_status": folio.folio_status,
#             "check_in_date": folio.check_in_date,
#             "check_out_date": folio.check_out_date,
#             "invoices": invoice_list
#         }
#
#     except Exception as e:
#         frappe.log_error(f"Error fetching folio details: {str(e)}")
#         raise
# # @frappe.whitelist(allow_guest=False, methods=["GET"])
# # def folio_find(folio_name=str):
# #     try:
# #         result = frappe.db.sql("""
# #             WITH folio_data AS (
# #               SELECT
# #                 f.name AS folio_name,
# #                 f.linked_reservation AS reservation_id,
# #                 f.guest AS customer,
# #                 f.folio_status,
# #                 f.check_in_date,
# #                 f.check_out_date,
# #                 i.name AS pos_invoice_id,
# #                 i.posting_date AS invoice_date,
# #                 w.name AS folio_window,
# #                 ii.item_name,
# #                 ii.base_amount AS item_amount,
# #                 ii.qty,
# #                 ii.rate
# #               FROM
# #                 `tabFolio` f
# #                 JOIN `tabPOS Invoice` i ON f.name = i.folio
# #                 JOIN `tabFolio Window` w ON f.name = w.parent
# #                 JOIN `tabPOS Invoice Item` ii ON i.name = ii.parent AND w.name = ii.folio_window
# #                 where f.name = %s
# #             )
# #             SELECT
# #               JSON_OBJECT(
# #                 'folio_name', T1.folio_name,
# #                 'reservation_id', T1.reservation_id,
# #                 'customer', T1.customer,
# #                 'folio_status', T1.folio_status,
# #                 'check_in_date', T1.check_in_date,
# #                 'check_out_date', T1.check_out_date,
# #                 'invoice', JSON_OBJECT(
# #                   'pos_invoice_id', T1.pos_invoice_id,
# #                   'invoice_date', T1.invoice_date,
# #                   'folio_windows', JSON_ARRAYAGG(
# #                     JSON_OBJECT(
# #                       'folio_window', T1.folio_window,
# #                       'items', (
# #                         SELECT JSON_ARRAYAGG(
# #                           JSON_OBJECT(
# #                             'name', ii2.name,
# #                             'item_code', ii2.item_code,
# #                             'item_name', ii2.item_name,
# #                             'item_amount', ii2.base_amount,
# #                             'qty', ii2.qty,
# #                             'rate', ii2.rate
# #                           )
# #                         )
# #                         FROM `tabPOS Invoice Item` ii2
# #                         WHERE ii2.parent = T1.pos_invoice_id
# #                           AND ii2.folio_window = T1.folio_window
# #                       )
# #                     )
# #                   )
# #                 )
# #               ) AS folio_details
# #             FROM folio_data AS T1
# #             GROUP BY
# #               T1.folio_name,
# #               T1.reservation_id,
# #               T1.customer,
# #               T1.folio_status,
# #               T1.check_in_date,
# #               T1.check_out_date,
# #               T1.pos_invoice_id,
# #               T1.invoice_date;
# #         """, (folio_name,), as_dict=True)
# #         if result:
# #             # The result is a list of dictionaries, where the value is a string.
# #             # We need to parse this string into a JSON object.
# #             return json.loads(result[0]['folio_details'])
# #         else:
# #             return None
# #
# #         return  result or []
# #
# #     except Exception as e:
# #         frappe.log_error(f"Error fetching cashier device printers map: {str(e)}")
# #         raise
# #
# #
