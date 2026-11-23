import frappe
from frappe.utils import cint

PREFIX = "wagroupbot:"
MEDIA_CACHE_INDEX_KEY = f"{PREFIX}media_cache_index"
MEDIA_CACHE_MAX_ENTRIES = 150


def get_redis_conn():
    return frappe.cache()


def acquire_lock(key, timeout=10):
    try:
        conn = get_redis_conn()
        return bool(conn.set(f"{PREFIX}lock:{key}", "1", nx=True, px=timeout * 1000))
    except Exception:
        frappe.log_error(title="WAGroupBot redis_lock acquire failed", message=f"key={key}: {frappe.get_traceback()}")
        return False


def release_lock(key):
    try:
        conn = get_redis_conn()
        conn.delete(f"{PREFIX}lock:{key}")
    except Exception:
        frappe.log_error(title="WAGroupBot redis_lock release failed", message=f"key={key}: {frappe.get_traceback()}")


def refresh_lock(key, timeout=10):
    try:
        conn = get_redis_conn()
        return bool(conn.set(f"{PREFIX}lock:{key}", "1", xx=True, px=timeout * 1000))
    except Exception:
        frappe.log_error(title="WAGroupBot redis_lock refresh failed", message=f"key={key}: {frappe.get_traceback()}")
        return False


def check_circuit_breaker(service, threshold=5):
    try:
        conn = get_redis_conn()
        failures = cint(conn.get(f"{PREFIX}cb:{service}"))
        return failures >= threshold
    except Exception:
        frappe.log_error(title="WAGroupBot circuit breaker check failed", message=f"service={service}: {frappe.get_traceback()}")
        return False


def record_api_failure(service, reset_timeout=300):
    try:
        conn = get_redis_conn()
        key = f"{PREFIX}cb:{service}"
        current = cint(conn.get(key) or 0)
        conn.incr(key)
        if current == 0:
            conn.expire(key, reset_timeout)
    except Exception:
        frappe.log_error(title="WAGroupBot circuit breaker record failure crashed", message=f"service={service}: {frappe.get_traceback()}")


def record_api_success(service):
    try:
        conn = get_redis_conn()
        conn.delete(f"{PREFIX}cb:{service}")
    except Exception:
        frappe.log_error(title="WAGroupBot circuit breaker record success crashed", message=f"service={service}: {frappe.get_traceback()}")


def try_reserve_rpm_slot(service, limit_per_minute):
    if not limit_per_minute or limit_per_minute <= 0:
        return True
    try:
        conn = get_redis_conn()
        bucket = frappe.utils.now_datetime().strftime("%Y%m%d%H%M")
        key = f"{PREFIX}rpm:{service}:{bucket}"
        count = conn.incrby(key, 1)
        if count == 1:
            conn.expire(key, 70)
        if count > limit_per_minute:
            conn.decrby(key, 1)
            return False
        return True
    except Exception:
        frappe.log_error(title="WAGroupBot rpm slot reservation failed", message=f"service={service}: {frappe.get_traceback()}")
        return False


def register_media_cache_key(cache_key, max_entries=MEDIA_CACHE_MAX_ENTRIES):
    try:
        conn = get_redis_conn()
        existing = conn.get_value(MEDIA_CACHE_INDEX_KEY)
        index = list(existing) if isinstance(existing, list) else []
        if cache_key in index:
            index.remove(cache_key)
        index.append(cache_key)
        evicted = []
        while len(index) > max_entries:
            evicted.append(index.pop(0))
        conn.set_value(MEDIA_CACHE_INDEX_KEY, index, expires_in_sec=86400)
        for stale_key in evicted:
            conn.delete_value(stale_key)
            conn.delete_value(f"{stale_key}:type")
    except Exception:
        frappe.log_error(title="WAGroupBot media cache index update failed", message=f"key={cache_key}: {frappe.get_traceback()}")


def trim_media_cache(max_entries=MEDIA_CACHE_MAX_ENTRIES):
    try:
        conn = get_redis_conn()
        existing = conn.get_value(MEDIA_CACHE_INDEX_KEY)
        index = list(existing) if isinstance(existing, list) else []
        evicted = []
        while len(index) > max_entries:
            evicted.append(index.pop(0))
        if evicted:
            conn.set_value(MEDIA_CACHE_INDEX_KEY, index, expires_in_sec=86400)
            for stale_key in evicted:
                conn.delete_value(stale_key)
                conn.delete_value(f"{stale_key}:type")
        return len(evicted)
    except Exception:
        frappe.log_error(title="WAGroupBot redis_lock trim_media_cache failed", message=frappe.get_traceback())
        return 0


def clear_media_cache():
    try:
        conn = get_redis_conn()
        existing = conn.get_value(MEDIA_CACHE_INDEX_KEY)
        index = list(existing) if isinstance(existing, list) else []
        for key in index:
            conn.delete_value(key)
            conn.delete_value(f"{key}:type")
        conn.delete_value(MEDIA_CACHE_INDEX_KEY)
        return len(index)
    except Exception:
        frappe.log_error(title="WAGroupBot redis_lock clear_media_cache failed", message=frappe.get_traceback())
        return 0