import base64
import json
import os
import random
import re
import subprocess
import tempfile

import frappe
import requests
from frappe.utils import now_datetime, add_to_date

from tap_lms.wagroupbot.redis_lock import try_reserve_rpm_slot
from tap_lms.wagroupbot.queues import enqueue as _wag_enqueue, AI_QUEUE
from tap_lms.tap_lms.doctype.wa_bot_settings.wa_bot_settings import get_model_config, is_ignored_staff_number
from tap_lms.wagroupbot.inbound import get_turn_items

SETTINGS_DOCTYPE = "WA Bot Settings"
TURN_DOCTYPE = "WA Group Turn"
TURN_ITEM_DOCTYPE = "WA Group Turn Item"
MAX_TAGS = 8
MAX_REPLY_CHARS = 1200
AI_BUDGET_CACHE_PREFIX = "wagroupbot:ai_draft_count"
AI_BUDGET_TTL_SECONDS = 2 * 86400
VIDEO_FRAME_TIMEOUT_SECONDS = 15
VIDEO_MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
IMAGE_MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
IMAGE_FETCH_TIMEOUT_SECONDS = 15
VOICE_FETCH_TIMEOUT_SECONDS = 20
VOICE_MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024
VOICE_TRANSCRIPT_MAX_CHARS = 1000
TAG_PLACEHOLDER = "@{{tag}}"
MIN_CHARS_FOR_LANGUAGE_DETECTION = 6
IMAGE_REPLY_SUPPRESSION_WINDOW_MINUTES = 90
MAX_EXTRA_VISUALS_TO_CATEGORIZE = 9
TEXT_REPLY_MAX_TOKENS = 500
IMAGE_REPLY_MAX_TOKENS = 260
CLASSIFY_ONLY_MAX_TOKENS = 90

SUPPORTED_IMAGE_MEDIA_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}

NEVER_VISION_ITEM_TYPES = {"Sticker", "Poll Response"}
AI_RELEVANT_ITEM_TYPES = {"Text", "Media", "Voice"}
VALID_MEDIA_CATEGORIES = {"school_activity", "poster", "support", "event", "unnecessary", "other"}
CATEGORY_LABELS = {
    "school_activity": "School Activity",
    "poster": "Poster",
    "support": "Support",
    "event": "Event",
    "unnecessary": "Unnecessary",
    "other": "Other",
}
VALID_CONFIDENCE = {"high", "medium", "low"}

OPENAI_COMPATIBLE_PROVIDERS = {"Groq", "OpenAI Compatible"}

PROVIDER_DEFAULT_BASE_URLS = {
    "Anthropic": "https://api.anthropic.com",
    "Groq": "https://api.groq.com/openai/v1",
    "OpenAI Compatible": "https://api.groq.com/openai/v1",
}

MODALITY_SLUGS = {
    "Text English": "text-english",
    "Text Indic": "text-indic",
    "Vision Image": "vision-image",
    "Vision Video": "vision-video",
    "Voice Audio": "voice-audio",
}

IMAGE_CATEGORY_CONTRACT = (
    "\nJSON only:\n"
    '{"media_category":"school_activity|poster|support|event|unnecessary|other",'
    '"media_category_confidence":"high|medium|low"}'
)

TEXT_JSON_CONTRACT = (
    "\nJSON only, no other text before or after it:\n"
    '{"tags":["lowercase_tag",...],'
    '"urgency":"normal|support",'
    '"reply":"reply text, optionally starting with @{{tag}} followed by a space, or empty string"}'
)

IMAGE_REPLY_JSON_CONTRACT = (
    "\nJSON only, no other text before or after it:\n"
    '{"tags":["lowercase_tag",...],'
    '"urgency":"normal|support",'
    '"media_category":"school_activity|poster|support|event|unnecessary|other",'
    '"media_category_confidence":"high|medium|low",'
    '"reply":"one short line if warranted, else empty string"}'
)

TEXT_SYSTEM_PROMPT = (
    "You are the TAP Buddy school communication assistant, replying inside a WhatsApp group for "
    "teachers, students and parents. You get one contact's full burst of messages (a \"turn\") as "
    "plain text, oldest first, each line labeled by type: message text, poll response, reaction, "
    "or a voice note transcript (or a note that it wasn't transcribed).\n\n"
    "SCOPE: only academics, attendance, homework, exams, school events/announcements and program "
    "logistics, and only when the turn is actually addressed to TAP Buddy. If it's off-topic but "
    "still addressed to TAP Buddy, redirect in one short sentence and tag \"off_topic\".\n\n"
    "NOT ADDRESSED TO YOU: if the turn clearly targets a specific other person (names a teacher/"
    "student, an \"@someone\" mention, an obvious private aside) or you can't tell who it's for or "
    "what's being asked, do not reply — reply must be empty, the only tag is \"ignored\", and no "
    "other tag is added. Never guess.\n\n"
    "ADDRESS STYLE: respectful, gender-neutral only — never sir, ma'am, madam, mr, mrs, miss, "
    "brother, sister or any gendered honorific. Use the person's name if known, otherwise a "
    "neutral respectful phrase.\n\n"
    "REPLY STYLE: 1-3 sentences, in the contact's own language unless the group has a Group "
    "Language set. Up to two relevant emoji, never more, never in place of content. Never invent "
    "facts, dates, policies or commitments. Never give medical, legal or financial advice. Never "
    "repeat a phone number, address or other personal detail. If real staff follow-up is needed, "
    "say staff will follow up rather than answering yourself. If the turn is only a poll response "
    "or reaction, reply must be empty.\n\n"
    "TAGS: up to 8 short lowercase tags for what the turn is about (e.g. attendance, homework, "
    "exam, feedback, question, event, urgent, thanks, complaint). Always add \"off_topic\" when "
    "relevant. \"ignored\" is used alone, only per the rule above.\n\n"
    "URGENCY: \"support\" only if the sender needs a real person soon (something broken, a "
    "complaint, distress, an explicit staff request, a safety concern); otherwise \"normal\". An "
    "ignored turn is always \"normal\".\n\n"
    "TAGGING THE SENDER: to address the sender personally, start the reply with the exact literal "
    "text @{{tag}} followed by one space, used at most once, only at the very start. Never replace "
    "it yourself — the system substitutes the real tag.\n\n"
    "Respond with strict JSON only, exactly matching the schema after this prompt — no prose, no "
    "markdown, nothing before or after the JSON object."
)

IMAGE_REPLY_SYSTEM_PROMPT = (
    "You are the TAP Buddy school communication assistant. One photo a contact just sent is "
    "attached, plus the rest of that burst as plain text.\n\n"
    "CATEGORY (pick exactly one): school_activity — students/teachers visibly doing an activity. "
    "poster — flyer, printed notice, banner, certificate, announcement. support — problem or "
    "damage needing staff attention. event — assembly, ceremony, celebration, non-routine group "
    "photo. unnecessary — unrelated screenshot, meme, forward, blurry/unusable. other — none of "
    "these fit. Confidence high/medium/low — pick low rather than guess confidently.\n\n"
    "REPLY only if ALL hold: category school_activity at high/medium confidence; people are "
    "visibly, actively engaged (not posed); the message is addressed to TAP Buddy, not a named "
    "individual. Otherwise reply is empty. Never more than one short sentence.\n\n"
    "NOT ADDRESSED TO YOU: caption names a teacher/student, an \"@someone\" mention, or an obvious "
    "private aside — reply empty, tag only \"ignored\", still classify the photo normally. If "
    "unclear who it's for, tag \"ignored\" rather than guess.\n\n"
    "ADDRESS STYLE: respectful, gender-neutral — never sir, ma'am, madam, mr, mrs, miss, brother, "
    "sister or any gendered honorific.\n\n"
    "REPLY STYLE: one short warm sentence specific to what's visible, in the contact's language "
    "unless Group Language is set, at most one emoji, never inventing facts beyond the image.\n\n"
    "TAGGING THE SENDER: to address them personally, start the reply with the exact literal text "
    "@{{tag}} followed by one space, at most once, only at the start. Never replace it yourself.\n\n"
    "TAGS: \"ignored\" alone when addressed to a specific person. Otherwise short lowercase tags "
    "(photo, activity, event, poster, support, thanks), up to 8. Urgency \"support\" only if real "
    "staff attention is needed soon, else \"normal\".\n\n"
    "Respond with strict JSON only, exactly matching the schema after this prompt — no prose, no "
    "markdown, nothing before or after the JSON object."
)

IMAGE_CLASSIFY_ONLY_SYSTEM_PROMPT = (
    "Classify one WhatsApp photo from a school program group (TAP Buddy) into exactly one "
    "category: school_activity, poster, support, event, unnecessary, other.\n"
    "school_activity: students/teachers visibly doing an activity.\n"
    "poster: flyer, printed notice, banner, certificate, announcement.\n"
    "support: problem or damage needing staff attention.\n"
    "event: assembly, ceremony, celebration, non-routine group photo.\n"
    "unnecessary: unrelated screenshot, meme, forward, blurry/unusable.\n"
    "other: none of these fit.\n"
    "Confidence high/medium/low — pick low rather than guess confidently."
)


def enqueue_turn_processing(turn_names):
    if not turn_names:
        return
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    if not settings.ai_enabled:
        return
    for turn_name in turn_names:
        _wag_enqueue("tap_lms.wagroupbot.ai.draft_turn_reply", AI_QUEUE, turn_name=turn_name)


def _today_budget_cache_key():
    return f"{AI_BUDGET_CACHE_PREFIX}:{now_datetime().strftime('%Y-%m-%d')}"


def _try_reserve_budget_slot(daily_limit):
    key = _today_budget_cache_key()
    cache = frappe.cache()
    count = cache.incrby(key, 1)
    if count == 1:
        cache.expire(key, AI_BUDGET_TTL_SECONDS)
    if count > daily_limit:
        cache.decrby(key, 1)
        return False
    return True


def _release_budget_slot():
    cache = frappe.cache()
    key = _today_budget_cache_key()
    count = cache.decrby(key, 1)
    if count < 0:
        cache.set_value(key, 0)


def _modality_rpm_key(modality):
    return f"ai_rpm:{MODALITY_SLUGS[modality]}"


def _modality_daily_key(modality):
    return f"wagroupbot:ai_draft_count:{MODALITY_SLUGS[modality]}:{now_datetime().strftime('%Y-%m-%d')}"


def _try_reserve_modality_slot(modality, cfg):
    if not cfg:
        return False
    daily_limit = cfg.daily_limit or 500
    key = _modality_daily_key(modality)
    cache = frappe.cache()
    count = cache.incrby(key, 1)
    if count == 1:
        cache.expire(key, AI_BUDGET_TTL_SECONDS)
    if count > daily_limit:
        cache.decrby(key, 1)
        return False
    if not try_reserve_rpm_slot(_modality_rpm_key(modality), cfg.requests_per_minute or 25):
        cache.decrby(key, 1)
        return False
    return True


def _release_modality_slot(modality):
    cache = frappe.cache()
    key = _modality_daily_key(modality)
    count = cache.decrby(key, 1)
    if count < 0:
        cache.set_value(key, 0)


def _resolve_text_model(settings, language_code):
    indic_codes = {
        c.strip().lower()
        for c in (settings.ai_indic_language_codes or "").split(",")
        if c.strip()
    }
    wants_indic = bool(language_code) and language_code.strip().lower() in indic_codes

    english_cfg = get_model_config("Text English", settings)
    indic_cfg = get_model_config("Text Indic", settings) if wants_indic else None

    if indic_cfg and indic_cfg.model_id:
        return "Text Indic", indic_cfg, True, False

    if not english_cfg or not english_cfg.model_id:
        raise Exception(
            "No AI text model is configured. Enable and fill the 'Text English' row in "
            "WA Bot Settings AI Model Configs at minimum — it is used as the fallback for every language."
        )
    return "Text English", english_cfg, False, wants_indic


def _resolve_vision_image_config(settings):
    return get_model_config("Vision Image", settings)


def _resolve_vision_video_config(settings):
    return get_model_config("Vision Video", settings)


def _resolve_voice_config(settings):
    return get_model_config("Voice Audio", settings)


def _normalize_detected_language_code(detected_code, settings):
    if not detected_code:
        return None
    code = detected_code.strip().lower()
    if not code:
        return None

    indic_codes = {
        c.strip().lower()
        for c in (settings.ai_indic_language_codes or "").split(",")
        if c.strip()
    }
    if code in indic_codes:
        return code
    if code == "en":
        return code
    return None


def _detect_message_language(items, settings):
    text_parts = []
    for item in items:
        if item.get("item_type") not in ("Text", "Voice"):
            continue
        candidate = (item.get("body") or item.get("transcript") or "").strip()
        if candidate:
            text_parts.append(candidate)

    combined_text = " ".join(text_parts).strip()
    if len(combined_text) < MIN_CHARS_FOR_LANGUAGE_DETECTION:
        return None

    try:
        from langdetect import detect, DetectorFactory, LangDetectException
        DetectorFactory.seed = 0
    except ImportError:
        frappe.logger("wagroupbot_ai").warning(
            "langdetect is not installed; skipping message language detection and "
            "falling back to the contact's stored profile language."
        )
        return None

    try:
        detected_code = detect(combined_text)
    except LangDetectException:
        return None
    except Exception as e:
        frappe.logger("wagroupbot_ai").warning(f"Language detection failed: {e}")
        return None

    return _normalize_detected_language_code(detected_code, settings)


def _resolve_reply_language(wa_group, contact_phone, items=None, settings=None):
    from tap_lms.wagroupbot.inbound import resolve_contact

    group_language = frappe.db.get_value("WA Group", wa_group, "group_language")
    if group_language:
        return group_language

    if items:
        settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
        detected = _detect_message_language(items, settings)
        if detected:
            return detected

    return resolve_contact(contact_phone).get("language") or "en"


def _resolve_send_schedule(settings, urgency):
    is_support = urgency == "Support"
    if is_support and settings.ai_human_review_on_low_confidence:
        return "Drafted", None
    if settings.ai_mode_default != "Auto Send":
        return "Drafted", None
    if is_support and settings.support_skip_delay:
        return "Ready To Go", None
    if not settings.natural_delay_enabled:
        return "Ready To Go", None

    min_minutes = settings.natural_delay_min_minutes or 2
    max_minutes = settings.natural_delay_max_minutes or max(min_minutes, 8)
    if max_minutes < min_minutes:
        max_minutes = min_minutes
    delay_minutes = random.uniform(min_minutes, max_minutes)
    return "Ready To Go", add_to_date(now_datetime(), minutes=delay_minutes)


def _passes_content_safety(reply, settings):
    if not settings.ai_content_safety_enabled:
        return True, None
    if reply and len(reply) > MAX_REPLY_CHARS:
        return False, f"Reply exceeded {MAX_REPLY_CHARS} characters."
    stripped = reply.replace(TAG_PLACEHOLDER, "").strip()
    if reply and not stripped:
        return False, "Reply contained only the tag placeholder with no actual content."
    return True, None


def _turn_has_ai_relevant_content(items):
    return any(it.get("item_type") in AI_RELEVANT_ITEM_TYPES for it in items)


def _finalize_turn_without_ai_call(turn_name):
    frappe.db.set_value(TURN_DOCTYPE, turn_name, {
        "ai_tags": "no_reply_needed",
        "ai_reply": "",
        "ai_urgency": "Normal",
        "ai_in_scope": 1,
        "is_closed": 1,
        "turn_status": "Discarded",
    })
    frappe.db.commit()


def draft_turn_reply(turn_name):
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    if not settings.ai_enabled:
        return

    max_attempts = settings.ai_max_attempts or 3

    turn = frappe.db.get_value(
        TURN_DOCTYPE, turn_name,
        ["name", "turn_status", "wa_group", "contact_phone", "ai_attempt_count"],
        as_dict=True,
    )
    if not turn or turn.turn_status != "Open":
        return

    if is_ignored_staff_number(turn.contact_phone, settings):
        frappe.db.set_value(TURN_DOCTYPE, turn_name, {
            "turn_status": "Discarded",
            "ai_tags": "ignored_staff_number",
        })
        frappe.db.commit()
        return

    if (turn.ai_attempt_count or 0) >= max_attempts:
        frappe.db.set_value(TURN_DOCTYPE, turn_name, "turn_status", "Failed")
        frappe.db.commit()
        return

    items = get_turn_items(turn_name)
    if not items:
        return

    items = items[: (settings.ai_max_batch_messages or 20)]

    if not _turn_has_ai_relevant_content(items):
        _finalize_turn_without_ai_call(turn_name)
        return

    daily_limit = settings.ai_daily_draft_limit or 500
    if not _try_reserve_budget_slot(daily_limit):
        frappe.log_error(title="WAGroupBot AI daily budget hit", message=turn_name)
        return

    reserved_modalities = []

    try:
        language = _resolve_reply_language(turn.wa_group, turn.contact_phone, items, settings)

        vision_image_cfg = _resolve_vision_image_config(settings)
        vision_video_cfg = _resolve_vision_video_config(settings)
        voice_cfg = _resolve_voice_config(settings)

        image_bytes, image_media_type, used_vision, visual_item, vision_modality = _first_usable_visual(
            items, settings, vision_image_cfg, vision_video_cfg
        )

        suppress_image_reply = False
        if used_vision and visual_item:
            from tap_lms.wagroupbot.inbound import has_recent_image_reply_for_contact
            suppress_image_reply = has_recent_image_reply_for_contact(
                turn.wa_group, turn.contact_phone,
                IMAGE_REPLY_SUPPRESSION_WINDOW_MINUTES, exclude_turn=turn_name,
            )

        if used_vision:
            vision_cfg = vision_image_cfg if vision_modality == "Vision Image" else vision_video_cfg
            if _try_reserve_modality_slot(vision_modality, vision_cfg):
                reserved_modalities.append(vision_modality)
            else:
                image_bytes, image_media_type, used_vision, visual_item = None, None, False, None
                frappe.logger("wagroupbot_ai").info(
                    f"{turn_name}: vision slot unavailable for {vision_modality}, downgrading to text-only"
                )

        voice_transcript_item = None
        if voice_cfg:
            voice_item = next((it for it in items if it.get("item_type") == "Voice"), None)
            if voice_item and not voice_item.get("transcript"):
                if _try_reserve_modality_slot("Voice Audio", voice_cfg):
                    reserved_modalities.append("Voice Audio")
                    transcript = _maybe_transcribe_voice(voice_item, voice_cfg)
                    if transcript:
                        voice_item["transcript"] = transcript
                        voice_transcript_item = voice_item
                        _patch_turn_item_transcript(turn_name, voice_item.get("bq_id"), transcript)
                        from tap_lms.wagroupbot.inbound import _bump_rollup
                        _bump_rollup(turn.wa_group, now_datetime(), "ai_voice_calls")

        text_modality, text_cfg, is_indic, is_indic_fallback = _resolve_text_model(settings, language)
        if not _try_reserve_modality_slot(text_modality, text_cfg):
            _release_budget_slot()
            for m in reserved_modalities:
                _release_modality_slot(m)
            _wag_enqueue(
                "tap_lms.wagroupbot.ai.draft_turn_reply",
                AI_QUEUE, turn_name=turn_name,
                enqueue_after_commit=True, at_front=False,
            )
            frappe.db.commit()
            return
        reserved_modalities.append(text_modality)

        prompt = _build_prompt(items, language, used_vision, suppress_image_reply)

        attempt_count = (turn.ai_attempt_count or 0) + 1
        vision_cfg_used = vision_image_cfg if vision_modality == "Vision Image" else vision_video_cfg

        if used_vision and not suppress_image_reply:
            system_prompt = IMAGE_REPLY_SYSTEM_PROMPT
            contract = IMAGE_REPLY_JSON_CONTRACT
            max_tokens = IMAGE_REPLY_MAX_TOKENS
        else:
            system_prompt = settings.ai_system_prompt or TEXT_SYSTEM_PROMPT
            contract = TEXT_JSON_CONTRACT
            max_tokens = TEXT_REPLY_MAX_TOKENS

        try:
            parsed = _call_ai_model(
                text_cfg, prompt, image_bytes if not suppress_image_reply else None,
                image_media_type if not suppress_image_reply else None,
                vision_cfg_used, system_prompt, contract, max_tokens,
            )
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(title="WAGroupBot AI draft failed", message=f"{turn_name}: {e}")
            updates = {
                "ai_attempt_count": attempt_count,
                "ai_last_attempt_at": now_datetime(),
                "ai_last_error": str(e)[:500],
            }
            if attempt_count >= max_attempts:
                updates["turn_status"] = "Failed"
            frappe.db.set_value(TURN_DOCTYPE, turn_name, updates)
            frappe.db.set_value(SETTINGS_DOCTYPE, None, {
                "last_ai_draft_status": "Failed",
                "last_ai_draft_message": str(e)[:500],
                "last_ai_draft_at": now_datetime(),
            })
            frappe.db.commit()

            from tap_lms.wagroupbot.inbound import _bump_rollup
            if attempt_count >= max_attempts:
                _bump_rollup(turn.wa_group, now_datetime(), "ai_failed_turns")

            for m in reserved_modalities:
                _release_modality_slot(m)
            _release_budget_slot()
            return

        tags = parsed["tags"]
        reply = _strip_stray_tag_placeholder(parsed["reply"])
        urgency = parsed["urgency"]
        is_ignored = "ignored" in tags

        if used_vision and not suppress_image_reply and reply:
            tags = list(set(tags + ["image_reply_sent"]))[:MAX_TAGS]

        if is_ignored:
            reply = ""
            tags = ["ignored"]
            urgency = "Normal"
        else:
            safe, safety_reason = _passes_content_safety(reply, settings)
            if not safe:
                reply = ""
                tags = list(set(tags + ["safety_discarded"]))[:MAX_TAGS]
                frappe.log_error(title="WAGroupBot AI reply blocked by safety guard",
                                  message=f"{turn_name}: {safety_reason}")

        model_used = (
            vision_image_cfg.model_id if vision_modality == "Vision Image" and used_vision and not suppress_image_reply else
            vision_video_cfg.model_id if vision_modality == "Vision Video" and used_vision and not suppress_image_reply else
            text_cfg.model_id
        )

        if is_ignored:
            turn_status, scheduled_after = "Ignored", None
        elif not reply:
            turn_status, scheduled_after = "Discarded", None
        else:
            turn_status, scheduled_after = _resolve_send_schedule(settings, urgency)

        updates = {
            "ai_tags": ",".join(tags),
            "ai_reply": reply,
            "ai_model_used": model_used,
            "ai_urgency": urgency,
            "ai_attempt_count": attempt_count,
            "ai_last_attempt_at": now_datetime(),
            "ai_last_error": "",
            "ai_in_scope": 0 if is_ignored else 1,
            "is_closed": 1,
            "turn_status": turn_status,
            "scheduled_send_after": scheduled_after,
        }

        frappe.db.set_value(TURN_DOCTYPE, turn_name, updates)
        frappe.db.set_value(SETTINGS_DOCTYPE, None, {
            "last_ai_draft_status": "Success",
            "last_ai_draft_message": f"Drafted turn {turn_name} via {text_cfg.model_id}",
            "last_ai_draft_at": now_datetime(),
        })

        from tap_lms.wagroupbot.inbound import _bump_rollup
        _bump_rollup(turn.wa_group, now_datetime(), "ai_turns_drafted")
        _bump_rollup(turn.wa_group, now_datetime(), "ai_indic_turns" if is_indic else "ai_english_turns")
        if is_indic_fallback:
            _bump_rollup(turn.wa_group, now_datetime(), "ai_indic_fallback_turns")
        if used_vision and not suppress_image_reply:
            _bump_rollup(turn.wa_group, now_datetime(), "ai_vision_calls")

        if used_vision and visual_item and settings.media_auto_categorize_enabled:
            _apply_media_category(visual_item, parsed.get("media_category"), parsed.get("media_category_confidence"))

        frappe.db.commit()

        _categorize_remaining_visuals(items, visual_item, settings, vision_image_cfg, turn_name)

    except Exception:
        frappe.db.rollback()
        frappe.log_error(title="WAGroupBot AI draft unexpected failure", message=f"{turn_name}: {frappe.get_traceback()}")
        for m in reserved_modalities:
            _release_modality_slot(m)
        _release_budget_slot()


def _categorize_remaining_visuals(items, primary_visual_item, settings, vision_image_cfg, turn_name):
    if not settings.media_auto_categorize_enabled or not vision_image_cfg:
        return

    primary_bq_id = primary_visual_item.get("bq_id") if primary_visual_item else None
    remaining = [
        it for it in items
        if it.get("item_type") == "Media"
        and (it.get("media_mime_type") or "").lower() == "image"
        and it.get("bq_id") != primary_bq_id
        and it.get("media_gcs_url")
    ][:MAX_EXTRA_VISUALS_TO_CATEGORIZE]

    for item in remaining:
        if not _try_reserve_modality_slot("Vision Image", vision_image_cfg):
            break
        try:
            content, content_type = _download_with_cap(
                item["media_gcs_url"], IMAGE_FETCH_TIMEOUT_SECONDS, IMAGE_MAX_DOWNLOAD_BYTES,
            )
            media_type = SUPPORTED_IMAGE_MEDIA_TYPES.get(content_type) if content else None
            if content and media_type:
                parsed = _call_classify_only(vision_image_cfg, content, media_type)
                _apply_media_category(item, parsed.get("media_category"), parsed.get("media_category_confidence"))
        except Exception as e:
            frappe.logger("wagroupbot_ai").warning(f"{turn_name}: extra visual classify failed: {e}")
        finally:
            _release_modality_slot("Vision Image")

    if remaining:
        frappe.db.commit()


def _call_classify_only(vision_cfg, image_bytes, image_media_type):
    api_key = vision_cfg.get_password("api_key", raise_exception=False)
    if not api_key or not vision_cfg.model_id:
        return {}

    provider = (vision_cfg.provider or "Groq").strip()
    base_url = (vision_cfg.api_base_url or PROVIDER_DEFAULT_BASE_URLS.get(provider, PROVIDER_DEFAULT_BASE_URLS["Groq"])).rstrip("/")
    system_prompt = IMAGE_CLASSIFY_ONLY_SYSTEM_PROMPT + IMAGE_CATEGORY_CONTRACT

    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "content-type": "application/json"}
        payload = {
            "model": vision_cfg.model_id,
            "max_tokens": CLASSIFY_ONLY_MAX_TOKENS,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": "Classify this photo."},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{image_media_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                    }},
                ]},
            ],
        }
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        text = (choices[0].get("message", {}).get("content") or "").strip() if choices else ""
        return _parse_classify_output(text)

    url = f"{base_url}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": vision_cfg.api_version or "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": vision_cfg.model_id,
        "max_tokens": CLASSIFY_ONLY_MAX_TOKENS,
        "system": system_prompt,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Classify this photo."},
            {"type": "image", "source": {
                "type": "base64", "media_type": image_media_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }},
        ]}],
    }
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()
    text = "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    ).strip()
    return _parse_classify_output(text)


def _parse_classify_output(text):
    candidate = _extract_json_object(text)
    if not candidate:
        return {}
    try:
        parsed = json.loads(candidate)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {
        "media_category": parsed.get("media_category"),
        "media_category_confidence": parsed.get("media_category_confidence"),
    }


def _patch_turn_item_transcript(turn_name, bq_id, transcript):
    if not bq_id:
        return
    frappe.db.sql(
        """
        UPDATE "tabWA Group Turn Item"
        SET transcript = %(transcript)s, modified = now()
        WHERE parent = %(parent)s AND parenttype = 'WA Group Turn' AND bq_id = %(bq_id)s
        """,
        {"transcript": transcript, "parent": turn_name, "bq_id": bq_id},
    )


def _apply_media_category(visual_item, category, confidence):
    category = (category or "").strip().lower()
    confidence = (confidence or "").strip().lower()
    if category not in VALID_MEDIA_CATEGORIES:
        return
    if confidence not in VALID_CONFIDENCE:
        confidence = None

    bq_id = visual_item.get("bq_id")
    if not bq_id:
        return

    existing_source = frappe.db.get_value("WA Media", {"bq_id": bq_id}, "category_source")
    if existing_source == "Manual":
        return

    from tap_lms.tap_lms.doctype.wa_media.wa_media import set_ai_category
    set_ai_category(
        bq_id,
        CATEGORY_LABELS[category],
        confidence.capitalize() if confidence else None,
    )


def _strip_stray_tag_placeholder(reply):
    if not reply:
        return reply
    if reply.startswith(TAG_PLACEHOLDER):
        head, rest = reply[: len(TAG_PLACEHOLDER)], reply[len(TAG_PLACEHOLDER):]
        return head + rest.replace(TAG_PLACEHOLDER, "")
    return reply.replace(TAG_PLACEHOLDER, "")


def _download_with_cap(url, timeout_seconds, max_bytes):
    response = requests.get(url, timeout=timeout_seconds, stream=True)
    response.raise_for_status()

    content_length = response.headers.get("Content-Length")
    if content_length and content_length.isdigit() and int(content_length) > max_bytes:
        response.close()
        return None, None

    content = bytearray()
    for chunk in response.iter_content(chunk_size=1024 * 64):
        content.extend(chunk)
        if len(content) > max_bytes:
            response.close()
            return None, None

    content_type = (response.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip().lower()
    return bytes(content), content_type


def _ffmpeg_available():
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    if settings.video_ffmpeg_available:
        return True
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            frappe.db.set_value(SETTINGS_DOCTYPE, None, "video_ffmpeg_available", 1)
            frappe.db.commit()
            return True
    except Exception:
        pass
    return False


def _extract_video_frame(video_gcs_url, timeout_seconds=VIDEO_FRAME_TIMEOUT_SECONDS):
    if not video_gcs_url:
        return None
    if not _ffmpeg_available():
        return None
    vid_path = None
    thumb_path = None
    try:
        content, _ = _download_with_cap(video_gcs_url, timeout_seconds, VIDEO_MAX_DOWNLOAD_BYTES)
        if content is None:
            return None

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as vid_file:
            vid_file.write(content)
            vid_path = vid_file.name

        thumb_path = vid_path + ".jpg"
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", vid_path, "-ss", "00:00:01.000", "-vframes", "1", thumb_path],
            capture_output=True, timeout=timeout_seconds,
        )
        if result.returncode != 0 or not os.path.exists(thumb_path):
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", vid_path, "-vframes", "1", thumb_path],
                capture_output=True, timeout=timeout_seconds,
            )
            if result.returncode != 0 or not os.path.exists(thumb_path):
                return None

        with open(thumb_path, "rb") as f:
            return f.read()
    except Exception as e:
        frappe.logger("wagroupbot_ai").warning(f"Video frame extraction failed: {e}")
        return None
    finally:
        for p in (vid_path, thumb_path):
            if p and os.path.exists(p):
                os.remove(p)


def _first_usable_visual(items, settings, vision_image_cfg, vision_video_cfg):
    for item in items:
        if item.get("item_type") in NEVER_VISION_ITEM_TYPES:
            continue

        mime = (item.get("media_mime_type") or "").lower()

        if item.get("item_type") == "Media" and mime == "image":
            if not vision_image_cfg:
                continue
            url = item.get("media_gcs_url")
            if not url:
                continue
            try:
                content, content_type = _download_with_cap(url, IMAGE_FETCH_TIMEOUT_SECONDS, IMAGE_MAX_DOWNLOAD_BYTES)
            except Exception as e:
                frappe.logger("wagroupbot_ai").warning(f"Failed to fetch visual media: {e}")
                continue
            if content is None:
                continue
            media_type = SUPPORTED_IMAGE_MEDIA_TYPES.get(content_type)
            if media_type:
                return content, media_type, True, item, "Vision Image"

        elif item.get("item_type") == "Media" and mime == "video" and settings.video_ai_mode != "Never Analyze":
            mode = settings.video_ai_mode
            if mode == "Thumbnail + Caption" and not vision_video_cfg:
                mode = "Caption Only"
                frappe.logger("wagroupbot_ai").info(
                    "video_ai_mode=Thumbnail+Caption but Vision Video config disabled; falling back to Caption Only"
                )
            if mode == "Thumbnail + Caption":
                frame = _extract_video_frame(item.get("media_gcs_url"))
                if frame:
                    return frame, "image/jpeg", True, item, "Vision Video"

    return None, None, False, None, None


def _maybe_transcribe_voice(item, voice_cfg):
    if not voice_cfg or not item.get("media_gcs_url"):
        return None
    if voice_cfg.provider == "Anthropic":
        frappe.logger("wagroupbot_ai").info("Voice Audio provider is Anthropic; no audio endpoint, skipping.")
        return None

    try:
        content, _ = _download_with_cap(item["media_gcs_url"], VOICE_FETCH_TIMEOUT_SECONDS, VOICE_MAX_DOWNLOAD_BYTES)
    except Exception as e:
        frappe.logger("wagroupbot_ai").warning(f"Voice download failed: {e}")
        return None
    if content is None:
        return None

    api_key = voice_cfg.get_password("api_key", raise_exception=False)
    if not api_key:
        return None

    base_url = (voice_cfg.api_base_url or PROVIDER_DEFAULT_BASE_URLS.get(voice_cfg.provider, PROVIDER_DEFAULT_BASE_URLS["Groq"])).rstrip("/")
    url = f"{base_url}/audio/transcriptions"

    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("voice.ogg", content, "audio/ogg")},
            data={"model": voice_cfg.model_id},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        transcript_text = (data.get("text") or "").strip()
        frappe.db.set_value(SETTINGS_DOCTYPE, None, {
            "last_voice_transcribe_status": "Success",
            "last_voice_transcribe_message": f"Transcribed via {voice_cfg.model_id}",
            "last_voice_transcribe_at": now_datetime(),
        })
        return transcript_text[:VOICE_TRANSCRIPT_MAX_CHARS] or None
    except Exception as e:
        frappe.logger("wagroupbot_ai").warning(f"Voice transcription failed: {e}")
        frappe.db.set_value(SETTINGS_DOCTYPE, None, {
            "last_voice_transcribe_status": "Failed",
            "last_voice_transcribe_message": str(e)[:500],
            "last_voice_transcribe_at": now_datetime(),
        })
        return None


def _build_prompt(items, language, used_vision, suppress_image_reply):
    lines = [
        f"Contact language: {language or 'unspecified'}",
        "Messages in this turn, oldest first:",
    ]

    visual_consumed = False

    for item in items:
        item_type = item.get("item_type")
        mime = (item.get("media_mime_type") or "").lower()

        if item_type == "Poll Response":
            lines.append(f"- Poll response: {item.get('poll_choice') or '(no choice captured)'}")
        elif item_type == "Reaction":
            lines.append(f"- Reacted with: {item.get('body') or '(unknown emoji)'}")
        elif item_type == "Sticker":
            lines.append("- Sent a sticker (shown in the gallery only, never sent for AI analysis)")
        elif item_type == "Media" and mime == "video":
            caption = (item.get("body") or "").strip()
            if visual_consumed:
                lines.append("- Sent another video (not analyzed — one-visual-per-turn limit already used)")
            else:
                visual_consumed = True
                if caption:
                    lines.append(f'- Sent a video, caption: "{caption[:200]}"')
                else:
                    lines.append("- Sent a video (no caption)")
        elif item_type == "Media" and mime == "image":
            if not visual_consumed:
                visual_consumed = True
                if used_vision and not suppress_image_reply:
                    lines.append("- Sent an image (attached to this prompt for classification and reply)")
                elif used_vision and suppress_image_reply:
                    lines.append(
                        "- Sent an image. A reply to an earlier image from this same contact was already "
                        "sent recently, so this image is not attached and must not get its own reply — "
                        "treat this only as context for the text portion of the turn."
                    )
                else:
                    lines.append("- Sent an image (not analyzed)")
            else:
                lines.append("- Sent another image (not analyzed — one-visual-per-turn limit already used)")
        elif item_type == "Media":
            lines.append("- Sent a media file (not analyzed)")
        elif item_type == "Voice":
            transcript = (item.get("transcript") or "").strip()
            if transcript:
                lines.append(f'- Sent a voice note, transcript: "{transcript[:400]}"')
            else:
                lines.append("- Sent a voice note (not transcribed)")
        else:
            lines.append(f"- {item.get('body') or ''}")

    return "\n".join(lines)


def _call_ai_model(text_cfg, prompt, image_bytes, image_media_type, vision_cfg, system_prompt, contract, max_tokens):
    model_to_call = vision_cfg.model_id if (image_bytes and image_media_type and vision_cfg) else text_cfg.model_id
    active_cfg = vision_cfg if (image_bytes and image_media_type and vision_cfg) else text_cfg

    if not model_to_call:
        raise Exception(
            f"No model configured for this call "
            f"({'vision' if image_bytes else 'text'} slot has no model_id set)."
        )

    api_key = active_cfg.get_password("api_key", raise_exception=False)
    if not api_key:
        raise Exception(f"No API key configured for {active_cfg.modality}.")

    provider = (active_cfg.provider or "Groq").strip()
    base_url = (active_cfg.api_base_url or PROVIDER_DEFAULT_BASE_URLS.get(provider, PROVIDER_DEFAULT_BASE_URLS["Groq"])).rstrip("/")
    full_system_prompt = system_prompt + contract

    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        }
        if image_bytes and image_media_type:
            user_content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_media_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                    },
                },
            ]
        else:
            user_content = prompt
        payload = {
            "model": model_to_call,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        text = (choices[0].get("message", {}).get("content") or "").strip() if choices else ""
        return _parse_model_output(text)

    url = f"{base_url}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": active_cfg.api_version or "2023-06-01",
        "content-type": "application/json",
    }
    content = [{"type": "text", "text": prompt}]
    if image_bytes and image_media_type:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_media_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            },
        })
    payload = {
        "model": model_to_call,
        "max_tokens": max_tokens,
        "system": full_system_prompt,
        "messages": [{"role": "user", "content": content}],
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    text = "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    ).strip()
    return _parse_model_output(text)


def _extract_json_object(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start:end + 1]


def _salvage_reply_field(text):
    match = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)"', text or "")
    if not match:
        return ""
    try:
        return json.loads(f'"{match.group(1)}"').strip()
    except Exception:
        return match.group(1).strip()


def _parse_model_output(text):
    candidate = _extract_json_object(text)
    parsed = None
    if candidate:
        try:
            parsed = json.loads(candidate)
        except Exception:
            parsed = None

    if not isinstance(parsed, dict):
        salvaged = _salvage_reply_field(text)
        frappe.logger("wagroupbot_ai").warning(
            f"Model output did not parse as JSON, salvaged reply only. Raw (truncated): {(text or '')[:300]}"
        )
        return {
            "tags": [], "urgency": "Normal", "media_category": None,
            "media_category_confidence": None, "reply": salvaged,
        }

    tags = [t.strip().lower() for t in (parsed.get("tags") or []) if t.strip()][:MAX_TAGS]
    reply = (parsed.get("reply") or "").strip()
    urgency_raw = (parsed.get("urgency") or "normal").strip().lower()
    urgency = "Support" if urgency_raw == "support" else "Normal"
    return {
        "tags": tags,
        "urgency": urgency,
        "media_category": parsed.get("media_category"),
        "media_category_confidence": parsed.get("media_category_confidence"),
        "reply": reply,
    }