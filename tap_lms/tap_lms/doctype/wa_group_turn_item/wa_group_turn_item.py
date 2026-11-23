import frappe
from frappe.model.document import Document


class WAGroupTurnItem(Document):
    pass


def backfill_media_gcs_url(bq_id, gcs_url):
    if not bq_id or not gcs_url:
        return False
    existing = frappe.db.sql(
        """
        SELECT parent, media_gcs_url
        FROM "tabWA Group Turn Item"
        WHERE bq_id = %(bq_id)s AND parenttype = 'WA Group Turn'
        LIMIT 1
        """,
        {"bq_id": bq_id},
        as_dict=True,
    )
    if not existing or existing[0].media_gcs_url:
        return False
    frappe.db.sql(
        """
        UPDATE "tabWA Group Turn Item"
        SET media_gcs_url = %(gcs_url)s, modified = now()
        WHERE bq_id = %(bq_id)s AND parenttype = 'WA Group Turn'
        """,
        {"bq_id": bq_id, "gcs_url": gcs_url},
    )
    return True