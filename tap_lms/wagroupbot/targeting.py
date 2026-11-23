import frappe


def get_collection_group_ids(collection_name, include_disabled=False):
    if include_disabled:
        return frappe.db.sql_list(
            'SELECT whatsapp_group FROM "tabWA Group Collection Mapping" WHERE collection = %(collection)s',
            {"collection": collection_name},
        )
    return frappe.db.sql_list(
        """
        SELECT m.whatsapp_group
        FROM "tabWA Group Collection Mapping" m
        JOIN "tabWA Group" g ON g.name = m.whatsapp_group
        WHERE m.collection = %(collection)s AND g.is_enabled = 1
        """,
        {"collection": collection_name},
    )


def resolve_groups_by_geo(district=None, city=None, state=None, school=None, include_disabled=False):
    conditions = []
    params = {}
    if school:
        conditions.append("school = %(school)s")
        params["school"] = school
    if district:
        conditions.append("district = %(district)s")
        params["district"] = district
    if city:
        conditions.append("city = %(city)s")
        params["city"] = city
    if state:
        conditions.append("state = %(state)s")
        params["state"] = state
    if not conditions:
        return []
    if not include_disabled:
        conditions.append("is_enabled = 1")
    return frappe.db.sql_list(
        f'SELECT name FROM "tabWA Group" WHERE {" AND ".join(conditions)}',
        params,
    )


def target_group_names(target_type, wa_group=None, wa_group_collection=None,
                        district=None, city=None, state=None, school=None,
                        include_disabled=False):
    if target_type == "Group":
        if not wa_group:
            frappe.throw("WA Group is required when Target Type is Group.")
        return [wa_group]

    if target_type == "Collection":
        if not wa_group_collection:
            frappe.throw("WA Group Collection is required when Target Type is Collection.")
        group_names = get_collection_group_ids(wa_group_collection, include_disabled)
        if not group_names:
            frappe.throw(f"WA Group Collection {wa_group_collection} has no mapped groups.")
        return group_names

    if target_type == "Geo":
        group_names = resolve_groups_by_geo(district, city, state, school, include_disabled)
        if not group_names:
            frappe.throw("No WA Groups match this geo target.")
        return group_names

    frappe.throw(f"Unknown target type: {target_type}")


def group_label_map(group_names):
    if not group_names:
        return {}
    rows = frappe.db.sql(
        """
        SELECT name, group_name
        FROM "tabWA Group"
        WHERE name = ANY(%(names)s)
        """,
        {"names": list(group_names)},
        as_dict=True,
    )
    return {r.name: r.group_name for r in rows}


def remaining_targets(resolved_target_groups, already_sent_group_names):
    if not already_sent_group_names:
        return list(resolved_target_groups)
    already_sent = set(already_sent_group_names)
    return [g for g in resolved_target_groups if g not in already_sent]