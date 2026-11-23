import frappe
from frappe.model.document import Document

DEFAULT_SYSTEM_PROMPT = (
	"You are the official school communication assistant replying inside a WhatsApp group for "
	"teachers, students, and parents connected to a school support program. You will be shown "
	"everything one contact sent together in one continuous burst (a \"turn\") as plain text "
	"descriptions — a message's text, a description of a photo (with the photo itself attached to "
	"this prompt only when image analysis is enabled), a poll response, a reaction, a voice note "
	"(transcribed only if voice transcription is enabled — otherwise just noted as sent), or a "
	"combination of these. You are never shown an image for a sticker or a poll response — treat "
	"those purely as the text description given to you, and never guess at their visual content.\n\n"
	"SCOPE: You only discuss school-related matters — academics, attendance, homework, exams, "
	"school events, school announcements, program logistics, and similar topics, and only when the "
	"turn is actually addressed to the program/assistant (a question, a report, a request for help). "
	"If the turn is off-topic but still addressed to the program (personal chit-chat, politics, "
	"unrelated commercial requests), politely redirect the sender back to school-related topics in "
	"one short sentence and tag it \"off_topic\".\n\n"
	"If the turn is clearly NOT addressed to the program at all — it is directed at a specific other "
	"person (a named teacher or student, an \"@someone\" style mention, or an obvious private aside "
	"between two group members) — or you genuinely cannot tell what is being asked or who it is "
	"for, do not reply. Set reply to an empty string and include the tag \"ignored\". Do not guess "
	"who a message \"probably\" means to help; when in doubt, ignore rather than answer.\n\n"
	"ADDRESS STYLE: If you address the sender directly, use respectful, gender-neutral language "
	"only. Never use sir, ma'am, madam, mr, mrs, miss, brother, sister, or any gendered honorific. "
	"Prefer neutral respectful phrasing appropriate to the group's language (e.g. using the "
	"person's name if known, or a neutral respectful form of address).\n\n"
	"REPLY STYLE: Keep replies short — one to three sentences. Reply in the same language the "
	"contact's own message is in, unless this group has an explicit Group Language configured, in "
	"which case use that language instead. You may use one or two relevant emoji to keep the tone "
	"warm and approachable, but never more than two, and never in place of actual content. Do not "
	"invent facts, dates, policies, or commitments the school/program has not made. Never give "
	"direct medical, legal, or financial advice. Never repeat back a phone number, address, or other "
	"personal detail. If the turn needs real follow-up from staff, say a staff member will follow up "
	"instead of answering it yourself. If the turn is only a poll response or a reaction with nothing "
	"meaningful to respond to, the reply must be an empty string.\n\n"
	"CATEGORIZATION: Choose one or more short lowercase tags describing what the turn was about. "
	"Always include \"off_topic\" when the turn is off-topic but still addressed to the program. "
	"Always include \"ignored\" (and only \"ignored\") when the turn is not addressed to the program at "
	"all, per SCOPE above — in that case reply must be empty and no other content tags should be "
	"added. Otherwise use whatever tags genuinely fit (e.g. attendance, homework, exam, feedback, "
	"photo, question, event, urgent, thanks, complaint). Pick as many or as few as apply, up to 8.\n\n"
	"URGENCY: Mark \"support\" if the sender needs help from a real person soon (something broken, "
	"a complaint, distress, an explicit request for staff, a safety concern), otherwise \"normal\". This "
	"only controls how fast the reply is sent — it does not change what you write. An ignored turn "
	"is always \"normal\".\n\n"
	"MEDIA CATEGORY: If this turn includes a photo attached to this prompt, classify what it mainly "
	"shows as exactly one of: classroom, support, homework, event, certificate, other — with a "
	"confidence of high, medium, or low. Choose \"other\" rather than guessing. If no photo is "
	"attached (including every sticker and poll response, which are never attached as images), "
	"media_category and media_category_confidence must both be null.\n\n"
	"TAGGING THE SENDER: If, and only if, your reply is meant to address the sender personally, "
	"begin it with the exact literal text @{{tag}} followed by a single space, then your reply. This "
	"is a fixed placeholder — type it exactly as shown, use it at most once, only at the very start, "
	"and never anywhere else in the reply. Do not replace it yourself; the system substitutes the "
	"real tag before sending.\n\n"
	"You will be told the contact's language and shown the turn's messages, oldest first, each "
	"labeled with its type. Respond with strict structured JSON only, following the exact schema "
	"given after this prompt — no prose, no markdown, no text before or after the JSON object."
)

MODALITY_DEFAULTS = {
	"Text English": {"requests_per_minute": 25, "daily_limit": 500},
	"Text Indic": {"requests_per_minute": 25, "daily_limit": 500},
	"Vision Image": {"requests_per_minute": 15, "daily_limit": 200},
	"Vision Video": {"requests_per_minute": 10, "daily_limit": 100},
	"Voice Audio": {"requests_per_minute": 15, "daily_limit": 150},
}

DEFAULTS = {
	"max_turn_items": 40,
	"ai_max_attempts": 3,
	"bq_max_bytes_billed": 209715200,
	"media_gallery_page_size": 24,
	"bot_mode": "Test",
	"natural_delay_min_minutes": 2,
	"natural_delay_max_minutes": 8,
	"ai_provider": "Groq",
	"turn_window_minutes": 45,
	"fetch_row_limit": 2000,
	"fetch_lookback_minutes": 15,
	"fetch_max_lookback_days": 35,
	"ai_mode_default": "Draft Only",
	"ai_daily_draft_limit": 500,
	"ai_max_batch_messages": 20,
	"ai_language_routing_enabled": 1,
	"ai_indic_language_codes": "hi,mr,gu,ta,te,kn,ml,bn,pa,or,as",
	"ai_content_safety_enabled": 1,
	"ai_blocked_categories": "medical_advice,legal_advice,financial_advice,personal_contact_info",
	"ai_pii_redaction_enabled": 1,
	"ai_human_review_on_low_confidence": 1,
	"support_skip_delay": 1,
	"natural_delay_enabled": 1,
	"reply_threading_enabled": 1,
	"reply_tagging_enabled": 1,
	"video_ai_mode": "Caption Only",
	"media_auto_categorize_enabled": 1,
	"ignore_staff_numbers_enabled": 0,
	"default_wave_size": 25,
	"default_wave_gap_minutes": 10,
	"ingest_chunk_size": 500,
	"ingest_time_budget_seconds": 240,
	"media_upload_max_mb": 16,
	"media_public_url_ttl_minutes": 180,
}

CREDENTIAL_CHECKS = (
	("glific_base_url", "Glific Base URL", False),
	("glific_phone", "Glific Phone", False),
	("glific_password", "Glific Password", True),
	("access_token", "Glific Access Token", True),
	("refresh_token", "Glific Refresh Token", True),
	("bq_project", "BQ Project", False),
	("bq_dataset", "BQ Dataset", False),
	("bq_table", "BQ Messages Table", False),
	("bq_credentials_json", "BQ Credentials JSON", False),
)

SETTINGS_DOCTYPE = "WA Bot Settings"


class WABotSettings(Document):
	def before_insert(self):
		self._seed_defaults()
		self._seed_model_configs()
		self._refresh_mode_banner()
		self._refresh_credential_status()

	def validate(self):
		self._seed_defaults()
		self._seed_model_configs()
		self._validate_mode()
		self._validate_wave_defaults()
		self._refresh_mode_banner()
		self._refresh_credential_status()
		self._normalize_ignored_staff_numbers()
		self._normalize_my_tag_id()

	CHECK_FIELDS = {
		"ai_language_routing_enabled", "ai_content_safety_enabled",
		"ai_pii_redaction_enabled", "ai_human_review_on_low_confidence",
		"support_skip_delay", "natural_delay_enabled",
		"reply_threading_enabled", "reply_tagging_enabled",
		"media_auto_categorize_enabled", "ignore_staff_numbers_enabled",
	}

	def _seed_defaults(self):
		if not self.ai_system_prompt:
			self.ai_system_prompt = DEFAULT_SYSTEM_PROMPT
		for field, value in DEFAULTS.items():
			current = self.get(field)
			is_unset = current in (None, "") if field in self.CHECK_FIELDS else current in (None, "", 0)
			if is_unset:
				self.set(field, value)
		if not self.manual_pull_min_interval_minutes:
			self.manual_pull_min_interval_minutes = 60
		if self.natural_delay_enabled and self.natural_delay_min_minutes and self.natural_delay_max_minutes:
			if self.natural_delay_min_minutes > self.natural_delay_max_minutes:
				frappe.throw("Minimum Delay Minutes cannot exceed Maximum Delay Minutes.")

	def _seed_model_configs(self):
		existing_modalities = {row.modality for row in (self.ai_model_configs or [])}
		for modality, limits in MODALITY_DEFAULTS.items():
			if modality in existing_modalities:
				continue
			self.append("ai_model_configs", {
				"modality": modality,
				"enabled": 0,
				"provider": "Groq",
				"requests_per_minute": limits["requests_per_minute"],
				"daily_limit": limits["daily_limit"],
			})

	def _validate_mode(self):
		if self.bot_mode == "Test" and not self.test_wa_group:
			frappe.throw("Select a Test WA Group before switching to Test Mode. Use the Group Picker on the dashboard's Safety & Settings tab.")
		if self.bot_mode == "Test" and self.test_wa_group:
			# Guard against a stale/disabled Test WA Group: if it's disabled,
			# get_effective_group() would still happily redirect every send
			# to it, and the failure would only surface later at actual send
			# time (per-group "Unknown WA Group" or simply sending into a
			# group nobody is watching). Catch it here instead, at save time.
			is_enabled = frappe.db.get_value("WA Group", self.test_wa_group, "is_enabled")
			if is_enabled is None:
				frappe.throw(f"Test WA Group {self.test_wa_group} does not exist. Pick a valid group.")
			if not is_enabled:
				frappe.throw(
					f"Test WA Group {self.test_wa_group} is currently disabled. "
					f"While Bot Mode is Test, every send is redirected here — enable this group first "
					f"(Safety & Settings tab) or choose a different, enabled Test WA Group."
				)
		if self.bot_mode == "Prod" and not self.test_wa_group:
			frappe.msgprint(
				"No Test WA Group is set. That's fine in Prod Mode, but switching back to "
				"Test Mode later will require one.",
				indicator="orange", alert=True,
			)

	def _validate_wave_defaults(self):
		if self.default_wave_size and self.default_wave_size <= 0:
			frappe.throw("Default Wave Size must be greater than 0.")
		if self.default_wave_gap_minutes is not None and self.default_wave_gap_minutes < 0:
			frappe.throw("Default Wave Gap Minutes cannot be negative.")
		if self.ingest_chunk_size and self.ingest_chunk_size <= 0:
			frappe.throw("Ingest Chunk Size must be greater than 0.")
		if self.ingest_time_budget_seconds and self.ingest_time_budget_seconds <= 0:
			frappe.throw("Ingest Time Budget Seconds must be greater than 0.")

	def _refresh_mode_banner(self):
		if self.bot_mode == "Test":
			group_label = frappe.db.get_value("WA Group", self.test_wa_group, "group_name") if self.test_wa_group else None
			self.test_mode_banner_message = f"TEST MODE — all sends redirected to {group_label or self.test_wa_group or 'no group selected'}"
		else:
			self.test_mode_banner_message = "PROD MODE — sending to real recipients across all groups, collections and geo targets"

	def _refresh_credential_status(self):
		rows = []
		for field, label, is_secret in CREDENTIAL_CHECKS:
			configured = bool(self.get_password(field, raise_exception=False)) if is_secret else bool(self.get(field))
			icon = "✅" if configured else "⚠️"
			state = "configured" if configured else "MISSING"
			rows.append(f'<div style="display:flex;justify-content:space-between;padding:2px 0;">'
			            f'<span>{icon} {label}</span><span style="color:{"#1d7a3e" if configured else "#a12626"};font-weight:600;">{state}</span></div>')
		enabled_modalities = sum(1 for row in (self.ai_model_configs or []) if row.enabled)
		icon = "✅" if enabled_modalities else "⚠️"
		state = f"{enabled_modalities} modality(ies) configured" if enabled_modalities else "MISSING"
		rows.append(f'<div style="display:flex;justify-content:space-between;padding:2px 0;">'
		            f'<span>{icon} AI Model Configs</span><span style="color:{"#1d7a3e" if enabled_modalities else "#a12626"};font-weight:600;">{state}</span></div>')
		self.credential_status_html = "".join(rows)

	def _normalize_ignored_staff_numbers(self):
		if not self.ignored_staff_numbers:
			return
		from tap_lms.wagroupbot.glific import normalize_phone
		seen = []
		for raw in self.ignored_staff_numbers.split(","):
			raw = raw.strip()
			if not raw:
				continue
			normalized = normalize_phone(raw)
			if normalized not in seen:
				seen.append(normalized)
		self.ignored_staff_numbers = ",".join(seen)

	def _normalize_my_tag_id(self):
		if not self.my_tag_id:
			return
		digits = "".join(ch for ch in self.my_tag_id if ch.isdigit())
		self.my_tag_id = digits or None


def is_test_mode(settings=None):
	settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
	return settings.bot_mode == "Test"


def get_effective_group(wa_group, settings=None):
	settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
	if settings.bot_mode == "Test":
		if not settings.test_wa_group:
			frappe.throw("Bot Mode is Test but no Test WA Group is configured in WA Bot Settings.")
		return settings.test_wa_group
	return wa_group


def get_model_config(modality, settings=None):
	settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
	for row in (settings.ai_model_configs or []):
		if row.modality == modality:
			return row if row.enabled else None
	return None


def get_ignored_staff_numbers(settings=None):
	settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
	if not settings.ignore_staff_numbers_enabled or not settings.ignored_staff_numbers:
		return set()
	from tap_lms.wagroupbot.glific import normalize_phone
	return {
		normalize_phone(p.strip())
		for p in settings.ignored_staff_numbers.split(",")
		if p.strip()
	}


def is_ignored_staff_number(phone, settings=None):
	if not phone:
		return False
	ignored = get_ignored_staff_numbers(settings)
	if not ignored:
		return False
	from tap_lms.wagroupbot.glific import normalize_phone
	return normalize_phone(phone) in ignored


def get_my_tag_id(settings=None):
	settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
	raw = (settings.my_tag_id or "").strip()
	digits = "".join(ch for ch in raw if ch.isdigit())
	return digits or None


def credential_health():
	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
	missing = []
	for field, label, is_secret in CREDENTIAL_CHECKS:
		configured = bool(settings.get_password(field, raise_exception=False)) if is_secret else bool(settings.get(field))
		if not configured:
			missing.append(label)
	ai_ready = any(row.enabled for row in (settings.ai_model_configs or []))
	if not ai_ready:
		missing.append("AI Model Config (none enabled)")
	return {
		"all_configured": not missing,
		"missing": missing,
		"glific_ready": not any(m.startswith("Glific") for m in missing),
		"bq_ready": not any(m.startswith("BQ") for m in missing),
		"ai_ready": ai_ready,
	}