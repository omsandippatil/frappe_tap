import frappe

QUEUE_SHORT = "short"
QUEUE_DEFAULT = "default"
QUEUE_LONG = "long"

VALID_QUEUES = (QUEUE_SHORT, QUEUE_DEFAULT, QUEUE_LONG)

# Frappe ships three worker queues out of the box: short (~300s timeout),
# default (~300s timeout) and long (~1500s timeout). Any other queue name
# needs a matching entry in common_site_config.json's "workers" block,
# `bench setup procfile`, and a worker restart — none of which can be done
# here, since hooks.py and the site config aren't editable in this
# environment. So every background job in this app now targets one of the
# three built-in queues:
#   AI_QUEUE     = short   -> one turn's AI draft, a few HTTP calls, done in seconds
#   INGEST_QUEUE = long    -> BigQuery pulls / directory sync, checkpointed, can run minutes
#   SEND_QUEUE   = long    -> send-wave dispatch, paced per group, can run minutes on a big wave
INGEST_QUEUE = QUEUE_LONG
SEND_QUEUE = QUEUE_LONG
AI_QUEUE = QUEUE_SHORT


def enqueue(method, queue=QUEUE_DEFAULT, **kwargs):
    if queue not in VALID_QUEUES:
        frappe.log_error(
            title="WAGroupBot: refusing unknown queue",
            message=(
                f"enqueue() called with queue={queue!r} for {method!r}; falling back to "
                f"'default'. Only {VALID_QUEUES} are valid without editing hooks.py or "
                f"common_site_config.json's \"workers\" block."
            ),
        )
        queue = QUEUE_DEFAULT
    return frappe.enqueue(method, queue=queue, **kwargs)