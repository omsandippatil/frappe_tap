import datetime
import json

import frappe
from google.api_core.exceptions import BadRequest, GoogleAPICallError, InvalidArgument, NotFound
from google.cloud import bigquery
from google.oauth2 import service_account

from tap_lms.wagroupbot.redis_lock import (
    check_circuit_breaker,
    record_api_failure,
    record_api_success,
)

SETTINGS_DOCTYPE = "WA Bot Settings"
BQ_SERVICE = "bigquery"

NON_BREAKER_EXCEPTIONS = (BadRequest, InvalidArgument, NotFound)


class BigQueryCircuitOpenError(Exception):
    pass


def _array_element_type(value, forced_type=None):
    if forced_type:
        return forced_type
    for v in value:
        if isinstance(v, bool):
            return "BOOL"
        if isinstance(v, int):
            return "INT64"
        if isinstance(v, float):
            return "FLOAT64"
        if isinstance(v, datetime.datetime):
            return "TIMESTAMP" if v.tzinfo is not None else "DATETIME"
        if isinstance(v, datetime.date):
            return "DATE"
        return "STRING"
    return forced_type or "STRING"


def _build_param(name, value, forced_type=None):
    if isinstance(value, (list, tuple, set)):
        values = list(value)
        element_type = _array_element_type(values, forced_type)
        return bigquery.ArrayQueryParameter(name, element_type, values)
    if forced_type:
        return bigquery.ScalarQueryParameter(name, forced_type, value)
    if isinstance(value, bool):
        return bigquery.ScalarQueryParameter(name, "BOOL", value)
    if isinstance(value, int):
        return bigquery.ScalarQueryParameter(name, "INT64", value)
    if isinstance(value, float):
        return bigquery.ScalarQueryParameter(name, "FLOAT64", value)
    if isinstance(value, datetime.datetime):
        return bigquery.ScalarQueryParameter(
            name, "TIMESTAMP" if value.tzinfo is not None else "DATETIME", value
        )
    if isinstance(value, datetime.date):
        return bigquery.ScalarQueryParameter(name, "DATE", value)
    return bigquery.ScalarQueryParameter(name, "STRING", str(value))


def _bq_client(settings):
    if not settings.bq_project or not settings.bq_credentials_json:
        frappe.throw("BQ Project and BQ Credentials JSON must be configured in WA Bot Settings.")

    info = json.loads(settings.bq_credentials_json)
    credentials = service_account.Credentials.from_service_account_info(info)
    return bigquery.Client(project=settings.bq_project, credentials=credentials)


def run_query(sql, params=None, max_bytes_billed=None, param_types=None):
    if check_circuit_breaker(BQ_SERVICE):
        raise BigQueryCircuitOpenError("BigQuery circuit breaker is open. Temporarily unavailable.")

    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)

    try:
        client = _bq_client(settings)

        param_types = param_types or {}
        query_parameters = [
            _build_param(k, v, forced_type=param_types.get(k))
            for k, v in (params or {}).items()
        ]
        job_config = bigquery.QueryJobConfig(
            query_parameters=query_parameters,
            maximum_bytes_billed=int(max_bytes_billed or settings.bq_max_bytes_billed or 209715200),
        )

        job = client.query(sql, job_config=job_config)
        rows = job.result()
        result = [dict(row.items()) for row in rows]
        record_api_success(BQ_SERVICE)
        return result
    except BigQueryCircuitOpenError:
        raise
    except NON_BREAKER_EXCEPTIONS:
        raise
    except GoogleAPICallError:
        record_api_failure(BQ_SERVICE)
        raise
    except Exception:
        record_api_failure(BQ_SERVICE)
        raise