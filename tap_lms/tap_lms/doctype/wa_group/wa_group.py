import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from tap_lms.wagroupbot.glific import normalize_phone

MAX_DISTINCT_PHONES_PER_GROUP = 5000


class WAGroup(Document):
    def before_insert(self):
        if self.school and not (self.district or self.city or self.state):
            school = frappe.db.get_value(
                "School", self.school, ["district", "city", "state"], as_dict=True
            )
            if school:
                self.district = self.district or school.district
                self.city = self.city or school.city
                self.state = self.state or school.state

    @frappe.whitelist()
    def refresh_group_members(self):
        frappe.only_for("System Manager")
        result = resync_group_members(self.name)
        self.reload()
        return result


def _normalized_phone_map(fieldtype, phone_field, extra_fields):
    rows = frappe.get_all(fieldtype, fields=["name", phone_field, *extra_fields])
    mapping = {}
    for r in rows:
        raw_phone = r.get(phone_field)
        if not raw_phone:
            continue
        normalized = normalize_phone(raw_phone)
        if normalized and normalized not in mapping:
            mapping[normalized] = r
    return mapping


def resync_group_members(wa_group_name):
    phones = frappe.db.sql_list(
        """
        SELECT DISTINCT contact_phone
        FROM "tabWA Group Turn"
        WHERE wa_group = %(wa_group)s AND contact_phone IS NOT NULL AND contact_phone != ''
        LIMIT %(limit)s
        """,
        {"wa_group": wa_group_name, "limit": MAX_DISTINCT_PHONES_PER_GROUP},
    )

    normalized_turn_phones = {}
    for p in phones:
        normalized = normalize_phone(p)
        if normalized and normalized not in normalized_turn_phones:
            normalized_turn_phones[normalized] = p

    teacher_map = _normalized_phone_map("Teacher", "phone_number", ["first_name", "last_name", "school_id"])
    student_map = _normalized_phone_map("Student", "phone", ["name1", "school_id"])

    member_rows = []
    matched_normalized = set()
    for normalized, _original_phone in normalized_turn_phones.items():
        teacher = teacher_map.get(normalized)
        if teacher:
            full_name = " ".join(filter(None, [teacher.get("first_name"), teacher.get("last_name")])) or teacher["name"]
            member_rows.append({
                "member_type": "Teacher",
                "teacher": teacher["name"],
                "member_name": full_name,
                "phone_number": teacher.get("phone_number") or _original_phone,
                "school_id": teacher.get("school_id"),
            })
            matched_normalized.add(normalized)
            continue
        student = student_map.get(normalized)
        if student:
            member_rows.append({
                "member_type": "Student",
                "student": student["name"],
                "member_name": student.get("name1") or student["name"],
                "phone_number": student.get("phone") or _original_phone,
                "school_id": student.get("school_id"),
            })
            matched_normalized.add(normalized)

    synced_at = now_datetime()

    frappe.db.sql(
        """
        DELETE FROM "tabWA Group Member"
        WHERE parent = %(wa_group)s AND parenttype = 'WA Group'
        """,
        {"wa_group": wa_group_name},
    )

    for idx, m in enumerate(member_rows, start=1):
        frappe.db.sql(
            """
            INSERT INTO "tabWA Group Member"
                (name, parent, parenttype, parentfield, idx,
                 member_type, teacher, student, member_name, phone_number, school_id,
                 creation, modified, owner, modified_by)
            VALUES
                (%(name)s, %(parent)s, 'WA Group', 'group_members', %(idx)s,
                 %(member_type)s, %(teacher)s, %(student)s, %(member_name)s, %(phone_number)s, %(school_id)s,
                 now(), now(), %(user)s, %(user)s)
            """,
            {
                "name": frappe.generate_hash(length=10),
                "parent": wa_group_name,
                "idx": idx,
                "member_type": m["member_type"],
                "teacher": m.get("teacher"),
                "student": m.get("student"),
                "member_name": m["member_name"],
                "phone_number": m["phone_number"],
                "school_id": m["school_id"],
                "user": frappe.session.user,
            },
        )

    frappe.db.sql(
        """
        UPDATE "tabWA Group"
        SET group_members_synced_at = %(synced_at)s, modified = now()
        WHERE name = %(wa_group)s
        """,
        {"wa_group": wa_group_name, "synced_at": synced_at},
    )
    frappe.db.commit()
    return {
        "matched": len(member_rows),
        "turn_phones_seen": len(normalized_turn_phones),
        "unmatched": len(normalized_turn_phones) - len(matched_normalized),
    }


def on_doctype_update():
    frappe.db.add_index("WA Group", ["school"])
    frappe.db.add_index("WA Group", ["is_enabled", "sync_status"])
    frappe.db.add_index("WA Group", ["district"])
    frappe.db.add_index("WA Group", ["city"])
    frappe.db.add_index("WA Group", ["state"])
    frappe.db.add_index("WA Group", ["group_name"])