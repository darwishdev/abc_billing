import os
from click import Path
import frappe
from pathlib import Path

from abc_utils.utils.customfield_utils import install_custom_fields
from abc_utils.utils.sql_utils import run_sql

SQL_DIR = Path(frappe.get_app_path("abc_billing",  "sql"))
CUSTOMFIELDS_PATH = os.path.join(frappe.get_app_path("abc_billing"),  "setup", "customfields")
WORKSPACE_NAME = "Billing"
MODULE_NAME = "Billing"

def after_install():
    upsert_workspace()

# Optional: run this on every migrate so changes apply during development
def after_migrate():
    upsert_workspace()
    install_custom_fields(CUSTOMFIELDS_PATH)
    run_sql(SQL_DIR)
    # exec_sql_file('procedures_down.sql')
    # exec_sql_file('procedures_up.sql')

def upsert_workspace():
    """
    Create/Update a Workspace named 'ABC Billing' and make it public.
    Visible to System Manager role only (for now).
    """
    # Fetch or create
    ws = frappe.get_doc("Workspace", WORKSPACE_NAME) if frappe.db.exists("Workspace", WORKSPACE_NAME) else frappe.new_doc("Workspace")
    ws.name = WORKSPACE_NAME
    ws.label = WORKSPACE_NAME
    ws.title = WORKSPACE_NAME
    ws.module = MODULE_NAME
    ws.public = 1               # show on Desk
    ws.is_hidden = 0
    ws.for_user = ""            # not a personal workspace
    ws.icon = "wallet"          # pick any frappe icon name you like

    # Restrict visibility to System Manager for now
    ws.set("roles", [])
    ws.append("roles", {"role": "System Manager"})

    # Shortcuts shown on the workspace



    ws.save(ignore_permissions=True)
    frappe.db.commit()

