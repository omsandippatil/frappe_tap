import frappe


def parse_filters(filters):
    if filters is None:
        return {}
    if isinstance(filters, str):
        return frappe.parse_json(filters) or {}
    return filters


def where(conditions):
    return " AND ".join(conditions) if conditions else "1=1"


def apply_geo_filters(conditions, params, filters, group_field="wa_group"):
    geo = (filters or {}).get("geo") or {}

    if geo.get("wa_group"):
        conditions.append(f"{group_field} = %(f_wa_group)s")
        params["f_wa_group"] = geo["wa_group"]

    if geo.get("wa_group_collection"):
        conditions.append(
            f'{group_field} IN (SELECT whatsapp_group FROM "tabWA Group Collection Mapping" '
            f'WHERE collection = %(f_collection)s)'
        )
        params["f_collection"] = geo["wa_group_collection"]

    for axis in ("district", "city", "state", "school"):
        if geo.get(axis):
            conditions.append(
                f'{group_field} IN (SELECT name FROM "tabWA Group" WHERE {axis} = %(f_{axis})s)'
            )
            params[f"f_{axis}"] = geo[axis]

    if not (filters or {}).get("include_disabled_groups"):
        conditions.append(f'{group_field} IN (SELECT name FROM "tabWA Group" WHERE is_enabled = 1)')

    return conditions, params


def apply_date_range(conditions, params, filters, field, param_prefix="dr"):
    dr = (filters or {}).get("date_range") or {}
    if dr.get("from"):
        key = f"f_{param_prefix}_from"
        conditions.append(f"{field} >= %({key})s")
        params[key] = f"{dr['from']} 00:00:00"
    if dr.get("to"):
        key = f"f_{param_prefix}_to"
        conditions.append(f"{field} <= %({key})s")
        params[key] = f"{dr['to']} 23:59:59"
    return conditions, params


def apply_turn_status(conditions, params, filters, field="turn_status"):
    statuses = (filters or {}).get("turn_status")
    if not statuses:
        return conditions, params
    if isinstance(statuses, str):
        statuses = [statuses]
    conditions.append(f"{field} IN %(f_turn_status)s")
    params["f_turn_status"] = tuple(statuses)
    return conditions, params


def apply_tag(conditions, params, filters, field="ai_tags"):
    tag = (filters or {}).get("tag")
    if not tag:
        return conditions, params
    conditions.append(f"{field} LIKE %(f_tag)s")
    params["f_tag"] = f"%{tag}%"
    return conditions, params


def apply_ai_urgency(conditions, params, filters, field="ai_urgency"):
    urgency = (filters or {}).get("ai_urgency")
    if not urgency:
        return conditions, params
    conditions.append(f"{field} = %(f_ai_urgency)s")
    params["f_ai_urgency"] = urgency
    return conditions, params


def apply_media_category(conditions, params, filters, override_field="m.category_override", ai_field="m.ai_category"):
    category = (filters or {}).get("media_category")
    if not category:
        return conditions, params
    conditions.append(f"COALESCE({override_field}, {ai_field}) = %(f_media_category)s")
    params["f_media_category"] = category
    return conditions, params


def apply_contact_phone(conditions, params, filters, field="contact_phone"):
    phone = (filters or {}).get("contact_phone")
    if not phone:
        return conditions, params
    from tap_lms.wagroupbot.glific import normalize_phone
    conditions.append(f"{field} = %(f_contact_phone)s")
    params["f_contact_phone"] = normalize_phone(phone)
    return conditions, params


def apply_send_status(conditions, params, filters, field="status"):
    statuses = (filters or {}).get("send_status")
    if not statuses:
        return conditions, params
    if isinstance(statuses, str):
        statuses = [statuses]
    conditions.append(f"{field} IN %(f_send_status)s")
    params["f_send_status"] = tuple(statuses)
    return conditions, params


def apply_send_origin(conditions, params, filters, field="origin"):
    origins = (filters or {}).get("send_origin")
    if not origins:
        return conditions, params
    if isinstance(origins, str):
        origins = [origins]
    conditions.append(f"{field} IN %(f_send_origin)s")
    params["f_send_origin"] = tuple(origins)
    return conditions, params


def apply_poll_uuid(conditions, params, filters, field):
    poll_uuid = (filters or {}).get("poll_uuid")
    if not poll_uuid:
        return conditions, params
    conditions.append(f"{field} = %(f_poll_uuid)s")
    params["f_poll_uuid"] = poll_uuid
    return conditions, params