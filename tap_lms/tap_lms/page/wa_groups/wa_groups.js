frappe.pages["wa-groups"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "WA Groups",
    single_column: true,
  });
  new WAGroupsDashboard(page);
};

class ReplyCache {
  constructor() {
    this.key = "wag_reply_cache_v6";
    this.ttlMs = 1000 * 60 * 5;
    this.maxPerContact = 2;
    this.maxContacts = 6;
    this.data = this._load();
  }
  _load() {
    try {
      const raw = sessionStorage.getItem(this.key);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (e) {
      return {};
    }
  }
  _save() {
    try {
      sessionStorage.setItem(this.key, JSON.stringify(this.data));
    } catch (e) {}
  }
  _prune() {
    const now = Date.now();
    let changed = false;
    const phones = Object.keys(this.data);
    phones.forEach((phone) => {
      this.data[phone] = (this.data[phone] || []).filter((r) => now - r.ts < this.ttlMs);
      if (!this.data[phone].length) {
        delete this.data[phone];
        changed = true;
      }
    });
    const remaining = Object.keys(this.data);
    if (remaining.length > this.maxContacts) {
      remaining
        .map((p) => ({ p, last: Math.max(...this.data[p].map((r) => r.ts)) }))
        .sort((a, b) => a.last - b.last)
        .slice(0, remaining.length - this.maxContacts)
        .forEach((x) => delete this.data[x.p]);
      changed = true;
    }
    if (changed) this._save();
  }
  add(contactPhone, turnName, bodySent) {
    if (!contactPhone || !bodySent) return;
    this._prune();
    const list = this.data[contactPhone] || (this.data[contactPhone] = []);
    list.push({ turn: turnName || null, body: bodySent, ts: Date.now() });
    if (list.length > this.maxPerContact) list.splice(0, list.length - this.maxPerContact);
    this._save();
  }
  forContact(contactPhone) {
    this._prune();
    return this.data[contactPhone] || [];
  }
  clearContact(contactPhone) {
    delete this.data[contactPhone];
    this._save();
  }
}

const TAB_FILTER_AXES = {
  overview: ["geo", "date_range"],
  conversations: ["geo", "turn_status", "tag", "ai_urgency"],
  campaigns: ["send_status"],
  polls: ["geo", "date_range", "poll_uuid"],
  gallery: ["geo", "media_category"],
  people: ["geo", "date_range"],
  replies: ["geo"],
  reactions: ["geo", "date_range"],
};

class WAGroupsDashboard {
  constructor(page) {
    this.page = page;
    this.localReplies = new ReplyCache();
    this.myTagId = null;
    this.myTagLabel = "tapbuddy";
    this.state = {
      active_tab: "overview",
      date_from: frappe.datetime.add_days(frappe.datetime.now_date(), -7),
      date_to: frappe.datetime.now_date(),
      geo: { district: null, city: null, state: null, school: null, wa_group: null, wa_group_collection: null },
      include_disabled_groups: false,
      privacy_mode: JSON.parse(localStorage.getItem("wag_privacy_mode") || "false"),
      auto_refresh_enabled: true,
      conversations_tab: {
        view_mode: "groups", group_timeline_mode: "all", turn_status: ["Open", "Drafted"], tag: null,
        start: 0, page_length: 25, selected_phone: null, selected_group: null,
      },
      campaigns_tab: { send_status: null, start: 0, page_length: 10 },
      gallery_tab: { category: null, start: 0, page_length: 24 },
      people_tab: { start: 0, page_length: 25, sort_by: "messages" },
      polls_tab: { start: 0, page_length: 25, poll_uuid: null, sort_by: "sent_at" },
      reactions_tab: { start: 0, page_length: 25 },
      replies_tab: { start: 0, page_length: 25, scan_batch: 100 },
      send_recent: { start: 0, page_length: 10 },
      send_draft_loaded: null,
    };
    this.build();
  }

  call(method, args) {
    return frappe.call({ method: `tap_lms.wagroupbot.api.${method}`, args }).then((r) => r.message);
  }

  date_range_args() {
    return {
      date_from: `${this.state.date_from} 00:00:00`,
      date_to: `${this.state.date_to} 23:59:59`,
    };
  }

  build_filters(axes) {
    const f = {};
    axes = axes || [];
    if (axes.includes("geo")) {
      f.geo = { ...this.state.geo };
      f.include_disabled_groups = !!this.state.include_disabled_groups;
    }
    if (axes.includes("date_range")) {
      f.date_range = { from: this.state.date_from, to: this.state.date_to };
    }
    if (axes.includes("turn_status")) {
      const s = this.state.conversations_tab.turn_status;
      f.turn_status = Array.isArray(s) ? s : (s ? [s] : null);
    }
    if (axes.includes("tag")) {
      f.tag = this.state.conversations_tab.tag || null;
    }
    if (axes.includes("ai_urgency")) {
      f.ai_urgency = this.state.conversations_tab.ai_urgency || null;
    }
    if (axes.includes("media_category")) {
      f.media_category = this.state.gallery_tab.category || null;
    }
    if (axes.includes("poll_uuid")) {
      f.poll_uuid = this.state.polls_tab.poll_uuid || null;
    }
    if (axes.includes("send_status")) {
      f.send_status = this.state.campaigns_tab.send_status || null;
    }
    return f;
  }

  filters_for(tabKey) {
    return this.build_filters(TAB_FILTER_AXES[tabKey] || []);
  }

  mask(text) {
    if (!this.state.privacy_mode || !text) return text;
    const s = String(text);
    if (s.length <= 4) return "•".repeat(s.length);
    return s.slice(0, 2) + "•".repeat(Math.max(3, s.length - 4)) + s.slice(-2);
  }

  esc(text) {
    return frappe.utils.escape_html(text == null ? "" : String(text));
  }

  digits_only(text) {
    return (text || "").toString().replace(/[^\d]/g, "");
  }

  load_my_tag_id() {
    return frappe.db.get_doc("WA Bot Settings").then((doc) => {
      this.myTagId = this.digits_only(doc.my_tag_id) || null;
      this.myTagLabel = (doc.my_tag_label || "").trim() || "tapbuddy";
      return this.myTagId;
    }).catch(() => {
      this.myTagId = null;
      this.myTagLabel = "tapbuddy";
      return null;
    });
  }

  tag_display_label() {
    return `@${this.myTagLabel || "tapbuddy"}`;
  }

  message_tags_me(body) {
    if (!this.myTagId || !body) return false;
    const mentions = String(body).match(/@\d[\d\s-]{4,}/g);
    if (!mentions) return false;
    return mentions.some((m) => {
      const d = this.digits_only(m);
      if (!d) return false;
      return d === this.myTagId || d.endsWith(this.myTagId) || this.myTagId.endsWith(d);
    });
  }

  strip_my_tag(body) {
    if (!this.myTagId || !body) return body || "";
    return String(body).replace(/^@\d[\d\s-]{4,}\s*/, "").trim();
  }

  is_poll_vote_body(text) {
    const t = (text || "").trim();
    if (!t) return false;
    if (/^\d{1,8}$/.test(t)) return true;
    if (t.length <= 3) return true;
    return false;
  }

  build() {
    const $root = $(`<div class="wag-wrap"></div>`).appendTo(this.page.body);
    this.$root = $root;
    this.$root.toggleClass("wag-privacy-on", this.state.privacy_mode);

    this.build_toolbar();
    this.build_geo_filter();
    this.build_tabs();

    $root.append(`
      <div class="wag-panel active" data-panel="overview"></div>
      <div class="wag-panel" data-panel="conversations"></div>
      <div class="wag-panel" data-panel="campaigns"></div>
      <div class="wag-panel" data-panel="polls"></div>
      <div class="wag-panel" data-panel="gallery"></div>
      <div class="wag-panel" data-panel="people"></div>
      <div class="wag-panel" data-panel="replies"></div>
      <div class="wag-panel" data-panel="reactions"></div>
      <div class="wag-panel" data-panel="send"></div>
      <div class="wag-panel" data-panel="safety"></div>
    `);

    this.load_my_tag_id().then(() => {
      this.refresh_last_synced_pill();
      this.render_overview();
      this.refresh_tab_counters();
      this.start_auto_refresh();
      this.start_auto_pull();
      this.start_send_wave_watch();
    });
  }

  build_toolbar() {
    const $tb = $(`<div class="wag-toolbar"></div>`).appendTo(this.$root);

    this.page.add_inner_button(__("Pull Latest"), () => this.pull_latest());
    this.page.add_inner_button(__("Pull Groups & Phones"), () => this.pull_directory());
    this.page.add_inner_button(__("Test Connection"), () => this.test_connection());

    $tb.append(`<div id="wag-pull-banner" class="wag-pull-banner" style="display:none;"></div>`);

    const $from = $(`<input type="date" class="form-control input-sm">`)
      .val(this.state.date_from)
      .on("change", (e) => {
        this.state.date_from = e.target.value;
        this.refresh_active_tab();
      });
    const $to = $(`<input type="date" class="form-control input-sm">`)
      .val(this.state.date_to)
      .on("change", (e) => {
        this.state.date_to = e.target.value;
        this.refresh_active_tab();
      });

    $tb.append(`<span class="wag-status-pill">${__("From")}</span>`);
    $tb.append($from);
    $tb.append(`<span class="wag-status-pill">${__("To")}</span>`);
    $tb.append($to);

    const $autoRefresh = $(`
      <label class="wag-toggle-label">
        <input type="checkbox" id="wag-auto-refresh-toggle" ${this.state.auto_refresh_enabled ? "checked" : ""}>
        ${__("Auto-refresh")}
      </label>
    `).on("change", "input", (e) => {
      this.state.auto_refresh_enabled = e.target.checked;
    });
    $tb.append($autoRefresh);

    const $privacyBtn = $(`<button class="btn btn-xs btn-default wag-privacy-btn">🔒 ${__("Privacy")}</button>`)
      .toggleClass("active", this.state.privacy_mode)
      .on("click", () => this.toggle_privacy_mode());
    $tb.append($privacyBtn);
    this.$privacyBtn = $privacyBtn;

    $tb.append(`<span class="wag-status-pill" id="wag-my-tag-pill"></span>`);
    $tb.append(`<span class="wag-status-pill" id="wag-last-synced"></span>`);
    $tb.append(`<span class="wag-status-pill" id="wag-send-wave-pill"></span>`);
  }

  refresh_last_synced_pill() {
    const $pill = this.$root.find("#wag-last-synced");
    const $tagPill = this.$root.find("#wag-my-tag-pill");
    if ($tagPill.length) {
      $tagPill.text(this.myTagId ? `🏷️ ${__("My Tag")}: ${this.tag_display_label()}` : `⚠️ ${__("My Tag ID not set")}`);
    }
    if (!$pill.length) return;
    this.call("get_safety_settings_summary").then((s) => {
      if (!s.last_poll_at) {
        $pill.text(__("Never synced"));
        return;
      }
      const label = s.last_poll_status === "Success" ? "✅" : s.last_poll_status === "Skipped" ? "⏳" : "⚠️";
      $pill.text(`${label} ${__("Last synced")}: ${frappe.datetime.str_to_user(s.last_poll_at)}`);
    });
  }

  toggle_privacy_mode() {
    this.state.privacy_mode = !this.state.privacy_mode;
    localStorage.setItem("wag_privacy_mode", JSON.stringify(this.state.privacy_mode));
    this.$root.toggleClass("wag-privacy-on", this.state.privacy_mode);
    this.$privacyBtn.toggleClass("active", this.state.privacy_mode);
    this.refresh_active_tab();
  }

  build_geo_filter() {
    const $tb = $(`<div class="wag-toolbar"></div>`).appendTo(this.$root);

    this.$collectionSelect = $(`<select class="form-control input-sm"><option value="">${__("All Collections")}</option></select>`)
      .on("change", (e) => this.on_collection_change(e.target.value));
    this.$stateSelect = $(`<select class="form-control input-sm"><option value="">${__("All States")}</option></select>`)
      .on("change", (e) => this.on_geo_change("state", e.target.value));
    this.$districtSelect = $(`<select class="form-control input-sm"><option value="">${__("All Districts")}</option></select>`)
      .on("change", (e) => this.on_geo_change("district", e.target.value));
    this.$citySelect = $(`<select class="form-control input-sm"><option value="">${__("All Cities")}</option></select>`)
      .on("change", (e) => this.on_geo_change("city", e.target.value));
    this.$schoolSelect = $(`<select class="form-control input-sm"><option value="">${__("All Schools")}</option></select>`)
      .on("change", (e) => this.on_geo_change("school", e.target.value));
    this.$groupSelect = $(`<select class="form-control input-sm"><option value="">${__("All WA Groups")}</option></select>`)
      .on("change", (e) => {
        this.state.geo.wa_group = e.target.value || null;
        this.refresh_active_tab();
      });

    const $disabledToggle = $(`
      <label class="wag-toggle-label">
        <input type="checkbox" id="wag-include-disabled-toggle">
        ${__("Show disabled groups too")}
      </label>
    `).on("change", "input", (e) => {
      this.state.include_disabled_groups = e.target.checked;
      this.load_geo_options();
      this.refresh_group_select();
      this.refresh_active_tab();
    });

    $tb.append(
      this.$collectionSelect,
      this.$stateSelect, this.$districtSelect, this.$citySelect, this.$schoolSelect, this.$groupSelect,
      $disabledToggle
    );
    this.load_geo_options();
    this.load_collection_options();
    this.refresh_group_select();
  }

  load_geo_options() {
    this.call("get_geo_options").then((opts) => {
      this.$stateSelect.find("option:not(:first)").remove();
      (opts.states || []).forEach((s) => this.$stateSelect.append(`<option value="${this.esc(s)}">${this.esc(s)}</option>`));
      this.$districtSelect.find("option:not(:first)").remove();
      (opts.districts || []).forEach((d) => this.$districtSelect.append(`<option value="${this.esc(d)}">${this.esc(d)}</option>`));
      this.$citySelect.find("option:not(:first)").remove();
      (opts.cities || []).forEach((c) => this.$citySelect.append(`<option value="${this.esc(c)}">${this.esc(c)}</option>`));
      this.$schoolSelect.find("option:not(:first)").remove();
      (opts.schools || []).forEach((s) => {
        const label = s.school_name || s.name;
        this.$schoolSelect.append(`<option value="${this.esc(s.name)}">${this.esc(label)}</option>`);
      });
    });
  }

  load_collection_options() {
    this.call("get_wa_group_collections").then((rows) => {
      this.$collectionSelect.find("option:not(:first)").remove();
      (rows || []).forEach((c) => {
        const label = c.collection_name || c.name;
        const count = c.group_count ? ` (${c.group_count})` : "";
        this.$collectionSelect.append(`<option value="${this.esc(c.name)}">${this.esc(label)}${count}</option>`);
      });
    });
  }

  on_collection_change(value) {
    this.state.geo.wa_group_collection = value || null;
    this.state.geo.wa_group = null;
    this.$groupSelect.val("");
    this.refresh_group_select();
    this.refresh_active_tab();
  }

  on_geo_change(field, value) {
    this.state.geo[field] = value || null;
    this.state.geo.wa_group = null;
    this.$groupSelect.val("");
    this.refresh_group_select();
    this.refresh_active_tab();
  }

  refresh_group_select() {
    const g = this.state.geo;
    this.call("get_wa_groups_for_filter", {
      district: g.district, city: g.city, state: g.state, school: g.school,
      wa_group_collection: g.wa_group_collection,
      include_disabled_groups: this.state.include_disabled_groups,
    }).then((rows) => {
      this.$groupSelect.find("option:not(:first)").remove();
      rows.forEach((r) => {
        const label = (r.group_name || r.name) + (r.is_enabled ? "" : ` (${__("disabled")})`);
        this.$groupSelect.append(`<option value="${this.esc(r.name)}">${this.esc(label)}</option>`);
      });
    });
  }

  build_tabs() {
    const tabs = [
      { key: "overview", label: __("Overview") },
      { key: "conversations", label: __("Conversations") },
      { key: "campaigns", label: __("Campaigns") },
      { key: "polls", label: __("Polls") },
      { key: "gallery", label: __("Gallery") },
      { key: "people", label: __("People") },
      { key: "replies", label: __("Tagged @Me") },
      { key: "reactions", label: __("Reactions") },
      { key: "send", label: __("Send") },
      { key: "safety", label: __("Safety & Settings") },
    ];
    const $tabs = $(`<div class="wag-tabs"></div>`).appendTo(this.$root);
    tabs.forEach((t, i) => {
      const $btn = $(`
        <button class="wag-tab-btn${i === 0 ? " active" : ""}" data-tab="${t.key}">
          <span class="wag-tab-label">${t.label}</span>
          <span class="wag-tab-badge" style="display:none;">0</span>
        </button>
      `).on("click", () => this.switch_tab(t.key));
      $tabs.append($btn);
    });
    this.$tabs = $tabs;
    this.tab_keys = tabs.map((t) => t.key);
  }

  set_tab_badge(key, count) {
    const $badge = this.$tabs.find(`.wag-tab-btn[data-tab="${key}"] .wag-tab-badge`);
    if (!$badge.length) return;
    if (count > 0) {
      $badge.text(count > 99 ? "99+" : String(count)).show();
    } else {
      $badge.hide();
    }
  }

  refresh_tab_counters() {
    this.call("get_turn_counts").then((counts) => {
      const open = (counts.Open || 0) + (counts.Failed || 0);
      this.set_tab_badge("conversations", open);
    });
    this.call("get_media_processing_summary", {}).then((d) => {
      this.set_tab_badge("gallery", d.unprocessed || 0);
    });
  }

  switch_tab(key) {
    this.state.active_tab = key;
    this.$tabs.find(".wag-tab-btn").each((i, el) => {
      $(el).toggleClass("active", this.tab_keys[i] === key);
    });
    this.$root.find(".wag-panel").removeClass("active");
    this.$root.find(`.wag-panel[data-panel="${key}"]`).addClass("active");
    this.refresh_active_tab();
  }

  refresh_active_tab() {
    const key = this.state.active_tab;
    if (key === "overview") this.render_overview();
    if (key === "campaigns") this.render_campaigns();
    if (key === "conversations") this.render_conversations();
    if (key === "polls") this.render_polls();
    if (key === "gallery") this.render_gallery();
    if (key === "people") this.render_people();
    if (key === "replies") this.render_replies();
    if (key === "reactions") this.render_reactions();
    if (key === "send") this.render_send();
    if (key === "safety") this.render_safety();
  }

  pull_latest() {
    this.call("pull_latest_messages").then((r) => {
      frappe.show_alert({ message: r.message, indicator: r.status === "queued" ? "green" : "orange" });
      if (r.status === "queued") this.start_pull_watch();
    });
  }

  start_pull_watch() {
    const $banner = this.$root.find("#wag-pull-banner");
    $banner.show().text(__("⏳ Pulling latest messages…"));
    if (this._pullWatchTimer) clearInterval(this._pullWatchTimer);
    const startedAt = Date.now();
    this._pullWatchTimer = setInterval(() => {
      this.call("get_safety_settings_summary").then((s) => {
        if (s.last_poll_status && s.last_poll_status !== "Skipped" && s.last_poll_message !== "Pull in progress...") {
          clearInterval(this._pullWatchTimer);
          $banner.hide();
          frappe.show_alert({
            message: s.last_poll_message || __("Pull finished"),
            indicator: s.last_poll_status === "Success" ? "green" : "red",
          });
          this.refresh_active_tab();
          this.refresh_last_synced_pill();
          this.refresh_tab_counters();
        } else if (Date.now() - startedAt > 120000) {
          clearInterval(this._pullWatchTimer);
          $banner.hide();
        }
      });
    }, 3000);
  }

  is_tab_visible() {
    return document.visibilityState === "visible" && !document.hidden;
  }

  start_auto_refresh() {
    if (this._autoRefreshTimer) clearInterval(this._autoRefreshTimer);
    const REFRESH_INTERVAL_MS = 10 * 60 * 1000;
    this._autoRefreshTimer = setInterval(() => {
      if (!this.state.auto_refresh_enabled) return;
      if (!this.is_tab_visible()) return;
      if (this.$root.find(".wag-convo-composer-input:focus").length) return;
      if (["overview", "conversations"].includes(this.state.active_tab)) this.refresh_active_tab();
      this.refresh_tab_counters();
    }, REFRESH_INTERVAL_MS);
  }

  start_auto_pull() {
    if (this._autoPullTimer) clearInterval(this._autoPullTimer);
    const AUTO_PULL_INTERVAL_MS = 10 * 60 * 1000;
    this._autoPullTimer = setInterval(() => {
      if (!this.state.auto_refresh_enabled) return;
      if (!this.is_tab_visible()) return;
      if (!this.$root || !document.body.contains(this.$root[0])) return;
      if (this._pullInFlight) return;
      this._pullInFlight = true;
      this.call("auto_pull_if_due")
        .then((r) => {
          if (r.status === "queued") this.start_pull_watch();
        })
        .always(() => {
          this._pullInFlight = false;
        });
    }, AUTO_PULL_INTERVAL_MS);

    $(window).on("hashchange.wagAutoPull", () => {
      if (!this.$root || !document.body.contains(this.$root[0])) {
        clearInterval(this._autoPullTimer);
        clearInterval(this._autoRefreshTimer);
        $(window).off("hashchange.wagAutoPull");
      }
    });
  }

  start_send_wave_watch() {
    if (this._sendWaveTimer) clearInterval(this._sendWaveTimer);
    const SEND_WAVE_INTERVAL_MS = 30 * 1000;
    const $pill = this.$root.find("#wag-send-wave-pill");

    const tick = () => {
      if (!this.$root || !document.body.contains(this.$root[0])) return;
      if (!this.is_tab_visible()) return;
      if (this._sendWaveInFlight) return;
      this._sendWaveInFlight = true;
      this.call("run_due_send_waves")
        .then((r) => {
          const dispatched = (r && r.dispatched) || 0;
          if ($pill.length) {
            $pill.text(dispatched ? `📤 ${__("Dispatched")} ${dispatched} ${__("wave(s)")}` : `📤 ${__("Send watcher active")}`);
          }
          if (dispatched && this.state.active_tab === "campaigns") this.render_campaigns();
        })
        .always(() => {
          this._sendWaveInFlight = false;
        });
    };

    tick();
    this._sendWaveTimer = setInterval(tick, SEND_WAVE_INTERVAL_MS);

    $(window).on("hashchange.wagSendWave", () => {
      if (!this.$root || !document.body.contains(this.$root[0])) {
        clearInterval(this._sendWaveTimer);
        $(window).off("hashchange.wagSendWave");
      }
    });
  }

  pull_directory() {
    this.call("pull_wa_groups_and_phones").then((r) => {
      frappe.show_alert({ message: r.message, indicator: "green" });
      this.load_geo_options();
      this.load_collection_options();
      this.refresh_group_select();
    });
  }

  test_connection() {
    this.call("test_glific_connection").then((r) => {
      frappe.show_alert({ message: r.message, indicator: r.status === "success" ? "green" : "red" });
    });
  }

  media_proxy_url(turnName, itemBqId) {
    const params = new URLSearchParams();
    if (turnName) params.set("turn_name", turnName);
    if (itemBqId) params.set("item_bq_id", itemBqId);
    return `/api/method/tap_lms.wagroupbot.media_proxy.get_media?${params.toString()}`;
  }

  safe_parse_items(raw) {
    if (Array.isArray(raw)) return raw;
    try {
      const parsed = JSON.parse(raw || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  is_poll_item(it) {
    if (it.item_type === "Poll Sent") return true;
    if (it.item_type === "Poll Response") return true;
    return false;
  }

  has_real_content(it) {
    if (this.is_poll_item(it)) return false;
    if (it.item_type === "Media") return true;
    const text = (it.body || "").trim();
    return !!text;
  }

  visible_turn_items(items) {
    return (items || []).filter((it) => this.has_real_content(it));
  }

  normalized_item_kind(it) {
    if (it.item_type === "Media") {
      const mime = (it.media_mime_type || "").toLowerCase();
      if (mime === "image") return "image";
      if (mime === "video") return "video";
      return "file";
    }
    if (it.item_type === "Text") return "text";
    if (it.item_type === "Voice") return "voice";
    if (it.item_type === "Sticker") return "sticker";
    if (it.item_type === "Reaction") return "reaction";
    return "other";
  }

  tag_label(tag) {
    if (tag === "ignored") return { text: `🚫 ${__("Ignored")}`, cls: "wag-chip-ignored" };
    if (tag === "off_topic") return { text: `↪ ${__("Off topic")}`, cls: "" };
    if (tag === "urgent" || tag === "support") return { text: `🆘 ${this.esc(tag)}`, cls: "wag-chip-urgent" };
    if (tag === "safety_discarded") return { text: `⛔ ${__("Blocked by safety")}`, cls: "wag-chip-ignored" };
    if (tag === "image_reply_sent") return { text: `📷 ${__("Image replied")}`, cls: "" };
    if (tag === "tagged_me") return { text: `🏷️ ${this.tag_display_label()}`, cls: "wag-chip-tagged" };
    if (tag === "no_reply_needed" || tag === "ignored_staff_number") return { text: this.esc(tag.replace(/_/g, " ")), cls: "wag-chip-ignored" };
    return { text: this.esc(tag), cls: "" };
  }

  render_tags_row(tagsRaw, taggedMe) {
    const tags = (tagsRaw || "").split(",").map((t) => t.trim()).filter(Boolean);
    const allTags = taggedMe && !tags.includes("tagged_me") ? ["tagged_me", ...tags] : tags;
    if (!allTags.length) return "";
    return allTags.map((t) => {
      const info = this.tag_label(t);
      return `<span class="wag-chip ${info.cls}">${info.text}</span>`;
    }).join("");
  }

  render_turn_item(it, turnName) {
    if (!this.has_real_content(it)) return "";
    const kind = this.normalized_item_kind(it);
    const bqId = it.bq_id;
    const taggedMe = this.message_tags_me(it.body);
    const displayText = taggedMe ? this.strip_my_tag(it.body) : (it.body || "");
    const tagBadge = taggedMe ? `<span class="wag-tag-badge">🏷️ ${this.tag_display_label()}</span>` : "";

    if (kind === "text") {
      if (!displayText.trim()) return "";
      return `<div class="wag-bubble wag-bubble-in${taggedMe ? " wag-bubble-tagged" : ""}" data-bq-id="${this.esc(bqId)}">${tagBadge}<span class="wag-bubble-text">${this.esc(displayText)}</span></div>`;
    }
    if (kind === "image") {
      const url = this.media_proxy_url(turnName, bqId);
      return `<div class="wag-bubble wag-bubble-in wag-bubble-media${taggedMe ? " wag-bubble-tagged" : ""}" data-bq-id="${this.esc(bqId)}">
                ${tagBadge}
                <img class="wag-turn-item-media" src="${url}" loading="lazy" alt=""
                     onclick="window.open('${url}', '_blank')"
                     onerror="this.closest('.wag-bubble-media').classList.add('wag-media-broken')">
                ${displayText ? `<div class="wag-bubble-caption">${this.esc(displayText)}</div>` : ""}
              </div>`;
    }
    if (kind === "video") {
      const url = this.media_proxy_url(turnName, bqId);
      return `<div class="wag-bubble wag-bubble-in wag-bubble-media${taggedMe ? " wag-bubble-tagged" : ""}" data-bq-id="${this.esc(bqId)}">
                ${tagBadge}
                <video class="wag-turn-item-media" controls preload="metadata" src="${url}"
                       onerror="this.closest('.wag-bubble-media').classList.add('wag-media-broken')"></video>
                ${displayText ? `<div class="wag-bubble-caption">${this.esc(displayText)}</div>` : ""}
              </div>`;
    }
    if (kind === "file") {
      return `<div class="wag-bubble wag-bubble-in${taggedMe ? " wag-bubble-tagged" : ""}" data-bq-id="${this.esc(bqId)}">${tagBadge}<span class="wag-bubble-text">📎 ${this.esc(displayText || __("File"))}</span></div>`;
    }
    if (kind === "voice") {
      const body = it.transcript
        ? `<span class="wag-bubble-caption">"${this.esc(it.transcript)}"</span>`
        : `<span class="wag-muted">${__("Voice note (not transcribed)")}</span>`;
      return `<div class="wag-bubble wag-bubble-in${taggedMe ? " wag-bubble-tagged" : ""}" data-bq-id="${this.esc(bqId)}">${tagBadge}<span class="wag-bubble-text">🎤 ${body}</span></div>`;
    }
    if (kind === "sticker") {
      return `<div class="wag-bubble wag-bubble-in wag-bubble-sticker" data-bq-id="${this.esc(bqId)}">🏷️ ${__("Sticker")}</div>`;
    }
    if (kind === "reaction") {
      return `<div class="wag-bubble wag-bubble-in wag-bubble-reaction" data-bq-id="${this.esc(bqId)}"><span class="wag-bubble-text">${this.esc(it.body || "")} ${__("reacted")}</span></div>`;
    }
    return "";
  }

  render_turn_item_with_sender(it, turnName, senderLabel) {
    const html = this.render_turn_item(it, turnName);
    if (!html) return "";
    return `<div class="wag-group-item-row">
              <div class="wag-group-item-sender">${this.esc(senderLabel)}</div>
              ${html}
            </div>`;
  }

  turn_item_preview(items) {
    const visible = this.visible_turn_items(items);
    if (!visible.length) return `<span class="wag-muted">${__("No content")}</span>`;
    for (let i = visible.length - 1; i >= 0; i--) {
      const it = visible[i];
      const kind = this.normalized_item_kind(it);
      if (kind === "text") {
        const text = this.strip_my_tag(it.body).trim();
        if (text) return this.esc(text.slice(0, 80));
        continue;
      }
      if (kind === "image") return `📷 ${__("Photo")}`;
      if (kind === "video") return `🎥 ${__("Video")}`;
      if (kind === "file") return `📎 ${__("File")}`;
      if (kind === "voice") return `🎤 ${__("Voice message")}`;
      if (kind === "sticker") return `🏷️ ${__("Sticker")}`;
      if (kind === "reaction") return `${this.esc(it.body || "")} ${__("reacted")}`;
    }
    return `<span class="wag-muted">${__("No content")}</span>`;
  }

  open_lightbox(url) {
    const $backdrop = $(`
      <div class="wag-lightbox-backdrop">
        <span class="wag-lightbox-close">&times;</span>
        <img class="wag-lightbox-img" src="${this.esc(url)}" alt="">
      </div>
    `).appendTo("body");
    const close = () => $backdrop.remove();
    $backdrop.on("click", (e) => { if (e.target === $backdrop[0]) close(); });
    $backdrop.find(".wag-lightbox-close").on("click", close);
  }

  render_overview() {
    const $panel = this.$root.find('[data-panel="overview"]').empty();
    const $cards = $(`<div class="wag-cards"></div>`).appendTo($panel);
    $panel.append(`<div class="wag-toolbar"><span class="wag-status-pill">${__("Granularity")}</span></div>`);
    const $granularityRow = $panel.find(".wag-toolbar").last();
    const $granSelect = $(`
      <select class="form-control input-sm">
        <option value="auto">${__("Auto")}</option>
        <option value="hour">${__("Hour")}</option>
        <option value="day">${__("Day")}</option>
      </select>
    `).on("change", () => this.render_overview());
    $granularityRow.append($granSelect);

    const $chartWrap = $(`<div id="wag-trend-chart" style="margin-bottom:18px;"></div>`).appendTo($panel);
    $panel.append(`<h5>${__("Tag Distribution")}</h5>`);
    const $tagWrap = $(`<div class="wag-chip-row" id="wag-tag-strip"></div>`).appendTo($panel);
    $panel.append(`<h5>${__("AI Model Usage")}</h5>`);
    const $modelWrap = $(`<div class="wag-table-wrap" id="wag-model-usage"></div>`).appendTo($panel);
    $panel.append(`<h5>${__("Media Ingestion Diagnostics")}</h5>`);
    const $diagWrap = $(`<div class="wag-cards" id="wag-media-diag"></div>`).appendTo($panel);
    $panel.append(`<h5>${__("Top Active Groups")}</h5>`);
    const $topWrap = $(`<div class="wag-table-wrap"></div>`).appendTo($panel);

    const g = this.state.geo;
    const rangeDays = frappe.datetime.get_day_diff(this.state.date_to, this.state.date_from);
    let granularity = $granSelect.val();
    if (granularity === "auto") granularity = rangeDays <= 2 ? "hour" : "day";

    const args = {
      ...this.date_range_args(),
      wa_group: g.wa_group, district: g.district, city: g.city, state: g.state, school: g.school,
      granularity,
    };

    this.call("get_overview_summary", args).then((d) => {
      const cards = [
        { label: __("Total Events"), value: d.total_events || 0 },
        { label: __("Media Submissions"), value: d.media_count || 0 },
        { label: __("Poll Responses"), value: d.poll_count || 0 },
        { label: __("Tagged Replies"), value: d.tagged_reply_count || 0 },
        { label: __("Groups Active"), value: d.groups_active || 0 },
        { label: __("AI Failed"), value: d.ai_failed_turns || 0 },
        { label: __("AI Vision Calls"), value: d.ai_vision_calls || 0 },
        { label: __("AI Voice Calls"), value: d.ai_voice_calls || 0 },
        { label: __("AI Turns Drafted"), value: d.ai_turns_drafted || 0 },
      ];
      $cards.empty();
      cards.forEach((c) => {
        $cards.append(`
          <div class="wag-card">
            <div class="wag-card-value">${c.value}</div>
            <div class="wag-card-label">${c.label}</div>
          </div>
        `);
      });

      $(`
        <div class="wag-card" style="cursor:pointer">
          <div class="wag-card-value">${d.unprocessed_media || 0}</div>
          <div class="wag-card-label">${__("Unprocessed Media")}</div>
        </div>
      `).on("click", () => {
        this.state.gallery_tab.category = "__unprocessed__";
        this.switch_tab("gallery");
      }).appendTo($cards);

      $(`
        <div class="wag-card" style="cursor:pointer">
          <div class="wag-card-value">${d.ai_ignored_turns || 0}</div>
          <div class="wag-card-label">${__("AI Ignored Turns")}</div>
        </div>
      `).on("click", () => {
        this.state.conversations_tab.turn_status = ["Ignored"];
        this.switch_tab("conversations");
      }).appendTo($cards);

      $(`
        <div class="wag-card" style="cursor:pointer;${(d.reactions_awaiting_group_match || 0) ? "border-color:#d4a900;" : ""}">
          <div class="wag-card-value">${d.reactions_awaiting_group_match || 0}</div>
          <div class="wag-card-label">${__("Reactions Awaiting Group Match")}</div>
        </div>
      `).on("click", () => this.open_reaction_retry_queue_drawer()).appendTo($cards);

      if (d.ai_indic_turns || d.ai_indic_fallback_turns) {
        [
          { label: __("AI Indic Turns"), value: d.ai_indic_turns || 0 },
          { label: __("AI Indic Fallback Turns"), value: d.ai_indic_fallback_turns || 0 },
        ].forEach((c) => {
          $cards.append(`
            <div class="wag-card">
              <div class="wag-card-value">${c.value}</div>
              <div class="wag-card-label">${c.label}</div>
            </div>
          `);
        });
      }

      this.call("get_turn_counts").then((counts) => {
        [
          { label: __("Open"), value: counts.Open || 0, key: "Open" },
          { label: __("AI Drafted"), value: counts.Drafted || 0, key: "Drafted" },
          { label: __("Ready To Go"), value: counts["Ready To Go"] || 0, key: "Ready To Go" },
          { label: __("Failed"), value: counts.Failed || 0, key: "Failed" },
        ].forEach((c) => {
          $(`
            <div class="wag-card" style="cursor:pointer">
              <div class="wag-card-value">${c.value}</div>
              <div class="wag-card-label">${c.label}</div>
            </div>
          `)
            .on("click", () => {
              this.state.conversations_tab.turn_status = [c.key];
              this.switch_tab("conversations");
            })
            .appendTo($cards);
        });
        this.refresh_tab_counters();
      });
    });

    this.call("get_media_ingestion_diagnostics", args).then((d) => {
      $diagWrap.empty();
      [
        { label: __("Visual Items Seen In Turns"), value: d.turn_items_media_or_sticker },
        { label: __("WA Media Rows Saved"), value: d.wa_media_rows },
        { label: __("ffmpeg Available"), value: d.ffmpeg_available ? __("Yes") : __("No") },
      ].forEach((c) => {
        $diagWrap.append(`
          <div class="wag-card">
            <div class="wag-card-value">${c.value}</div>
            <div class="wag-card-label">${c.label}</div>
          </div>
        `);
      });
    });

    this.call("get_daily_trend", args).then((rows) => {
      const buckets = [...new Set(rows.map((r) => r.bucket))].sort();
      const series = ["text_count", "media_count", "voice_count", "poll_response_count", "reaction_count", "sticker_count"];
      const labels = { text_count: "Text", media_count: "Media", voice_count: "Voice", poll_response_count: "Poll", reaction_count: "Reaction", sticker_count: "Sticker" };
      const datasets = series.map((key) => ({
        name: labels[key],
        values: buckets.map((b) => {
          const match = rows.find((r) => r.bucket === b);
          return match ? (match[key] || 0) : 0;
        }),
      }));
      $chartWrap.empty();
      if (!buckets.length) {
        $chartWrap.append(`<div class="wag-empty">${__("No activity in this range.")}</div>`);
        return;
      }
      const chartLabels = buckets.map((b) =>
        granularity === "hour" ? frappe.datetime.str_to_user(b).replace(/:00$/, "") : frappe.datetime.str_to_user(b)
      );
      new frappe.Chart("#wag-trend-chart", {
        data: { labels: chartLabels, datasets },
        type: "bar",
        height: 220,
        colors: ["#128C7E", "#25D366", "#ffa00a", "#e03131", "#17a2b8", "#6c757d"],
      });
    });

    this.call("get_tag_distribution", args).then((rows) => {
      $tagWrap.empty();
      if (!rows.length) {
        $tagWrap.append(`<div class="wag-empty">${__("No tags in this range.")}</div>`);
        return;
      }
      rows.forEach((r) => {
        $(`<span class="wag-chip">${this.esc(r.tag)} <span class="wag-chip-count">${r.count}</span></span>`)
          .on("click", () => {
            this.state.conversations_tab.tag = r.tag;
            this.state.conversations_tab.turn_status = null;
            this.switch_tab("conversations");
          })
          .appendTo($tagWrap);
      });
    });

    this.call("get_model_usage_breakdown", this.date_range_args()).then((rows) => {
      $modelWrap.empty();
      if (!rows.length) {
        $modelWrap.append(`<div class="wag-empty">${__("No AI drafts in this range.")}</div>`);
        return;
      }
      const $table = $(`
        <table class="wag-table">
          <thead><tr><th>${__("Model")}</th><th>${__("Turns")}</th></tr></thead>
          <tbody></tbody>
        </table>
      `);
      const $tbody = $table.find("tbody");
      rows.forEach((r) => {
        $tbody.append(`<tr><td>${this.esc(r.ai_model_used)}</td><td>${r.turns}</td></tr>`);
      });
      $modelWrap.append($table);
    });

    this.call("get_top_active_groups", args).then((rows) => {
      $topWrap.empty();
      if (!rows.length) {
        $topWrap.append(`<div class="wag-empty">${__("No group activity in this range.")}</div>`);
        return;
      }
      const $table = $(`
        <table class="wag-table">
          <thead><tr>
            <th>${__("Group")}</th><th>${__("State")}</th><th>${__("District")}</th><th>${__("City")}</th><th>${__("School")}</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      `);
      const $tbody = $table.find("tbody");
      rows.forEach((r) => {
        const $tr = $(`
          <tr class="wag-row-clickable">
            <td>${this.esc(r.group_name || r.wa_group || "")}</td>
            <td>${this.esc(r.state || "")}</td>
            <td>${this.esc(r.district || "")}</td>
            <td>${this.esc(r.city || "")}</td>
            <td>${this.esc(r.school || "")}</td>
          </tr>
        `).on("click", () => {
          this.state.geo.wa_group = r.wa_group;
          this.$groupSelect.val(r.wa_group);
          this.switch_tab("conversations");
        });
        $tbody.append($tr);
      });
      $topWrap.append($table);
    });
  }

  open_reaction_retry_queue_drawer() {
    const $backdrop = $(`<div class="wag-person-drawer-backdrop"></div>`).appendTo("body");
    const $drawer = $(`
      <div class="wag-person-drawer">
        <div class="wag-person-drawer-head">
          <h4>${__("Reactions Awaiting Group Match")}</h4>
          <span class="wag-person-drawer-close">&times;</span>
        </div>
        <div class="wag-status-pill">${__("These reactions arrived from BigQuery before we could resolve which group they belong to. Usually fixed by running Sync Groups.")}</div>
        <button class="btn btn-xs btn-default" id="wag-retry-sync-groups">${__("Run Sync Groups")}</button>
        <div class="wag-table-wrap" id="wag-retry-queue-table" style="margin-top:12px;"></div>
      </div>
    `).appendTo($backdrop);

    const close = () => $backdrop.remove();
    $backdrop.on("click", (e) => { if (e.target === $backdrop[0]) close(); });
    $drawer.find(".wag-person-drawer-close").on("click", close);
    $drawer.find("#wag-retry-sync-groups").on("click", () => this.pull_directory());

    const loadQueue = () => {
      this.call("list_reaction_retry_queue", { start: 0, page_length: 100 }).then((res) => {
        const $wrap = $drawer.find("#wag-retry-queue-table");
        $wrap.empty();
        if (!res.rows.length) {
          $wrap.html(`<div class="wag-empty">${__("Nothing queued.")}</div>`);
          return;
        }
        const $table = $(`
          <table class="wag-table">
            <thead><tr>
              <th>${__("Phone")}</th><th>${__("Reaction")}</th><th>${__("Message")}</th>
              <th>${__("Inserted")}</th><th>${__("Attempts")}</th><th></th>
            </tr></thead>
            <tbody></tbody>
          </table>
        `);
        const $tbody = $table.find("tbody");
        res.rows.forEach((r) => {
          const $tr = $(`
            <tr>
              <td>${this.esc(this.mask(r.phone || ""))}</td>
              <td>${this.esc(r.reaction || "")}</td>
              <td class="wag-td-wrap">${this.esc((r.body || "").slice(0, 80))}</td>
              <td>${frappe.datetime.str_to_user(r.inserted_at)}</td>
              <td>${r.retry_attempts}</td>
              <td><button class="btn btn-xs btn-default wag-retry-one">${__("Retry now")}</button></td>
            </tr>
          `);
          $tr.find(".wag-retry-one").on("click", () => {
            this.call("retry_one_queued_reaction", { name: r.name }).then((res2) => {
              frappe.show_alert({
                message: res2.status === "ok" ? __("Resolved") : __("Still unresolved"),
                indicator: res2.status === "ok" ? "green" : "orange",
              });
              loadQueue();
            });
          });
          $tbody.append($tr);
        });
        $wrap.append($table);
      });
    };
    loadQueue();
  }

  pagination_controls($panel, pagerId, state, onChange) {
    const $wrap = $(`
      <div class="wag-pagination-row">
        <select class="form-control input-sm wag-page-size-select" id="${pagerId}-size">
          <option value="10">10 / page</option>
          <option value="25">25 / page</option>
          <option value="50">50 / page</option>
          <option value="100">100 / page</option>
        </select>
        <button class="btn btn-xs btn-default" id="${pagerId}-more">${__("Load more")}</button>
      </div>
    `).appendTo($panel);
    $wrap.find(`#${pagerId}-size`).val(String(state.page_length)).on("change", (e) => {
      state.page_length = parseInt(e.target.value, 10);
      state.start = 0;
      onChange(false);
    });
    $wrap.find(`#${pagerId}-more`).hide().on("click", () => {
      state.start += state.page_length;
      onChange(true);
    });
    return $wrap;
  }

  render_polls() {
    const $panel = this.$root.find('[data-panel="polls"]').empty();
    const s = this.state.polls_tab;
    const g = this.state.geo;

    $panel.append(`<div class="wag-status-pill">${__("Polls are sent from the Send tab. This tab shows poll results and who voted what only.")}</div>`);
    const $cards = $(`<div class="wag-cards"></div>`).appendTo($panel);

    const $filters = $(`<div class="wag-toolbar"></div>`).appendTo($panel);
    const $pollSelect = $(`
      <select class="form-control input-sm" id="wag-polls-filter-poll">
        <option value="">${__("All polls")}</option>
      </select>
    `).on("change", (e) => {
      s.poll_uuid = e.target.value || null;
      s.start = 0;
      this.load_polls(false);
    });
    const $sortSelect = $(`
      <select class="form-control input-sm">
        <option value="sent_at">${__("Sort: Most Recent")}</option>
        <option value="response_rate">${__("Sort: Highest Response Rate")}</option>
        <option value="total_responses">${__("Sort: Most Responses")}</option>
      </select>
    `).val(s.sort_by).on("change", (e) => {
      s.sort_by = e.target.value;
      s.start = 0;
      this.load_polls(false);
    });
    $(`<button class="btn btn-xs btn-default">${__("Sync Poll Labels")}</button>`)
      .on("click", () => {
        this.call("sync_poll_labels").then((r) => {
          frappe.show_alert({ message: `${__("Synced")} ${r.synced || 0}`, indicator: "green" });
          this.load_poll_filter_options();
        });
      })
      .appendTo($filters);
    $filters.append($pollSelect, $sortSelect);

    if (this.state.geo.wa_group || this.state.geo.district || this.state.geo.city || this.state.geo.state || this.state.geo.school || this.state.geo.wa_group_collection) {
      $filters.append(`<span class="wag-status-pill">${__("Geo filter from the top bar also applies here.")}</span>`);
    }

    $panel.append(`<div class="wag-table-wrap" id="wag-polls-table"></div>`);
    this.pagination_controls($panel, "wag-polls-pager", s, (append) => this.load_polls(append));

    this.call("get_polls_overview", { ...this.date_range_args(), wa_group: g.wa_group, district: g.district, city: g.city, state: g.state, school: g.school, poll_uuid: s.poll_uuid }).then((d) => {
      $cards.empty();
      [
        { label: __("Total Polls Sent"), value: d.total_polls || 0 },
        { label: __("Total Responses"), value: d.total_responses || 0 },
        { label: __("Groups Targeted"), value: d.total_groups_targeted || 0 },
        { label: __("Avg Response Rate"), value: `${d.avg_response_rate || 0}%` },
      ].forEach((c) => {
        $cards.append(`
          <div class="wag-card">
            <div class="wag-card-value">${c.value}</div>
            <div class="wag-card-label">${c.label}</div>
          </div>
        `);
      });
    });

    this.load_poll_filter_options();
    s.start = 0;
    this.load_polls(false);
  }

  load_poll_filter_options() {
    const $select = this.$root.find("#wag-polls-filter-poll");
    if (!$select.length) return;
    this.call("list_wa_polls").then((polls) => {
      const current = this.state.polls_tab.poll_uuid || "";
      $select.find("option:not(:first)").remove();
      polls.forEach((p) => {
        $select.append(`<option value="${this.esc(p.uuid)}">${this.esc(p.label)}</option>`);
      });
      $select.val(current);
    });
  }

  load_polls(append) {
    const s = this.state.polls_tab;
    const g = this.state.geo;
    const $wrap = this.$root.find("#wag-polls-table");
    const $loadMore = this.$root.find("#wag-polls-pager-more");

    this.call("get_all_polls_summary", {
      ...this.date_range_args(),
      wa_group: g.wa_group, district: g.district, city: g.city, state: g.state, school: g.school,
      start: s.start, page_length: s.page_length,
    }).then((res) => {
      if (!append) $wrap.empty();
      if (!res.rows.length && !append) {
        $wrap.html(`<div class="wag-empty">${__("No polls sent in this range.")}</div>`);
        $loadMore.hide();
        return;
      }

      let $table = $wrap.find("table.wag-table");
      if (!$table.length) {
        $table = $(`
          <table class="wag-table">
            <thead><tr>
              <th>${__("Poll Label")}</th><th>${__("Sent At")}</th><th>${__("Target")}</th>
              <th>${__("Groups Targeted")}</th><th>${__("Total Responses")}</th>
              <th>${__("Response Rate")}</th><th>${__("Staff Replies")}</th><th></th>
            </tr></thead>
            <tbody></tbody>
          </table>
        `);
        $wrap.append($table);
      }
      const $tbody = $table.find("tbody");
      res.rows.forEach((r) => {
        const target = r.is_multi_language_poll ? __("Multi-language") : (r.wa_group_name || "");
        const $tr = $(`
          <tr>
            <td>${this.esc(r.label || "")}</td>
            <td>${frappe.datetime.str_to_user(r.sent_at)}</td>
            <td>${this.esc(target)}</td>
            <td>${r.groups_targeted}</td>
            <td>${r.total_responses}</td>
            <td>
              <div class="wag-poll-bar-track" style="display:inline-block;width:80px;vertical-align:middle;">
                <div class="wag-poll-bar-fill" style="width:${Math.min(r.response_rate, 100)}%;"></div>
              </div>
              <span style="margin-left:6px;">${r.response_rate}%</span>
            </td>
            <td>${r.staff_replies}</td>
            <td><button class="btn btn-xs btn-default wag-view-breakdown-btn">${__("View Breakdown")}</button></td>
          </tr>
          <tr class="wag-poll-breakdown-row" style="display:none;">
            <td colspan="8"><div class="wag-poll-results" id="wag-poll-breakdown-${r.campaign}"></div></td>
          </tr>
        `);
        $tr.first().find(".wag-view-breakdown-btn").on("click", () => this.toggle_poll_breakdown(r.campaign, $tr));
        $tbody.append($tr);
      });
      $loadMore.toggle(res.has_more);
    });
  }

  toggle_poll_breakdown(batch_name, $trPair) {
    const $row = $trPair.last();
    const $results = $row.find(`#wag-poll-breakdown-${batch_name}`);
    if ($row.is(":visible")) {
      $row.hide();
      return;
    }
    $row.show();
    $results.html(`<div class="wag-empty">${__("Loading...")}</div>`);
    this.call("get_campaign_poll_results", { batch_name }).then((res) => {
      $results.empty();
      if (!res.results.length) {
        $results.html(`<div class="wag-empty">${__("No poll responses captured yet.")}</div>`);
        return;
      }
      const maxCount = Math.max(...res.results.map((r) => r.count));
      $results.append(`<div class="wag-status-pill">${res.total_responses} ${__("responses total")}</div>`);
      res.results.forEach((r) => {
        const pct = maxCount ? Math.round((r.count / maxCount) * 100) : 0;
        $results.append(`
          <div class="wag-poll-bar-row">
            <span class="wag-poll-bar-label" title="${this.esc(r.option)}">${this.esc(r.option)}</span>
            <div class="wag-poll-bar-track"><div class="wag-poll-bar-fill" style="width:${pct}%;"></div></div>
            <span class="wag-poll-bar-count">${r.count}</span>
          </div>
        `);
      });
    });
  }

  render_campaigns() {
    const $panel = this.$root.find('[data-panel="campaigns"]').empty();
    const s = this.state.campaigns_tab;

    const $filters = $(`<div class="wag-toolbar"></div>`).appendTo($panel);
    const $statusSelect = $(`
      <select class="form-control input-sm">
        <option value="">${__("All statuses")}</option>
        <option value="Draft">${__("Draft")}</option>
        <option value="Scheduled">${__("Scheduled")}</option>
        <option value="Throttling">${__("Throttling")}</option>
        <option value="Sent">${__("Sent")}</option>
        <option value="Partially Failed">${__("Partially Failed")}</option>
        <option value="Failed">${__("Failed")}</option>
        <option value="Cancelled">${__("Cancelled")}</option>
      </select>
    `).val(s.send_status || "").on("change", (e) => {
      s.send_status = e.target.value || null;
      s.start = 0;
      this.load_campaign_stats(false);
    });
    $filters.append($statusSelect);

    $panel.append(`<div id="wag-campaign-list"></div>`);
    this.pagination_controls($panel, "wag-campaign-pager", s, (append) => this.load_campaign_stats(append));
    this.load_campaign_stats(false);
  }

  load_campaign_stats(append) {
    const s = this.state.campaigns_tab;
    const $wrap = this.$root.find("#wag-campaign-list");
    const $loadMore = this.$root.find("#wag-campaign-pager-more");

    this.call("list_send_batches", {
      filters: { send_status: s.send_status ? [s.send_status] : null },
      start: s.start, page_length: s.page_length,
    }).then((res) => {
      if (!append) $wrap.empty();
      if (!res.rows.length && !append) {
        $wrap.html(`<div class="wag-empty">${__("No sends yet.")}</div>`);
        $loadMore.hide();
        return;
      }
      res.rows.forEach((r) => this.render_campaign_card($wrap, r));
      $loadMore.toggle(res.has_more);
    });
  }

  render_campaign_card($wrap, r) {
    const mime = (r.media_url || "").toLowerCase();
    const isVideo = /\.(mp4|mov|webm)(\?|$)/.test(mime);
    const bodyHtml = r.message_body
      ? `<div class="wag-bubble wag-bubble-out"><span class="wag-bubble-text">${this.esc(r.message_body)}</span></div>`
      : "";
    let mediaHtml = "";
    if (r.media_url) {
      mediaHtml = isVideo
        ? `<video class="wag-campaign-media-thumb" controls preload="metadata" src="${this.esc(r.media_url)}" onerror="this.classList.add('wag-media-broken')"></video>`
        : `<img class="wag-campaign-media-thumb" src="${this.esc(r.media_url)}" loading="lazy" alt="" onerror="this.classList.add('wag-media-broken')">`;
    }

    const isInFlight = ["Scheduled", "Throttling"].includes(r.status);
    const progressHtml = isInFlight
      ? `<div class="wag-status-pill" id="wag-batch-progress-${r.name}">${__("Loading progress…")}</div>`
      : "";
    const editBtn = r.status === "Draft"
      ? `<button class="btn btn-xs btn-default wag-edit-draft-btn">${__("Edit Draft")}</button>`
      : "";
    const cancelBtn = ["Draft", "Scheduled", "Throttling"].includes(r.status)
      ? `<button class="btn btn-xs btn-default wag-cancel-batch-btn">${__("Cancel")}</button>`
      : "";

    const $card = $(`
      <div class="wag-campaign-card">
        <div class="wag-campaign-head">
          <span class="wag-campaign-title">${this.esc(r.target_label || r.name)}</span>
          ${this.badge(r.send_kind, "neutral")}
          ${this.badge(r.status, this.status_color(r.status))}
          <span class="wag-campaign-meta">${r.scheduled_send_at ? frappe.datetime.str_to_user(r.scheduled_send_at) : ""}</span>
          ${r.send_kind === "Poll" ? `<button class="btn btn-xs btn-default wag-view-poll-btn">${__("View poll results")}</button>` : ""}
          ${editBtn}
          ${cancelBtn}
        </div>
        ${bodyHtml}
        ${mediaHtml}
        ${progressHtml}
        <div class="wag-campaign-stats">
          <div class="wag-campaign-stat">
            <div class="wag-campaign-stat-value">${r.total_groups || 0}</div>
            <div class="wag-campaign-stat-label">${__("Groups Targeted")}</div>
          </div>
          <div class="wag-campaign-stat">
            <div class="wag-campaign-stat-value">${r.sent_count || 0}</div>
            <div class="wag-campaign-stat-label">${__("Sent")}</div>
          </div>
          <div class="wag-campaign-stat">
            <div class="wag-campaign-stat-value">${r.failed_count || 0}</div>
            <div class="wag-campaign-stat-label">${__("Failed")}</div>
          </div>
        </div>
        <div class="wag-poll-results" id="wag-poll-results-${r.name}"></div>
        <div class="wag-chip-row" id="wag-campaign-reactions-${r.name}" style="margin-top:4px;"></div>
      </div>
    `);

    if (r.media_url && !isVideo) {
      $card.find(".wag-campaign-media-thumb").on("click", () => this.open_lightbox(r.media_url));
    }
    if (r.send_kind === "Poll") {
      $card.find(".wag-view-poll-btn").on("click", () => this.toggle_poll_results(r.name, $card));
    }
    $card.find(".wag-edit-draft-btn").on("click", () => {
      this.state.send_draft_loaded = r.name;
      this.switch_tab("send");
    });
    $card.find(".wag-cancel-batch-btn").on("click", () => {
      frappe.confirm(__("Cancel this send? Already-sent waves stay sent."), () => {
        this.call("cancel_send_batch", { batch_name: r.name }).then(() => {
          frappe.show_alert({ message: __("Cancelled"), indicator: "orange" });
          this.load_campaign_stats(false);
        });
      });
    });
    if (r.sent_count) {
      this.call("reactions_for_campaign", { batch_name: r.name }).then((rows) => {
        if (!rows || !rows.length) return;
        const chips = rows.map((rx) =>
          `<span class="wag-chip">${rx.reaction_emoji} ${this.esc(this.mask(rx.contact_phone || ""))} <span class="wag-chip-count">${__("on our send")}</span></span>`
        ).join(" ");
        $card.find(`#wag-campaign-reactions-${r.name}`).html(chips);
      });
    }
    if (isInFlight) this.watch_batch_progress(r.name, $card);
    $wrap.append($card);
  }

  watch_batch_progress(batch_name, $card) {
    const update = () => {
      if (!document.body.contains($card[0])) return;
      this.call("get_send_batch_progress", { batch_name }).then((p) => {
        const $pill = $card.find(`#wag-batch-progress-${batch_name}`);
        if (!$pill.length) return;
        if (!["Scheduled", "Throttling"].includes(p.status)) {
          $pill.remove();
          this.load_campaign_stats(false);
          return;
        }
        const waveLabel = p.waves_total
          ? `${__("Wave")} ${(p.waves_sent || 0) + 1}/${p.waves_total}`
          : __("Preparing wave");
        const nextIn = p.next_wave_at ? this.time_until_label(p.next_wave_at) : "";
        $pill.text(`${waveLabel} · ${p.sent_count || 0}/${p.total_groups || 0} ${__("groups done")}${nextIn ? " · " + nextIn : ""}`);
        setTimeout(update, 15000);
      });
    };
    update();
  }

  time_until_label(datetimeStr) {
    const target = frappe.datetime.str_to_obj(datetimeStr).getTime();
    const diffMs = target - Date.now();
    if (diffMs <= 0) return __("sending shortly");
    const mins = Math.floor(diffMs / 60000);
    const secs = Math.floor((diffMs % 60000) / 1000);
    return `${__("next wave in")} ${mins}m ${secs}s`;
  }

  toggle_poll_results(batch_name, $card) {
    const $results = $card.find(`#wag-poll-results-${batch_name}`);
    if ($results.hasClass("open")) {
      $results.removeClass("open");
      return;
    }
    $results.addClass("open").html(`<div class="wag-empty">${__("Loading...")}</div>`);
    this.call("get_campaign_poll_results", { batch_name }).then((res) => {
      $results.empty();
      if (!res.results.length) {
        $results.html(`<div class="wag-empty">${__("No poll responses captured yet.")}</div>`);
        return;
      }
      const maxCount = Math.max(...res.results.map((r) => r.count));
      $results.append(`<div class="wag-status-pill">${res.total_responses} ${__("responses total")}</div>`);
      res.results.forEach((r) => {
        const pct = maxCount ? Math.round((r.count / maxCount) * 100) : 0;
        $results.append(`
          <div class="wag-poll-bar-row">
            <span class="wag-poll-bar-label" title="${this.esc(r.option)}">${this.esc(r.option)}</span>
            <div class="wag-poll-bar-track"><div class="wag-poll-bar-fill" style="width:${pct}%;"></div></div>
            <span class="wag-poll-bar-count">${r.count}</span>
          </div>
        `);
      });
    });
  }

  render_conversations() {
    const $panel = this.$root.find('[data-panel="conversations"]').empty();
    const s = this.state.conversations_tab;

    $panel.append(`<div class="wag-summary-bar" id="wag-conv-summary"></div>`);
    this.load_conversations_summary();

    const $filters = $(`<div class="wag-toolbar"></div>`).appendTo($panel);

    const $modeToggle = $(`
      <div class="wag-mode-toggle">
        <button class="wag-mode-btn ${s.view_mode === "groups" ? "active" : ""}" data-mode="groups">${__("Groups")}</button>
        <button class="wag-mode-btn ${s.view_mode === "people" ? "active" : ""}" data-mode="people">${__("People")}</button>
      </div>
    `).appendTo($filters);
    $modeToggle.find(".wag-mode-btn").on("click", (e) => {
      s.view_mode = $(e.currentTarget).data("mode");
      s.selected_phone = null;
      s.selected_group = null;
      this.render_conversations();
    });

    const currentStatus = Array.isArray(s.turn_status) && s.turn_status.length === 1 ? s.turn_status[0] : "";
    const $statusSelect = $(`
      <select class="form-control input-sm">
        <option value="">${__("Open + Drafted (default)")}</option>
        <option value="Open">${__("Open")}</option>
        <option value="Drafted">${__("Drafted")}</option>
        <option value="Ready To Go">${__("Ready To Go")}</option>
        <option value="Sent">${__("Sent")}</option>
        <option value="Failed">${__("Failed")}</option>
        <option value="Ignored">${__("Ignored")}</option>
        <option value="Discarded">${__("Discarded")}</option>
      </select>
    `).val(currentStatus).on("change", (e) => {
      s.turn_status = e.target.value ? [e.target.value] : ["Open", "Drafted"];
      s.start = 0;
      this.load_conversations_panel(false);
    });
    $filters.append($statusSelect);

    if (s.tag) {
      const $tagPill = $(`<span class="wag-chip active">${__("Tag")}: ${this.esc(s.tag)} ✕</span>`)
        .on("click", () => {
          s.tag = null;
          s.turn_status = ["Open", "Drafted"];
          this.render_conversations();
        });
      $filters.append($tagPill);
    }

    const $discardAllBtn = $(`<button class="btn btn-xs btn-default wag-discard-all-btn">${__("Discard All (filtered)")}</button>`)
      .on("click", () => this.discard_all_filtered());
    $filters.append($discardAllBtn);

    if (this.state.geo.wa_group) {
      $panel.append(`<div id="wag-conv-group-members"></div>`);
      this.load_group_members(this.state.geo.wa_group);
    }

    const $grid = $(`
      <div class="wag-convo-grid">
        <div class="wag-convo-list" id="wag-convo-list"></div>
        <div class="wag-convo-detail" id="wag-convo-detail">
          <div class="wag-convo-empty">${__("Select a conversation to see the full thread.")}</div>
        </div>
      </div>
    `).appendTo($panel);

    this.pagination_controls($panel, "wag-conv-pager", s, (append) => this.load_conversations_panel(append));
    this.load_conversations_panel(false);
  }

  load_conversations_panel(append) {
    const s = this.state.conversations_tab;
    if (s.view_mode === "groups" && !s.selected_group) {
      this.load_conversation_groups(append);
    } else if (s.view_mode === "groups" && s.selected_group) {
      return;
    } else {
      this.load_conversations(append);
    }
  }

  discard_all_filtered() {
    const s = this.state.conversations_tab;
    frappe.confirm(
      __("Discard every conversation matching the current filters? This cannot be undone."),
      () => {
        this.call("discard_all_turns", {
          filters: this.filters_for("conversations"),
        }).then((r) => {
          frappe.show_alert({ message: `${__("Discarded")}: ${r.discarded || 0}`, indicator: "green" });
          this.load_conversations_summary();
          this.load_conversations_panel(false);
          this.refresh_tab_counters();
        });
      }
    );
  }

  load_conversations_summary() {
    const s = this.state.conversations_tab;

    this.call("get_conversations_summary", {
      filters: this.filters_for("conversations"),
      include_poll_only: false,
    }).then((counts) => {
      const $bar = this.$root.find("#wag-conv-summary");
      $bar.empty();
      const scheduled = counts["Ready To Go"] || 0;
      const entries = [
        ["Open", counts.Open || 0],
        ["Drafted", counts.Drafted || 0],
        ["Scheduled", scheduled],
        ["Sent", counts.Sent || 0],
        ["Failed", counts.Failed || 0],
        ["Ignored", counts.Ignored || 0],
      ];
      const activeSet = new Set(Array.isArray(s.turn_status) ? s.turn_status : [s.turn_status]);
      entries.forEach(([key, val]) => {
        const matchKey = key === "Scheduled" ? "Ready To Go" : key;
        $(`
          <div class="wag-summary-chip" data-status="${key}" data-active="${activeSet.has(matchKey)}">
            <span class="wag-summary-chip-value">${val}</span>
            <span class="wag-summary-chip-label">${__(key)}</span>
          </div>
        `).on("click", () => {
          s.turn_status = [matchKey];
          s.start = 0;
          this.render_conversations();
        }).appendTo($bar);
      });

      const $sendAllBtn = $(`<button class="btn btn-xs btn-success wag-send-all-ready">${__("Send All Ready")} (${scheduled})</button>`);
      $sendAllBtn.prop("disabled", !scheduled).on("click", () => {
        $sendAllBtn.prop("disabled", true).text(__("Sending..."));
        this.call("send_all_ready").then((r) => {
          frappe.show_alert({ message: `${__("Sent")}: ${r.sent}, ${__("Failed")}: ${r.failed}`, indicator: r.failed ? "orange" : "green" });
          this.load_conversations_summary();
          this.load_conversations_panel(false);
          this.refresh_tab_counters();
        });
      });
      $bar.append($sendAllBtn);
    });
  }

  load_group_members(wa_group) {
    const $wrap = this.$root.find("#wag-conv-group-members");
    const render = (rows) => {
      $wrap.empty();
      if (!rows.length) {
        $wrap.append(`
          <div class="wag-status-pill">
            ${__("No matched teachers or students in this group yet.")}
            <button class="btn btn-xs btn-default wag-refresh-members">${__("Refresh")}</button>
          </div>
        `);
      } else {
        const chips = rows.map((r) =>
          `<span class="wag-chip">${r.member_type === "Teacher" ? "👩‍🏫" : "🎓"} ${this.esc(this.mask(r.member_name || r.phone_number || ""))}</span>`
        ).join(" ");
        $wrap.append(`<div class="wag-chip-row">${chips} <button class="btn btn-xs btn-default wag-refresh-members">${__("Refresh")}</button></div>`);
      }
      $wrap.find(".wag-refresh-members").on("click", () => {
        $wrap.html(`<div class="wag-status-pill">${__("Refreshing...")}</div>`);
        this.call("refresh_group_members", { wa_group }).then((result) => {
          this.call("get_group_members", { wa_group }).then((rows2) => {
            render(rows2);
            if (result && typeof result.matched === "number") {
              frappe.show_alert({
                message: `${__("Matched")} ${result.matched} / ${result.turn_phones_seen || 0} ${__("contacts")}`,
                indicator: result.matched ? "green" : "orange",
              });
            }
          });
        });
      });
    };
    this.call("get_group_members", { wa_group }).then(render);
  }

  load_conversation_groups(append) {
    const s = this.state.conversations_tab;
    const $list = this.$root.find("#wag-convo-list");
    const $loadMore = this.$root.find("#wag-conv-pager-more");

    this.call("get_conversation_groups", {
      filters: this.filters_for("conversations"),
      start: s.start, page_length: s.page_length,
    }).then((res) => {
      if (!append) $list.empty();
      if (!res.rows.length && !append) {
        $list.html(`<div class="wag-empty">${__("No group activity in this queue.")}</div>`);
        $loadMore.hide();
        return;
      }
      res.rows.forEach((r) => this.render_convo_group_row($list, r));
      $loadMore.toggle(res.has_more);
    });
  }

  render_convo_group_row($list, r) {
    const initial = (r.group_name || r.wa_group || "?").trim().charAt(0).toUpperCase();
    const needsAttention = (r.needs_attention || 0) > 0;
    const $row = $(`
      <div class="wag-convo-row ${needsAttention ? "wag-convo-row-unread" : ""}" data-group="${this.esc(r.wa_group)}">
        <div class="wag-convo-row-avatar">${initial}</div>
        <div class="wag-convo-row-body">
          <div class="wag-convo-row-top">
            <span class="wag-convo-row-name">${this.esc(r.group_name || r.wa_group)}</span>
            <span class="wag-convo-row-time">${frappe.datetime.str_to_user(r.last_activity)}</span>
          </div>
          <div class="wag-convo-row-top">
            <span class="wag-convo-row-preview">${r.turn_count} ${__("conversations")}</span>
            ${needsAttention ? `<span class="wag-badge wag-badge-pending">${r.needs_attention}</span>` : ""}
          </div>
        </div>
      </div>
    `).on("click", () => {
      this.state.conversations_tab.selected_group = r.wa_group;
      this.state.conversations_tab.start = 0;
      this.state.conversations_tab.group_timeline_mode = "all";
      this.render_group_detail_view(r.wa_group, r.group_name);
    });
    $list.append($row);
  }

  render_group_detail_view(wa_group, group_name) {
    const $list = this.$root.find("#wag-convo-list");
    $list.empty();
    $list.append(`
      <div class="wag-convo-row-back" id="wag-convo-back-to-groups">
        ← ${__("Back to groups")} — ${this.esc(group_name || wa_group)}
      </div>
    `);
    $list.find("#wag-convo-back-to-groups").on("click", () => {
      this.state.conversations_tab.selected_group = null;
      this.render_conversations();
    });

    const s = this.state.conversations_tab;
    const $modeRow = $(`
      <div class="wag-mode-toggle" style="margin:0 10px 10px;">
        <button class="wag-mode-btn ${s.group_timeline_mode === "all" ? "active" : ""}" data-gmode="all">${__("All")}</button>
        <button class="wag-mode-btn ${s.group_timeline_mode === "people" ? "active" : ""}" data-gmode="people">${__("By Person")}</button>
      </div>
    `).appendTo($list);
    $modeRow.find(".wag-mode-btn").on("click", (e) => {
      s.group_timeline_mode = $(e.currentTarget).data("gmode");
      this.render_group_detail_view(wa_group, group_name);
    });

    $list.append(`<div id="wag-group-detail-list"></div>`);
    const $detailList = $list.find("#wag-group-detail-list");

    if (s.group_timeline_mode === "all") {
      this.render_group_timeline(wa_group, group_name);
      $detailList.hide();
      return;
    }

    this.$root.find("#wag-convo-detail").html(`<div class="wag-convo-empty">${__("Select a conversation to see the full thread.")}</div>`);

    this.call("get_conversation_turns", {
      filters: { ...this.filters_for("conversations"), geo: { wa_group } },
      start: 0, page_length: 100,
      include_poll_only: false,
    }).then((res) => {
      const grouped = this.group_turns_by_contact(res.rows);
      $detailList.empty();
      if (!grouped.length) {
        $detailList.append(`<div class="wag-empty">${__("Nothing in this queue.")}</div>`);
        return;
      }
      grouped.forEach((entry) => this.render_convo_row($detailList, entry));
    });
  }

  render_group_timeline(wa_group, group_name) {
    const $detail = this.$root.find("#wag-convo-detail").empty();
    const $head = $(`
      <div class="wag-convo-detail-head">
        <div class="wag-convo-row-avatar">${(group_name || wa_group || "?").trim().charAt(0).toUpperCase()}</div>
        <div>
          <div class="wag-convo-detail-name">${this.esc(group_name || wa_group)}</div>
          <div class="wag-convo-detail-sub">${__("Full group timeline")}</div>
        </div>
      </div>
      <div class="wag-convo-thread" id="wag-group-timeline-thread"></div>
    `);
    $detail.append($head);

    const $thread = $detail.find("#wag-group-timeline-thread");
    $thread.html(`<div class="wag-empty" id="wag-timeline-loading">${__("Loading group timeline...")}</div>`);

    const pageLength = 60;
    let nextStart = 0;
    let hasMore = false;

    this.call("get_group_timeline", { wa_group, start: 0, page_length: pageLength }).then((res) => {
      $thread.empty();
      hasMore = !!res.has_more;
      nextStart = pageLength;

      const $loadEarlier = $(`
        <button class="btn btn-xs btn-default wag-load-earlier-btn">${__("Load earlier messages")}</button>
      `).toggle(hasMore);
      $thread.append($loadEarlier);

      this.render_group_timeline_entries($thread, res.rows, res.replies, false);

      $loadEarlier.on("click", () => {
        $loadEarlier.prop("disabled", true).text(__("Loading..."));
        this.call("get_group_timeline", { wa_group, start: nextStart, page_length: pageLength }).then((res2) => {
          nextStart += pageLength;
          hasMore = !!res2.has_more;
          this.render_group_timeline_entries($thread, res2.rows, res2.replies, true);
          $loadEarlier.toggle(hasMore).prop("disabled", false).text(__("Load earlier messages"));
        });
      });

      this.attach_thread_autoscroll($thread);
      this.pin_thread_to_bottom($thread);
    });
  }

  render_group_timeline_entries($thread, itemRows, replyRows, prepend) {
    const entries = [];
    (itemRows || []).forEach((r) => {
      const items = this.safe_parse_items([{
        bq_id: r.bq_id, item_type: r.item_type, body: r.body, tagged_user_id: r.tagged_user_id,
        media_gcs_url: r.media_gcs_url, media_mime_type: r.media_mime_type, poll_choice: r.poll_choice,
        transcript: r.transcript, occurred_at: r.occurred_at,
      }]);
      items.forEach((it) => {
        if (!this.has_real_content(it)) return;
        entries.push({
          ts: it.occurred_at, turnName: r.turn_name,
          senderLabel: this.mask(r.contact_display || r.contact_phone || ""),
          item: it,
        });
      });
    });
    (replyRows || []).forEach((r) => {
      entries.push({
        ts: r.sent_at, isReply: true, body: r.message_body,
      });
    });

    entries.sort((a, b) => new Date(a.ts) - new Date(b.ts));

    let lastDay = null;
    const $batch = $(document.createDocumentFragment());
    entries.forEach((entry) => {
      const dayLabel = entry.ts ? this.day_label_for(entry.ts) : __("Today");
      if (dayLabel !== lastDay) {
        $batch.append(`<div class="wag-status-pill wag-convo-day-sep">${dayLabel}</div>`);
        lastDay = dayLabel;
      }
      if (entry.isReply) {
        $batch.append(`
          <div class="wag-bubble wag-bubble-out">
            <span class="wag-bubble-text">${this.esc(entry.body || "")}</span>
          </div>
        `);
      } else {
        const html = this.render_turn_item_with_sender(entry.item, entry.turnName, entry.senderLabel);
        if (html) $batch.append(html);
      }
    });

    if (prepend) {
      const prevHeight = $thread[0].scrollHeight;
      const prevScrollTop = $thread[0].scrollTop;
      $thread.find(".wag-load-earlier-btn").after($batch);
      $thread.scrollTop($thread[0].scrollHeight - prevHeight + prevScrollTop);
    } else {
      $thread.append($batch);
      this.pin_thread_to_bottom($thread);
    }
  }

  load_conversations(append) {
    const s = this.state.conversations_tab;
    const $list = this.$root.find("#wag-convo-list");
    const $loadMore = this.$root.find("#wag-conv-pager-more");

    this.call("get_conversation_turns", {
      filters: this.filters_for("conversations"),
      start: s.start,
      page_length: s.page_length,
      include_poll_only: false,
    }).then((res) => {
      if (!append) $list.empty();
      const grouped = this.group_turns_by_contact(res.rows);
      if (!grouped.length && !append) {
        $list.html(`<div class="wag-empty">${__("Nothing in this queue.")}</div>`);
        $loadMore.hide();
        return;
      }
      grouped.forEach((entry) => this.render_convo_row($list, entry));
      $loadMore.toggle(res.has_more);
    });
  }

  group_turns_by_contact(rows) {
    const byPhone = new Map();
    const order = [];
    rows.forEach((r) => {
      const key = `${r.wa_group}-${r.contact_phone}`;
      if (!byPhone.has(key)) {
        byPhone.set(key, { ...r, turn_count: 1 });
        order.push(key);
      } else {
        const existing = byPhone.get(key);
        existing.turn_count += 1;
        if (new Date(r.last_item_at) > new Date(existing.last_item_at)) {
          Object.assign(existing, r, { turn_count: existing.turn_count });
        }
      }
    });
    return order.map((k) => byPhone.get(k)).sort((a, b) => new Date(b.last_item_at) - new Date(a.last_item_at));
  }

  row_tags_me(r) {
    if (this.message_tags_me((r.ai_tags || ""))) return false;
    const items = this.safe_parse_items(r.turn_items);
    return items.some((it) => this.message_tags_me(it.body));
  }

  render_convo_row($list, r) {
    const items = this.safe_parse_items(r.turn_items);
    const preview = this.turn_item_preview(items);
    const displayName = this.mask(r.contact_display || r.contact_phone || "");
    const initial = (displayName || "?").trim().charAt(0).toUpperCase();
    const needsAttention = ["Open", "Failed"].includes(r.turn_status);
    const isActive = this.state.conversations_tab.selected_phone === r.contact_phone;
    const taggedMe = this.row_tags_me(r);

    const $row = $(`
      <div class="wag-convo-row ${needsAttention ? "wag-convo-row-unread" : ""} ${isActive ? "active" : ""}" data-phone="${this.esc(r.contact_phone)}">
        <div class="wag-convo-row-avatar">${initial}</div>
        <div class="wag-convo-row-body">
          <div class="wag-convo-row-top">
            <span class="wag-convo-row-name">${this.esc(displayName)} ${taggedMe ? `<span class="wag-row-tag-icon" title="${this.tag_display_label()}">🏷️</span>` : ""}</span>
            <span class="wag-convo-row-time">${frappe.datetime.str_to_user(r.last_item_at)}</span>
          </div>
          <div class="wag-convo-row-top">
            <span class="wag-convo-row-preview">${preview}</span>
            <span class="wag-status-dot wag-status-dot-${this.turn_status_color(r.turn_status)}"></span>
          </div>
          <div class="wag-convo-row-group">${this.esc(r.wa_group_name || r.wa_group || "")}</div>
        </div>
      </div>
    `).on("click", () => {
      this.$root.find(".wag-convo-row").removeClass("active");
      $row.addClass("active");
      this.state.conversations_tab.selected_phone = r.contact_phone;
      this.render_convo_detail(r);
    });

    $list.append($row);
  }

  render_convo_detail(turnRow) {
    const $detail = this.$root.find("#wag-convo-detail").empty();

    const $head = $(`
      <div class="wag-convo-detail-head">
        <div class="wag-convo-row-avatar">${(this.mask(turnRow.contact_display || "?") || "?").charAt(0).toUpperCase()}</div>
        <div>
          <div class="wag-convo-detail-name">${this.esc(this.mask(turnRow.contact_display || turnRow.contact_phone || ""))}</div>
          <div class="wag-convo-detail-sub">${this.esc(this.mask(turnRow.contact_phone || ""))} · ${this.esc(turnRow.wa_group_name || turnRow.wa_group || "")}</div>
        </div>
      </div>
      <div class="wag-convo-tags" id="wag-convo-tags"></div>
      <div class="wag-convo-thread" id="wag-convo-thread"></div>
      <div class="wag-convo-composer wag-convo-composer-sticky" id="wag-convo-composer"></div>
    `);
    $detail.append($head);

    this.render_full_thread_for_contact($detail.find("#wag-convo-thread"), $detail.find("#wag-convo-tags"), turnRow);
    this.render_convo_composer($detail.find("#wag-convo-composer"), turnRow);
    this.attach_composer_resize_observer($detail);
  }

  attach_composer_resize_observer($detail) {
    const $thread = $detail.find("#wag-convo-thread");
    const $composer = $detail.find("#wag-convo-composer");
    if (!$thread.length || !$composer.length || typeof ResizeObserver === "undefined") return;
    const apply = () => {
      const h = $composer[0].getBoundingClientRect().height || 48;
      $thread.css("padding-bottom", `${h + 10}px`);
    };
    apply();
    const observer = new ResizeObserver(() => apply());
    observer.observe($composer[0]);
    if (this._composerObserver) this._composerObserver.disconnect();
    this._composerObserver = observer;
  }

  is_thread_near_bottom($thread) {
    const el = $thread[0];
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }

  pin_thread_to_bottom($thread) {
    const el = $thread[0];
    if (el) el.scrollTop = el.scrollHeight;
  }

  attach_thread_autoscroll($thread) {
    if (typeof ResizeObserver === "undefined") return;
    const el = $thread[0];
    if (!el) return;

    let userHasScrolledUp = false;
    $thread.off("scroll.wagAutoscroll").on("scroll.wagAutoscroll", () => {
      userHasScrolledUp = !this.is_thread_near_bottom($thread);
    });

    const observer = new ResizeObserver(() => {
      if (!userHasScrolledUp) this.pin_thread_to_bottom($thread);
    });
    observer.observe(el);

    if (this._threadObserver) this._threadObserver.disconnect();
    this._threadObserver = observer;
  }

  day_label_for(dt) {
    const d = frappe.datetime.str_to_obj(dt);
    const today = frappe.datetime.str_to_obj(frappe.datetime.now_date());
    const diffDays = frappe.datetime.get_day_diff(frappe.datetime.obj_to_str(d), frappe.datetime.obj_to_str(today));
    if (diffDays === 0) return __("Today");
    if (diffDays === 1) return __("Yesterday");
    return frappe.datetime.str_to_user(frappe.datetime.obj_to_str(d)).split(" ")[0];
  }

  build_thread_entries(turns, contactPhone) {
    const entries = [];
    const allTags = new Set();
    let taggedMeInThread = false;
    turns.forEach((t) => {
      const items = this.safe_parse_items(t.turn_items);
      this.visible_turn_items(items).forEach((it) => {
        if (this.message_tags_me(it.body)) taggedMeInThread = true;
        entries.push({ kind: "item", item: it, turnName: t.name, ts: it.occurred_at || t.last_item_at });
      });
      (t.ai_tags || "").split(",").map((x) => x.trim()).filter(Boolean).forEach((tag) => allTags.add(tag));
      (t.replies || []).forEach((reply) => {
        entries.push({ kind: "reply", reply, turnName: t.name, ts: reply.sent_at });
      });
      if (t.ai_reply && t.turn_status === "Sent" && !(t.replies || []).length) {
        entries.push({ kind: "reply", reply: { body_sent: t.ai_reply, sent_at: t.last_item_at }, turnName: t.name, ts: t.last_item_at });
      }
    });

    const local = this.localReplies.forContact(contactPhone);
    const existingBodies = new Set(entries.filter((e) => e.kind === "reply").map((e) => `${e.reply.body_sent}`));
    local.forEach((r) => {
      if (existingBodies.has(r.body)) return;
      entries.push({ kind: "reply", reply: { body_sent: r.body, sent_at: null, pending: true }, turnName: r.turn, ts: new Date(r.ts).toISOString() });
    });

    if (taggedMeInThread) allTags.add("tagged_me");

    entries.sort((a, b) => {
      const ta = a.ts ? new Date(a.ts).getTime() : 0;
      const tb = b.ts ? new Date(b.ts).getTime() : 0;
      return ta - tb;
    });
    return { entries, tags: [...allTags], taggedMe: taggedMeInThread };
  }

  render_thread_entries($thread, entries, prepend) {
    let lastDay = null;
    const $batch = $(document.createDocumentFragment());

    entries.forEach((entry) => {
      const dayLabel = entry.ts ? this.day_label_for(entry.ts) : __("Today");
      if (dayLabel !== lastDay) {
        $batch.append(`<div class="wag-status-pill wag-convo-day-sep">${dayLabel}</div>`);
        lastDay = dayLabel;
      }
      if (entry.kind === "item") {
        const html = this.render_turn_item(entry.item, entry.turnName);
        if (html) $batch.append(html);
      } else {
        const reply = entry.reply;
        $batch.append(`
          <div class="wag-bubble wag-bubble-out${reply.pending ? " wag-bubble-pending" : ""}">
            <span class="wag-bubble-text">${this.esc(reply.body_sent || "")}</span>
            ${reply.pending ? `<div class="wag-bubble-caption">${__("sending…")}</div>` : ""}
          </div>
        `);
      }
    });

    if (prepend) {
      const prevHeight = $thread[0].scrollHeight;
      const prevScrollTop = $thread[0].scrollTop;
      $thread.find(".wag-load-earlier-btn").after($batch);
      $thread.scrollTop($thread[0].scrollHeight - prevHeight + prevScrollTop);
    } else {
      $thread.append($batch);
      this.pin_thread_to_bottom($thread);
    }
  }

  render_full_thread_for_contact($thread, $tagsWrap, turnRow) {
    $thread.empty();
    $thread.append(`<div class="wag-empty" id="wag-thread-loading">${__("Loading conversation...")}</div>`);

    const pageLength = 30;
    let nextStart = 0;
    let hasMore = false;

    this.call("get_person_turns", { contact_phone: turnRow.contact_phone, start: 0, page_length: pageLength }).then((res) => {
      $thread.empty();
      hasMore = !!res.has_more;
      nextStart = pageLength;

      const $loadEarlier = $(`
        <button class="btn btn-xs btn-default wag-load-earlier-btn">
          ${__("Load earlier messages")}
        </button>
      `).toggle(hasMore);

      $thread.append($loadEarlier);
      const built = this.build_thread_entries(res.rows, turnRow.contact_phone);
      this.render_thread_entries($thread, built.entries, false);
      $tagsWrap.html(this.render_tags_row(built.tags.join(","), built.taggedMe));

      $loadEarlier.on("click", () => {
        $loadEarlier.prop("disabled", true).text(__("Loading..."));
        this.call("get_person_turns", { contact_phone: turnRow.contact_phone, start: nextStart, page_length: pageLength }).then((res2) => {
          nextStart += pageLength;
          hasMore = !!res2.has_more;
          const earlierBuilt = this.build_thread_entries(res2.rows, turnRow.contact_phone);
          this.render_thread_entries($thread, earlierBuilt.entries, true);
          $loadEarlier.toggle(hasMore).prop("disabled", false).text(__("Load earlier messages"));
        });
      });

      this.attach_reaction_badges($thread, turnRow);
      this.attach_thread_autoscroll($thread);
      this.pin_thread_to_bottom($thread);
    });
  }

  attach_reaction_badges($thread, turnRow) {
    this.call("reactions_for_turn", { turn_name: turnRow.name }).then((rows) => {
      (rows || []).forEach((rx) => {
        const $bubble = $thread.find(`[data-bq-id="${rx.reacted_message_bq_id}"]`).first();
        if ($bubble.length) {
          const badge = `<span class="wag-reaction-badge" title="${this.esc(this.mask(rx.contact_phone || ""))}">${rx.reaction_emoji}</span>`;
          $bubble.append(badge);
        }
      });
    });

    if (turnRow.turn_status === "Sent") {
      this.call("get_reply_for_turn", { turn_name: turnRow.name }).then((reply) => {
        if (!reply || !reply.name) return;
        this.call("reactions_for_reply", { reply_name: reply.name }).then((rows) => {
          if (!rows || !rows.length) return;
          const chips = rows.map((rx) =>
            `<span class="wag-chip">${rx.reaction_emoji} ${this.esc(this.mask(rx.contact_phone || ""))} <span class="wag-chip-count">${__("on our reply")}</span></span>`
          ).join(" ");
          $thread.append(`<div class="wag-chip-row" style="margin-top:4px;">${chips}</div>`);
        });
      });
    }
  }

  render_convo_composer($composer, r) {
    $composer.empty();

    if (r.turn_status === "Sent" || r.turn_status === "Discarded") {
      this.build_followup_composer($composer, r);
      return;
    }

    if (r.turn_status === "Ignored") {
      const $link = $(`<a href="#" class="wag-reply-anyway-link">${__("Reply anyway?")}</a>`);
      $composer.append($link);
      $link.on("click", (e) => {
        e.preventDefault();
        this.build_active_composer($composer, r, "");
      });
      return;
    }

    this.build_active_composer($composer, r, r.ai_reply || "");
  }

  build_followup_composer($composer, r) {
    const $row = $(`<div class="wag-composer-row"></div>`);
    const $input = $(`<input type="text" class="form-control wag-convo-composer-input wag-convo-composer-input-compact" placeholder="${__("Message")}">`);
    const $send = $(`<button class="btn btn-xs btn-success">${__("Send")}</button>`);
    $row.append($input, $send);
    $composer.append($row);

    let sending = false;
    const send = () => {
      if (sending) return;
      const text = $input.val().trim();
      if (!text) return;
      sending = true;
      $send.prop("disabled", true);
      this.send_tracked_reply(r.name, r.contact_phone, text, () => {
        $input.val("");
        sending = false;
        $send.prop("disabled", false);
        this.render_convo_detail(r);
      });
    };
    $send.on("click", send);
    $input.on("keydown", (e) => { if (e.key === "Enter") send(); });
  }

  send_tracked_reply(turnName, contactPhone, text, onDone) {
    this.localReplies.add(contactPhone, turnName, text);
    const $thread = this.$root.find("#wag-convo-thread");
    if ($thread.length) {
      $thread.append(`
        <div class="wag-bubble wag-bubble-out wag-bubble-pending">
          <span class="wag-bubble-text">${this.esc(text)}</span>
          <div class="wag-bubble-caption">${__("sending…")}</div>
        </div>
      `);
      this.pin_thread_to_bottom($thread);
    }
    this.call("send_manual_reply", { turn_name: turnName, reply_text: text }).then(() => {
      frappe.show_alert({ message: __("Sent"), indicator: "green" });
      if (onDone) onDone();
      this.load_conversations_panel(false);
      this.load_conversations_summary();
      this.refresh_tab_counters();
    }).fail(() => {
      frappe.show_alert({ message: __("Send failed"), indicator: "red" });
    });
  }

  build_active_composer($composer, r, prefill) {
    $composer.empty();

    const editable = ["Open", "Drafted", "Ready To Go", "Failed"].includes(r.turn_status);
    const canApprove = r.turn_status === "Drafted";
    const canRetry = r.turn_status === "Failed";

    if (r.turn_status === "Failed" && r.ai_last_error) {
      $composer.append(`<div class="wag-convo-error">${this.esc(r.ai_last_error)}</div>`);
    }
    if (r.turn_status === "Ready To Go" && r.scheduled_send_after) {
      $composer.append(`<div class="wag-status-pill">${__("Sending after")} ${frappe.datetime.str_to_user(r.scheduled_send_after)}</div>`);
    }

    const $row = $(`<div class="wag-composer-row"></div>`);
    const $input = $(`<input type="text" class="form-control wag-convo-composer-input wag-convo-composer-input-compact" placeholder="${__("Reply")}" ${editable ? "" : "disabled"}>`).val(prefill);
    $row.append($input);
    $composer.append($row);

    $input.on("focus", () => {
      const $thread = this.$root.find("#wag-convo-thread");
      if ($thread.length) this.pin_thread_to_bottom($thread);
    });

    const $actions = $(`<div class="wag-turn-actions"></div>`);
    if (canApprove) $actions.append(`<button class="btn btn-xs btn-primary wag-c-approve">${__("Approve")}</button>`);
    if (editable) {
      $actions.append(`<button class="btn btn-xs btn-success wag-c-send">${__("Send now")}</button>`);
      $actions.append(`<button class="btn btn-xs btn-default wag-c-discard">${__("Discard")}</button>`);
    }
    if (canRetry) $actions.append(`<button class="btn btn-xs btn-warning wag-c-retry">${__("Retry")}</button>`);
    $composer.append($actions);

    let acting = false;
    const refresh = () => {
      acting = false;
      this.load_conversations_panel(false);
      this.load_conversations_summary();
      this.refresh_tab_counters();
    };

    $actions.find(".wag-c-approve").on("click", () => {
      if (acting) return;
      acting = true;
      this.call("approve_turn", { turn_name: r.name, reply_text: $input.val() }).then(() => {
        frappe.show_alert({ message: __("Marked Ready To Go"), indicator: "green" });
        refresh();
      });
    });
    $actions.find(".wag-c-send").on("click", () => {
      if (acting) return;
      acting = true;
      this.send_tracked_reply(r.name, r.contact_phone, $input.val(), refresh);
    });
    $actions.find(".wag-c-discard").on("click", () => {
      if (acting) return;
      acting = true;
      this.call("cancel_turn", { turn_name: r.name }).then(() => {
        frappe.show_alert({ message: __("Discarded"), indicator: "orange" });
        refresh();
      });
    });
    $actions.find(".wag-c-retry").on("click", () => {
      if (acting) return;
      acting = true;
      this.call("retry_failed_turn", { turn_name: r.name }).then(() => {
        frappe.show_alert({ message: __("Retrying"), indicator: "blue" });
        refresh();
      });
    });
  }

  render_gallery() {
    const $panel = this.$root.find('[data-panel="gallery"]').empty();
    const s = this.state.gallery_tab;

    $panel.append(`<div class="wag-cards" id="wag-gallery-stats"></div>`);
    this.load_gallery_stats();

    const $filters = $(`<div class="wag-toolbar wag-gallery-filters"></div>`).appendTo($panel);
    const $categorySelect = $(`
      <select class="form-control input-sm">
        <option value="">${__("All categories")}</option>
        <option value="__unprocessed__">${__("Unprocessed")}</option>
        <option value="School Activity">${__("School Activity")}</option>
        <option value="Poster">${__("Poster")}</option>
        <option value="Support">${__("Support")}</option>
        <option value="Event">${__("Event")}</option>
        <option value="Unnecessary">${__("Unnecessary")}</option>
        <option value="Other">${__("Other")}</option>
      </select>
    `).val(s.category || "").on("change", (e) => {
      s.category = e.target.value || null;
      s.start = 0;
      this.load_gallery(false);
    });
    $filters.append($categorySelect);

    $panel.append(`<div class="wag-chip-row" id="wag-gallery-category-strip"></div>`);
    $panel.append(`<div class="wag-gallery-grid" id="wag-gallery-grid"></div>`);
    this.pagination_controls($panel, "wag-gallery-pager", s, (append) => this.load_gallery(append));

    this.load_gallery_category_summary();
    this.load_gallery(false);
  }

  load_gallery_stats() {
    const g = this.state.geo;
    const $cards = this.$root.find("#wag-gallery-stats");
    this.call("get_media_processing_summary", { wa_group: g.wa_group, district: g.district, city: g.city, state: g.state, school: g.school }).then((d) => {
      $cards.empty();
      [
        { label: __("Total Images"), value: d.total_images || 0 },
        { label: __("Total Videos"), value: d.total_videos || 0 },
        { label: __("Total Stickers"), value: d.total_stickers || 0 },
        { label: __("Processed"), value: d.processed || 0 },
      ].forEach((c) => {
        $cards.append(`
          <div class="wag-card">
            <div class="wag-card-value">${c.value}</div>
            <div class="wag-card-label">${c.label}</div>
          </div>
        `);
      });
      $(`
        <div class="wag-card" style="cursor:pointer;border-color:var(--wag-green-mid);">
          <div class="wag-card-value">${d.unprocessed || 0}</div>
          <div class="wag-card-label">${__("Unprocessed")}</div>
        </div>
      `).on("click", () => {
        this.state.gallery_tab.category = "__unprocessed__";
        this.render_gallery();
      }).appendTo($cards);
    });
  }

  load_gallery_category_summary() {
    const g = this.state.geo;
    const $strip = this.$root.find("#wag-gallery-category-strip");
    this.call("get_media_category_summary", {
      wa_group: g.wa_group, district: g.district, city: g.city, state: g.state, school: g.school,
    }).then((rows) => {
      $strip.empty();
      rows.forEach((r) => {
        $(`<span class="wag-chip">${this.esc(r.category)} <span class="wag-chip-count">${r.count}</span></span>`)
          .on("click", () => {
            this.state.gallery_tab.category = r.category === "Uncategorized" ? null : r.category;
            this.state.gallery_tab.start = 0;
            this.render_gallery();
          })
          .appendTo($strip);
      });
    });
  }

  load_gallery(append) {
    const s = this.state.gallery_tab;
    const $grid = this.$root.find("#wag-gallery-grid");
    const $loadMore = this.$root.find("#wag-gallery-pager-more");

    this.call("get_conversations_gallery", {
      filters: this.filters_for("gallery"), start: s.start, page_length: s.page_length,
    }).then((res) => {
      if (!append) $grid.empty();
      if (!res.rows.length && !append) {
        $grid.html(`<div class="wag-empty">${__("No media in this view yet.")}</div>`);
        $loadMore.hide();
        return;
      }
      res.rows.forEach((r) => this.render_gallery_card($grid, r));
      $loadMore.toggle(res.has_more);
    });
  }

  render_gallery_card($grid, r) {
    const isVideoThumb = (r.media_mime_type || "").toLowerCase() === "video";
    const categories = ["School Activity", "Poster", "Support", "Event", "Unnecessary", "Other"];
    const optionsHtml = [`<option value="">${__("Uncategorized")}</option>`]
      .concat(categories.map((c) => `<option value="${c}" ${r.category === c ? "selected" : ""}>${c}</option>`))
      .join("");
    const imgSrc = this.media_proxy_url(r.source_turn, r.bq_id || r.media_name);

    const $card = $(`
      <div class="wag-gallery-card">
        ${isVideoThumb
          ? `<video class="wag-gallery-thumb" controls preload="metadata" src="${imgSrc}" onerror="this.classList.add('wag-media-broken')"></video>`
          : `<img class="wag-gallery-thumb" src="${imgSrc}" loading="lazy" alt="" onerror="this.classList.add('wag-media-broken')">`}
        <div class="wag-gallery-body">
          <div class="wag-gallery-meta-row">
            <span>${this.esc(r.wa_group_name || r.wa_group || "")}</span>
            <span>${frappe.datetime.str_to_user(r.occurred_at)}</span>
          </div>
          <div class="wag-gallery-meta-row">
            <span>${this.esc(this.mask(r.contact_display || r.contact_phone || ""))}</span>
            ${isVideoThumb ? this.badge(__("Video"), "neutral") : ""}
            ${r.is_processed ? "" : this.badge(__("Unprocessed"), "pending")}
          </div>
          ${r.caption ? `<div class="wag-gallery-caption">${this.esc(r.caption)}</div>` : ""}
          <select class="form-control input-sm wag-gallery-category-select">${optionsHtml}</select>
        </div>
      </div>
    `);

    if (!isVideoThumb) {
      $card.find(".wag-gallery-thumb").on("click", () => this.open_lightbox(imgSrc));
    }

    $card.find(".wag-gallery-category-select").on("change", (e) => {
      this.call("set_media_category_override", { media_name: r.media_name, category: e.target.value }).then(() => {
        frappe.show_alert({ message: __("Category updated"), indicator: "green" });
        this.load_gallery_category_summary();
        this.load_gallery_stats();
        this.refresh_tab_counters();
      });
    });

    $grid.append($card);
  }

  render_people() {
    const $panel = this.$root.find('[data-panel="people"]').empty();
    const s = this.state.people_tab;

    const $filters = $(`<div class="wag-toolbar"></div>`).appendTo($panel);
    const $sortSelect = $(`
      <select class="form-control input-sm">
        <option value="messages">${__("Sort: Most Messages")}</option>
        <option value="last_seen">${__("Sort: Recently Active")}</option>
        <option value="replies">${__("Sort: Most Replies Received")}</option>
      </select>
    `).val(s.sort_by).on("change", (e) => {
      s.sort_by = e.target.value;
      s.start = 0;
      this.load_people(false);
    });
    $filters.append($sortSelect);

    $panel.append(`<div class="wag-table-wrap" id="wag-people-table"></div>`);
    this.pagination_controls($panel, "wag-people-pager", s, (append) => this.load_people(append));
    this.load_people(false);
  }

  load_people(append) {
    const s = this.state.people_tab;
    const $wrap = this.$root.find("#wag-people-table");
    const $loadMore = this.$root.find("#wag-people-pager-more");

    this.call("get_people_summary", {
      date_from: this.state.date_from, date_to: this.state.date_to,
      filters: this.filters_for("people"),
      start: s.start, page_length: s.page_length, sort_by: s.sort_by,
    }).then((res) => {
      if (!append) $wrap.empty();
      if (!res.rows.length && !append) {
        $wrap.html(`<div class="wag-empty">${__("No activity for this range.")}</div>`);
        $loadMore.hide();
        return;
      }

      let $table = $wrap.find("table.wag-table");
      if (!$table.length) {
        $table = $(`
          <table class="wag-table">
            <thead><tr>
              <th>${__("Contact")}</th><th>${__("Kind")}</th><th>${__("Turns")}</th>
              <th>${__("Messages")}</th><th>${__("Groups")}</th><th>${__("Response Rate")}</th>
              <th>${__("Support Turns")}</th><th>${__("Last Seen")}</th>
            </tr></thead>
            <tbody></tbody>
          </table>
        `);
        $wrap.append($table);
      }
      const $tbody = $table.find("tbody");
      res.rows.forEach((r) => {
        const $tr = $(`
          <tr class="wag-row-clickable">
            <td>${this.esc(this.mask(r.contact_display || r.contact_phone || ""))}</td>
            <td>${this.esc(r.contact_kind || "-")}</td>
            <td>${r.turn_count}</td>
            <td>${r.message_count}</td>
            <td>${r.groups_touched}</td>
            <td>${r.response_rate}%</td>
            <td>${r.support_turns}</td>
            <td>${frappe.datetime.str_to_user(r.last_seen)}</td>
          </tr>
        `).on("click", () => this.open_person_drawer(r));
        $tbody.append($tr);
      });
      $loadMore.toggle(res.has_more);
    });
  }

  open_person_drawer(r) {
    const $backdrop = $(`<div class="wag-person-drawer-backdrop"></div>`).appendTo("body");
    const $drawer = $(`
      <div class="wag-person-drawer">
        <div class="wag-person-drawer-head">
          <h4>${this.esc(this.mask(r.contact_display || r.contact_phone))}</h4>
          <span class="wag-person-drawer-close">&times;</span>
        </div>
        <div class="wag-person-stats-row">
          <div class="wag-card"><div class="wag-card-value">${r.turn_count}</div><div class="wag-card-label">${__("Turns")}</div></div>
          <div class="wag-card"><div class="wag-card-value">${r.message_count}</div><div class="wag-card-label">${__("Messages")}</div></div>
          <div class="wag-card"><div class="wag-card-value">${r.response_rate}%</div><div class="wag-card-label">${__("Response Rate")}</div></div>
          <div class="wag-card"><div class="wag-card-value">${r.staff_tagged_replies}</div><div class="wag-card-label">${__("Staff Replies")}</div></div>
        </div>
        <div id="wag-person-turns" class="wag-convo-thread wag-convo-thread-embedded"></div>
        <div class="wag-load-more"><button class="btn btn-xs btn-default" id="wag-person-load-more">${__("Load more")}</button></div>
      </div>
    `).appendTo($backdrop);

    const close = () => {
      if (this._personThreadObserver) {
        this._personThreadObserver.disconnect();
        this._personThreadObserver = null;
      }
      $backdrop.remove();
    };
    $backdrop.on("click", (e) => { if (e.target === $backdrop[0]) close(); });
    $drawer.find(".wag-person-drawer-close").on("click", close);

    let start = 0;
    const pageLength = 25;
    const $list = $drawer.find("#wag-person-turns");
    const $loadMore = $drawer.find("#wag-person-load-more").hide();

    const loadTurns = (append) => {
      this.call("get_person_turns", { contact_phone: r.contact_phone, start, page_length: pageLength }).then((res) => {
        const built = this.build_thread_entries(res.rows, r.contact_phone);
        this.render_thread_entries($list, built.entries, false);
        $loadMore.toggle(res.has_more);
        if (typeof ResizeObserver !== "undefined" && !this._personThreadObserver) {
          const observer = new ResizeObserver(() => this.pin_thread_to_bottom($list));
          observer.observe($list[0]);
          this._personThreadObserver = observer;
        }
        this.pin_thread_to_bottom($list);
      });
    };
    $loadMore.on("click", () => {
      start += pageLength;
      loadTurns(true);
    });
    loadTurns(false);
  }

  render_replies() {
    const $panel = this.$root.find('[data-panel="replies"]').empty();
    const s = this.state.replies_tab;

    $panel.append(`<div class="wag-status-pill">${__("Messages where someone tagged")} ${this.tag_display_label()}</div>`);
    $panel.append(`<div class="wag-table-wrap" id="wag-reply-table"></div>`);
    this.pagination_controls($panel, "wag-reply-pager", s, (append) => this.load_replies(append));

    s.start = 0;
    this._repliesAccum = [];
    this._repliesRenderedCount = 0;
    this._repliesSourceStart = 0;
    this._repliesSourceExhausted = false;
    this.load_replies(false);
  }

  load_replies(append) {
    const s = this.state.replies_tab;
    const $wrap = this.$root.find("#wag-reply-table");
    const $loadMore = this.$root.find("#wag-reply-pager-more");

    if (!append) {
      this._repliesAccum = [];
      this._repliesRenderedCount = 0;
      this._repliesSourceStart = 0;
      this._repliesSourceExhausted = false;
      $wrap.empty();
    }

    const targetCount = this._repliesRenderedCount + s.page_length;

    const pullNextBatch = () => {
      if (this._repliesAccum.length >= targetCount || this._repliesSourceExhausted) {
        return Promise.resolve();
      }
      return this.call("get_conversation_turns", {
        filters: { geo: this.filters_for("replies").geo, turn_status: ["Open", "Drafted", "Ready To Go", "Sent", "Failed", "Ignored"] },
        start: this._repliesSourceStart,
        page_length: s.scan_batch,
        include_poll_only: false,
      }).then((res) => {
        this._repliesSourceStart += s.scan_batch;
        if (!res.has_more) this._repliesSourceExhausted = true;

        (res.rows || []).forEach((r) => {
          const items = this.safe_parse_items(r.turn_items);
          this.visible_turn_items(items).forEach((it) => {
            if (this.message_tags_me(it.body)) {
              this._repliesAccum.push({
                when: it.occurred_at || r.last_item_at,
                group: r.wa_group_name || r.wa_group || "",
                phone: r.contact_phone,
                name: r.contact_display || r.contact_phone,
                body: this.strip_my_tag(it.body),
              });
            }
          });
        });

        if (!res.rows.length) this._repliesSourceExhausted = true;
        return pullNextBatch();
      });
    };

    pullNextBatch().then(() => {
      const toRender = this._repliesAccum.slice(this._repliesRenderedCount, targetCount);
      this._repliesRenderedCount = Math.min(targetCount, this._repliesAccum.length);

      if (!this._repliesAccum.length && !append) {
        $wrap.html(`<div class="wag-empty">${__("No one has tagged")} ${this.tag_display_label()} ${__("in this view yet.")}</div>`);
        $loadMore.hide();
        return;
      }

      let $table = $wrap.find("table.wag-table");
      if (!$table.length) {
        $table = $(`
          <table class="wag-table">
            <thead><tr>
              <th>${__("When")}</th><th>${__("Group")}</th><th>${__("Contact")}</th>
              <th>${__("Message")}</th><th></th>
            </tr></thead>
            <tbody></tbody>
          </table>
        `);
        $wrap.append($table);
      }
      const $tbody = $table.find("tbody");
      toRender.forEach((t) => {
        const $tr = $(`
          <tr>
            <td>${frappe.datetime.str_to_user(t.when)}</td>
            <td>${this.esc(t.group)}</td>
            <td>${this.esc(this.mask(t.name))}</td>
            <td class="wag-td-wrap">${this.esc(t.body)}</td>
            <td><button class="btn btn-xs btn-default wag-open-tagged-convo">${__("Open")}</button></td>
          </tr>
        `);
        $tr.find(".wag-open-tagged-convo").on("click", () => {
          this.state.conversations_tab.view_mode = "people";
          this.state.conversations_tab.turn_status = ["Open", "Drafted", "Ready To Go", "Sent", "Failed", "Ignored"];
          this.state.conversations_tab.selected_phone = t.phone;
          this.switch_tab("conversations");
        });
        $tbody.append($tr);
      });

      const stillHasMore = this._repliesAccum.length > this._repliesRenderedCount || !this._repliesSourceExhausted;
      $loadMore.toggle(stillHasMore);
    });
  }

  render_reactions() {
    const $panel = this.$root.find('[data-panel="reactions"]').empty();
    const g = this.state.geo;
    const s = this.state.reactions_tab;

    $panel.append(`<div class="wag-status-pill">${__("Reactions placed on anything our WhatsApp number sent — text or media — are captured here.")}</div>`);
    $panel.append(`<div class="wag-chip-row" id="wag-reaction-emoji-strip"></div>`);
    $panel.append(`<div id="wag-reaction-feed"></div>`);
    this.pagination_controls($panel, "wag-reaction-pager", s, (append) => this.load_reactions_feed(append));

    this.call("get_reaction_emoji_breakdown", {
      ...this.date_range_args(),
      wa_group: g.wa_group, district: g.district, city: g.city, state: g.state, school: g.school,
    }).then((rows) => {
      const $strip = this.$root.find("#wag-reaction-emoji-strip");
      $strip.empty();
      if (!rows.length) {
        $strip.append(`<div class="wag-empty">${__("No reactions in this range.")}</div>`);
        return;
      }
      rows.forEach((r) => {
        $strip.append(`<span class="wag-chip">${r.reaction_emoji} <span class="wag-chip-count">${r.cnt}</span></span>`);
      });
    });

    s.start = 0;
    this.load_reactions_feed(false);
  }

  load_reactions_feed(append) {
    const s = this.state.reactions_tab;
    const $feed = this.$root.find("#wag-reaction-feed");
    const $loadMore = this.$root.find("#wag-reaction-pager-more");

    this.call("get_reactions_feed", {
      filters: this.filters_for("reactions"), start: s.start, page_length: s.page_length,
    }).then((res) => {
      if (!append) $feed.empty();
      if (!res.rows.length && !append) {
        $feed.html(`<div class="wag-empty">${__("No reactions in this view yet.")}</div>`);
        $loadMore.hide();
        return;
      }
      res.rows.forEach((row) => this.render_reaction_feed_row($feed, row));
      $loadMore.toggle(res.has_more);
    });
  }

  render_reaction_feed_row($feed, row) {
    const typeTag = row.reacted_message_type && row.reacted_message_type !== "text"
      ? this.badge(row.reacted_message_type, "neutral") : "";
    const mediaHtml = row.reacted_message_media_url && row.reacted_message_type !== "text"
      ? `<img class="wag-campaign-media-thumb" src="${this.esc(row.reacted_message_media_url)}" loading="lazy" alt="">`
      : "";
    const messageHtml = `<div class="wag-bubble wag-bubble-out"><span class="wag-bubble-text">${this.esc(row.reacted_message_body || "")}</span></div>`;

    const reactionChips = (row.reactions || []).map((rx) =>
      `<span class="wag-chip">${rx.emoji} ${this.esc(this.mask(rx.contact_display || rx.contact_phone || ""))}</span>`
    ).join(" ");

    const $row = $(`
      <div class="wag-turn-card">
        <div class="wag-turn-head">
          <span class="wag-turn-group">${this.esc(row.wa_group_name || row.wa_group || "")}</span>
          ${typeTag}
          <span class="wag-badge wag-badge-neutral">${row.total_count} ${__("reactions")}</span>
        </div>
        <div class="wag-turn-items">${messageHtml}${mediaHtml}</div>
        <div class="wag-chip-row">${reactionChips}</div>
      </div>
    `);
    $feed.append($row);
  }

  render_safety() {
    const $panel = this.$root.find('[data-panel="safety"]').empty();
    $panel.append(`<div id="wag-safety-general"></div>`);
    $panel.append(`<h5>${__("Per-Modality AI Model Configs")}</h5>`);
    $panel.append(`<div class="wag-safety-grid" id="wag-safety-modalities"></div>`);
    $panel.append(`<div id="wag-safety-other"></div>`);
    $panel.append(`<h5>${__("WA Groups")}</h5>`);
    $panel.append(`<div class="wag-table-wrap" id="wag-safety-groups"></div>`);

    this.call("get_safety_settings_summary").then((s) => {
      this.myTagId = this.digits_only(s.my_tag_id) || null;
      this.myTagLabel = (s.my_tag_label || "").trim() || "tapbuddy";
      this.refresh_last_synced_pill();
      this.render_safety_general(s);
      this.render_safety_modalities(s);
      this.render_safety_other(s);
    });

    this.load_safety_groups();
  }

  load_safety_groups() {
    const $wrap = this.$root.find("#wag-safety-groups");
    this.call("get_wa_groups_for_filter", { include_disabled_groups: true }).then((rows) => {
      $wrap.empty();
      if (!rows.length) {
        $wrap.html(`<div class="wag-empty">${__("No groups synced yet.")}</div>`);
        return;
      }
      const $table = $(`
        <table class="wag-table">
          <thead><tr>
            <th>${__("Group")}</th><th>${__("Sync Status")}</th><th>${__("Enabled")}</th><th>${__("Reason")}</th><th></th>
          </tr></thead>
          <tbody></tbody>
        </table>
      `);
      const $tbody = $table.find("tbody");
      rows.forEach((r) => {
        const $tr = $(`
          <tr>
            <td>${this.esc(r.group_name || r.name)}</td>
            <td>${this.badge(r.sync_status || "Unknown", r.sync_status === "Active" ? "success" : "neutral")}</td>
            <td>${r.is_enabled ? this.badge(__("Enabled"), "success") : this.badge(__("Disabled"), "failed")}</td>
            <td class="wag-td-wrap">${this.esc(r.disabled_reason || "")}</td>
            <td><button class="btn btn-xs btn-default wag-toggle-group-enabled">${r.is_enabled ? __("Disable") : __("Enable")}</button></td>
          </tr>
        `);
        $tr.find(".wag-toggle-group-enabled").on("click", () => {
          const willEnable = !r.is_enabled;
          const applyToggle = (reason) => {
            this.call("set_group_enabled", { wa_group: r.name, is_enabled: willEnable, disabled_reason: reason }).then(() => {
              frappe.show_alert({ message: __("Updated"), indicator: "green" });
              this.load_safety_groups();
              this.refresh_group_select();
            });
          };
          if (willEnable) {
            applyToggle(null);
          } else {
            frappe.prompt(
              { fieldname: "reason", fieldtype: "Data", label: __("Reason (optional)") },
              (vals) => applyToggle(vals.reason || null),
              __("Disable group"), __("Disable")
            );
          }
        });
        $tbody.append($tr);
      });
      $wrap.append($table);
    });
  }

  render_safety_general(s) {
    const $wrap = this.$root.find("#wag-safety-general").empty();
    const $card = $(`
      <div class="wag-safety-card">
        <h6>${__("AI Reply")}</h6>
        <div class="wag-safety-edit-row">
          <label><input type="checkbox" id="wag-set-ai-enabled" ${s.ai_enabled ? "checked" : ""}> ${__("AI Enabled")}</label>
        </div>
        <div class="wag-safety-edit-row">
          <label>${__("Mode")}</label>
          <select class="form-control input-sm" id="wag-set-ai-mode">
            <option value="Draft Only" ${s.ai_mode_default === "Draft Only" ? "selected" : ""}>${__("Draft Only")}</option>
            <option value="Auto Send" ${s.ai_mode_default === "Auto Send" ? "selected" : ""}>${__("Auto Send")}</option>
          </select>
        </div>
        <div class="wag-safety-edit-row">
          <label>${__("Daily Draft Limit")}</label>
          <input type="number" class="form-control input-sm" id="wag-set-daily-limit" value="${s.ai_daily_draft_limit || 500}">
        </div>
        <div class="wag-safety-edit-row">
          <label>${__("Max Attempts")}</label>
          <input type="number" class="form-control input-sm" id="wag-set-max-attempts" value="${s.ai_max_attempts || 3}">
        </div>
        <button class="btn btn-xs btn-primary" id="wag-save-general">${__("Save")}</button>
        <div class="wag-status-pill">${__("Last Draft")}: ${s.last_ai_draft_status || "-"} — ${this.esc(s.last_ai_draft_message || "")}</div>
      </div>
    `);
    $card.find("#wag-save-general").on("click", () => {
      frappe.call({
        method: "frappe.client.set_value",
        args: {
          doctype: "WA Bot Settings",
          name: "WA Bot Settings",
          fieldname: {
            ai_enabled: $card.find("#wag-set-ai-enabled").is(":checked") ? 1 : 0,
            ai_mode_default: $card.find("#wag-set-ai-mode").val(),
            ai_daily_draft_limit: parseInt($card.find("#wag-set-daily-limit").val(), 10) || 500,
            ai_max_attempts: parseInt($card.find("#wag-set-max-attempts").val(), 10) || 3,
          },
        },
      }).then(() => frappe.show_alert({ message: __("Saved"), indicator: "green" }));
    });
    $wrap.append($card);

    const $tagCard = $(`
      <div class="wag-safety-card">
        <h6>${__("My Tag")}</h6>
        <div class="wag-safety-edit-row">
          <label>${__("Your phone number/ID as it appears in an @mention")}</label>
          <input class="form-control input-sm" id="wag-set-my-tag-id" value="${this.esc(s.my_tag_id || "")}" placeholder="${__("e.g. 38157261221942")}">
        </div>
        <div class="wag-safety-edit-row">
          <label>${__("Display label shown on the dashboard")}</label>
          <input class="form-control input-sm" id="wag-set-my-tag-label" value="${this.esc(s.my_tag_label || "")}" placeholder="tapbuddy">
        </div>
        <button class="btn btn-xs btn-primary" id="wag-save-my-tag">${__("Save")}</button>
        <div class="wag-status-pill">${s.my_tag_id ? `🏷️ ${__("Currently")}: ${this.tag_display_label()}` : `⚠️ ${__("Not set")}`}</div>
      </div>
    `);
    $tagCard.find("#wag-save-my-tag").on("click", () => {
      frappe.call({
        method: "frappe.client.set_value",
        args: {
          doctype: "WA Bot Settings",
          name: "WA Bot Settings",
          fieldname: {
            my_tag_id: $tagCard.find("#wag-set-my-tag-id").val(),
            my_tag_label: $tagCard.find("#wag-set-my-tag-label").val() || "tapbuddy",
          },
        },
      }).then(() => {
        frappe.show_alert({ message: __("Saved"), indicator: "green" });
        this.load_my_tag_id().then(() => {
          this.refresh_last_synced_pill();
          this.render_safety();
        });
      });
    });
    $wrap.append($tagCard);

    const $staffCard = $(`
      <div class="wag-safety-card">
        <h6>${__("Staff Number Filtering")}</h6>
        <div class="wag-safety-edit-row">
          <label><input type="checkbox" id="wag-set-ignore-staff" ${s.ignore_staff_numbers_enabled ? "checked" : ""}> ${__("Ignore Staff Numbers")}</label>
        </div>
        <div class="wag-safety-edit-row">
          <label>${__("Staff Numbers To Ignore (comma-separated)")}</label>
          <textarea class="form-control input-sm" id="wag-set-ignored-numbers" rows="2">${this.esc(s.ignored_staff_numbers || "")}</textarea>
        </div>
        <button class="btn btn-xs btn-primary" id="wag-save-staff-filter">${__("Save")}</button>
      </div>
    `);
    $staffCard.find("#wag-save-staff-filter").on("click", () => {
      this.call("set_staff_filter_settings", {
        ignore_staff_numbers_enabled: $staffCard.find("#wag-set-ignore-staff").is(":checked"),
        ignored_staff_numbers: $staffCard.find("#wag-set-ignored-numbers").val(),
      }).then(() => frappe.show_alert({ message: __("Saved"), indicator: "green" }));
    });
    $wrap.append($staffCard);

    const $waveCard = $(`
      <div class="wag-safety-card">
        <h6>${__("Send Waves")}</h6>
        <div class="wag-safety-edit-row">
          <label>${__("Default Wave Size")}</label>
          <input type="number" class="form-control input-sm" id="wag-set-wave-size" value="${s.default_wave_size || 25}">
        </div>
        <div class="wag-safety-edit-row">
          <label>${__("Default Wave Gap (minutes)")}</label>
          <input type="number" class="form-control input-sm" id="wag-set-wave-gap" value="${s.default_wave_gap_minutes != null ? s.default_wave_gap_minutes : 10}">
        </div>
        <button class="btn btn-xs btn-primary" id="wag-save-wave-settings">${__("Save")}</button>
      </div>
    `);
    $waveCard.find("#wag-save-wave-settings").on("click", () => {
      frappe.call({
        method: "frappe.client.set_value",
        args: {
          doctype: "WA Bot Settings",
          name: "WA Bot Settings",
          fieldname: {
            default_wave_size: parseInt($waveCard.find("#wag-set-wave-size").val(), 10) || 25,
            default_wave_gap_minutes: parseInt($waveCard.find("#wag-set-wave-gap").val(), 10) || 0,
          },
        },
      }).then(() => frappe.show_alert({ message: __("Saved"), indicator: "green" }));
    });
    $wrap.append($waveCard);
  }

  render_safety_modalities(s) {
    const $grid = this.$root.find("#wag-safety-modalities").empty();
    (s.model_configs || []).forEach((cfg) => {
      const $card = $(`
        <div class="wag-safety-card">
          <h6>${this.esc(cfg.modality)}</h6>
          <div class="wag-safety-edit-row">
            <label><input type="checkbox" class="wag-m-enabled" ${cfg.enabled ? "checked" : ""}> ${__("Enabled")}</label>
          </div>
          <div class="wag-safety-edit-row">
            <label>${__("Provider")}</label>
            <select class="form-control input-sm wag-m-provider">
              <option value="Anthropic" ${cfg.provider === "Anthropic" ? "selected" : ""}>Anthropic</option>
              <option value="Groq" ${cfg.provider === "Groq" ? "selected" : ""}>Groq</option>
              <option value="OpenAI Compatible" ${cfg.provider === "OpenAI Compatible" ? "selected" : ""}>OpenAI Compatible</option>
            </select>
          </div>
          <div class="wag-safety-edit-row">
            <label>${__("Model ID")}</label>
            <input class="form-control input-sm wag-m-model" value="${this.esc(cfg.model_id || "")}">
          </div>
          <div class="wag-safety-edit-row">
            <label>${__("API Key")}</label>
            <input type="password" class="form-control input-sm wag-m-key" placeholder="${cfg.configured ? "✅ " + __("configured") : "⚠️ " + __("not set")}">
          </div>
          <div class="wag-safety-edit-row">
            <label>${__("API Base URL")}</label>
            <input class="form-control input-sm wag-m-url" value="${this.esc(cfg.api_base_url || "")}" placeholder="${__("provider default")}">
          </div>
          <div class="wag-safety-edit-row">
            <label>${__("Requests/min")}</label>
            <input type="number" class="form-control input-sm wag-m-rpm" value="${cfg.requests_per_minute || 25}">
          </div>
          <div class="wag-safety-edit-row">
            <label>${__("Daily Limit")}</label>
            <input type="number" class="form-control input-sm wag-m-daily" value="${cfg.daily_limit || 500}">
          </div>
          <button class="btn btn-xs btn-primary wag-m-save">${__("Save")}</button>
          <div class="wag-status-pill wag-m-usage" style="margin-top:6px;"></div>
        </div>
      `);

      $card.find(".wag-m-save").on("click", () => {
        this.call("set_model_config", {
          modality: cfg.modality,
          enabled: $card.find(".wag-m-enabled").is(":checked"),
          provider: $card.find(".wag-m-provider").val(),
          model_id: $card.find(".wag-m-model").val(),
          api_key: $card.find(".wag-m-key").val() || undefined,
          api_base_url: $card.find(".wag-m-url").val(),
          requests_per_minute: parseInt($card.find(".wag-m-rpm").val(), 10) || 25,
          daily_limit: parseInt($card.find(".wag-m-daily").val(), 10) || 500,
        }).then(() => {
          frappe.show_alert({ message: __("Saved"), indicator: "green" });
          this.render_safety();
        });
      });

      $grid.append($card);
    });

    this.call("get_modality_usage_today").then((usage) => {
      $grid.find(".wag-safety-card").each((i, el) => {
        const $el = $(el);
        const modality = $el.find("h6").text();
        const slug = { "Text English": "text-english", "Text Indic": "text-indic", "Vision Image": "vision-image", "Vision Video": "vision-video", "Voice Audio": "voice-audio" }[modality];
        const cfg = (s.model_configs || []).find((c) => c.modality === modality);
        if (slug && usage[slug] !== undefined && cfg) {
          $el.find(".wag-m-usage").text(`${usage[slug]} / ${cfg.daily_limit || 0} ${__("requests used today")}`);
        }
      });
    });
  }

  render_safety_other(s) {
    const $wrap = this.$root.find("#wag-safety-other").empty();

    $wrap.append(this.safety_card(__("Natural Response Delay"), [
      [__("Delay Enabled"), s.natural_delay_enabled],
      [__("Delay Window"), `${s.natural_delay_min_minutes ?? "-"} – ${s.natural_delay_max_minutes ?? "-"} min`],
      [__("Support Skips Delay"), s.support_skip_delay],
    ]));

    $wrap.append(this.safety_card(__("Content Safety"), [
      [__("Safety Checks Enabled"), s.content_safety_enabled],
      [__("Avoid PII In Replies"), s.pii_redaction_enabled],
      [__("Support Routes To Draft"), s.support_routes_to_draft],
      [__("Blocked Categories"), (s.blocked_categories || []).join(", ") || "-"],
    ]));

    $wrap.append(this.safety_card(__("Media & Data"), [
      [__("Auto Categorize Media"), s.media_auto_categorize_enabled],
      [__("Video AI Mode"), s.video_ai_mode],
      [__("BQ Max Bytes Per Query"), s.bq_max_bytes_billed ? `${(s.bq_max_bytes_billed / (1024 * 1024 * 1024)).toFixed(2)} GiB` : "-"],
    ]));

    $wrap.append(this.safety_card(__("Reaction Retry Queue"), [
      [__("Queue Size"), s.reaction_retry_queue_size || 0],
      [__("Oldest Entry"), s.reaction_retry_queue_oldest ? frappe.datetime.str_to_user(s.reaction_retry_queue_oldest) : "-"],
    ]));

    const $promptCard = $(`
      <div class="wag-safety-card" style="grid-column:1/-1;">
        <h6>${__("System Prompt (Text)")}</h6>
        <textarea class="form-control" id="wag-system-prompt" rows="8"></textarea>
        <div style="margin-top:8px;display:flex;gap:8px;">
          <button class="btn btn-xs btn-primary" id="wag-save-prompt">${__("Save")}</button>
          <button class="btn btn-xs btn-default" id="wag-reset-prompt">${__("Reset to default")}</button>
        </div>
      </div>
    `);
    frappe.db.get_single_value("WA Bot Settings", "ai_system_prompt").then((val) => {
      $promptCard.find("#wag-system-prompt").val(val || "");
    });
    $promptCard.find("#wag-save-prompt").on("click", () => {
      frappe.call({
        method: "frappe.client.set_value",
        args: { doctype: "WA Bot Settings", name: "WA Bot Settings", fieldname: "ai_system_prompt", value: $promptCard.find("#wag-system-prompt").val() },
      }).then(() => frappe.show_alert({ message: __("Saved"), indicator: "green" }));
    });
    $promptCard.find("#wag-reset-prompt").on("click", () => {
      this.call("reset_system_prompt_to_default").then(() => {
        frappe.show_alert({ message: __("Reset"), indicator: "green" });
        this.render_safety();
      });
    });
    $wrap.append($promptCard);

    $wrap.append(this.safety_card(__("Diagnostics"), [
      [__("Last Poll Status"), s.last_poll_status || "-"],
      [__("Last Poll Message"), s.last_poll_message || "-"],
      [__("Last Send Sweep Status"), s.last_send_sweep_status || "-"],
      [__("Last Voice Transcribe Status"), s.last_voice_transcribe_status || "-"],
      [__("Unreconciled Sends (7d)"), s.unreconciled_sends_last_7d || 0],
      [__("Reaction Dedup Index"), s.reaction_dedup_index_exists ? __("Present") : __("Missing")],
    ]));
  }

  safety_card(title, rows) {
    const rowsHtml = rows.map(([label, value]) => {
      let valueHtml;
      if (typeof value === "boolean") {
        valueHtml = value ? `<span class="wag-safety-on">${__("On")}</span>` : `<span class="wag-safety-off">${__("Off")}</span>`;
      } else {
        valueHtml = this.esc(String(value ?? "-"));
      }
      return `<div class="wag-safety-row"><span class="wag-safety-row-label">${label}</span><span>${valueHtml}</span></div>`;
    }).join("");
    return $(`<div class="wag-safety-card"><h6>${title}</h6>${rowsHtml}</div>`);
  }

  render_send() {
    const $panel = this.$root.find('[data-panel="send"]').empty();

    const $form = $(`
      <div class="wag-send-form">
        <div class="wag-full" id="wag-send-draft-field">
          <label>${__("Load a Draft")}</label>
          <select class="form-control input-sm" id="wag-send-draft-select">
            <option value="">${__("New send (start blank)")}</option>
          </select>
        </div>
        <div>
          <label>${__("Target Type")}</label>
          <select class="form-control input-sm" id="wag-send-target-type">
            <option value="Group">${__("Group")}</option>
            <option value="Collection">${__("Collection")}</option>
            <option value="Geo">${__("State / District / City / School")}</option>
          </select>
        </div>
        <div>
          <label>${__("Send Type")}</label>
          <select class="form-control input-sm" id="wag-send-type">
            <option value="Text">${__("Text")}</option>
            <option value="Media">${__("Media")}</option>
            <option value="Flow">${__("Flow")}</option>
            <option value="Poll">${__("Poll")}</option>
          </select>
        </div>
        <div class="wag-full" id="wag-send-target-field">
          <label>${__("WA Group or Collection")}</label>
          <select class="form-control input-sm" id="wag-send-group"><option value="">${__("Select...")}</option></select>
        </div>
        <div class="wag-full" id="wag-send-geo-field" style="display:none;">
          <label>${__("Target Geography")}</label>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;">
            <select class="form-control input-sm" id="wag-send-geo-state"><option value="">${__("Any State")}</option></select>
            <select class="form-control input-sm" id="wag-send-geo-district"><option value="">${__("Any District")}</option></select>
            <select class="form-control input-sm" id="wag-send-geo-city"><option value="">${__("Any City")}</option></select>
            <select class="form-control input-sm" id="wag-send-geo-school"><option value="">${__("Any School")}</option></select>
          </div>
          <div class="wag-status-pill" id="wag-send-geo-preview"></div>
        </div>
        <div class="wag-full" id="wag-send-body-field">
          <label>${__("Message Body")}</label>
          <textarea class="form-control" id="wag-send-body" rows="3"></textarea>
        </div>
        <div class="wag-full" id="wag-send-media-field" style="display:none;">
          <label>${__("Media File")}</label>
          <div id="wag-send-media-attach"></div>
          <label style="margin-top:8px;">${__("…or a Media URL")}</label>
          <input class="form-control input-sm" id="wag-send-media-url">
          <div class="wag-status-pill" id="wag-send-media-status"></div>
        </div>
        <div class="wag-full" id="wag-send-flow-field" style="display:none;">
          <label>${__("Glific Flow ID")}</label>
          <input class="form-control input-sm" id="wag-send-flow-id">
        </div>
        <div class="wag-full" id="wag-send-poll-field" style="display:none;">
          <label>
            <input type="checkbox" id="wag-send-poll-multi-lang"> ${__("Multi-language poll (different poll per group language, one send)")}
          </label>
          <div id="wag-send-poll-single-wrap">
            <label>${__("Poll")}</label>
            <select class="form-control input-sm" id="wag-send-poll-select"></select>
          </div>
          <div id="wag-send-poll-multi-wrap" style="display:none;">
            <div id="wag-poll-lang-rows"></div>
            <button class="btn btn-xs btn-default" id="wag-poll-lang-add-row" style="margin-top:6px;">${__("+ Add language variant")}</button>
          </div>
          <div style="margin-top:6px;">
            <button class="btn btn-xs btn-default" id="wag-send-poll-new-toggle">${__("+ Create new poll")}</button>
          </div>
          <div id="wag-send-poll-new-form" style="display:none;margin-top:8px;border:1px solid var(--border-color);border-radius:6px;padding:10px;">
            <input class="form-control input-sm" id="wag-poll-new-label" placeholder="${__("Poll label")}" style="margin-bottom:6px;">
            <input class="form-control input-sm" id="wag-poll-new-text" placeholder="${__("Poll question")}" style="margin-bottom:6px;">
            <div id="wag-poll-new-options"></div>
            <button class="btn btn-xs btn-default" id="wag-poll-new-add-option" style="margin:6px 0;">${__("+ Add option")}</button>
            <div>
              <label><input type="checkbox" id="wag-poll-new-multi"> ${__("Allow multiple answers")}</label>
            </div>
            <button class="btn btn-xs btn-primary" id="wag-poll-new-create" style="margin-top:6px;">${__("Create poll")}</button>
          </div>
        </div>
        <div class="wag-full" id="wag-send-wave-field" style="display:none;">
          <label>${__("Throttling")}</label>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div>
              <label style="font-size:11px;">${__("Groups per wave")}</label>
              <input type="number" class="form-control input-sm" id="wag-send-wave-size">
            </div>
            <div>
              <label style="font-size:11px;">${__("Minutes between waves")}</label>
              <input type="number" class="form-control input-sm" id="wag-send-wave-gap">
            </div>
          </div>
        </div>
        <div>
          <label>${__("Send")}</label>
          <select class="form-control input-sm" id="wag-send-mode">
            <option value="now">${__("Now")}</option>
            <option value="draft">${__("Save as Draft")}</option>
            <option value="schedule">${__("Schedule")}</option>
          </select>
        </div>
        <div id="wag-send-schedule-field" style="display:none;">
          <label>${__("Scheduled At")}</label>
          <input type="datetime-local" class="form-control input-sm" id="wag-send-scheduled-at">
        </div>
        <div class="wag-full">
          <button class="btn btn-sm btn-primary" id="wag-send-btn">${__("Submit")}</button>
        </div>
      </div>
    `).appendTo($panel);

    $panel.append(`<h5>${__("Recent Sends")}</h5>`);
    $panel.append(`<div class="wag-table-wrap" id="wag-recent-campaigns"></div>`);
    this.pagination_controls($panel, "wag-send-recent-pager", this.state.send_recent, (append) => this.load_recent_campaigns(append));

    this.call("get_wa_groups_for_filter", {}).then((rows) => {
      this._allGroupsCache = rows;
      this.refresh_send_target_options();
      this.apply_pending_draft_load($form);
    });
    this.call("list_wa_polls").then((polls) => { this._allPollsCache = polls; });
    this.call("get_safety_settings_summary").then((s) => {
      $form.find("#wag-send-wave-size").val(s.default_wave_size || 25);
      $form.find("#wag-send-wave-gap").val(s.default_wave_gap_minutes != null ? s.default_wave_gap_minutes : 10);
    });

    const $attach = frappe.ui.form.make_control({
      parent: $form.find("#wag-send-media-attach"),
      df: { fieldtype: "Attach", fieldname: "media_file", label: "" },
      render_input: true,
    });
    this._sendMediaAttach = $attach;

    const addPollOptionRow = (value) => {
      const $row = $(`<input class="form-control input-sm wag-poll-option" style="margin-bottom:6px;" placeholder="${__("Option")}">`);
      if (value) $row.val(value);
      $form.find("#wag-poll-new-options").append($row);
    };
    addPollOptionRow();
    addPollOptionRow();

    $form.find("#wag-poll-new-add-option").on("click", () => addPollOptionRow());

    this.call("get_geo_options").then((opts) => {
      const $state = $form.find("#wag-send-geo-state");
      const $district = $form.find("#wag-send-geo-district");
      const $city = $form.find("#wag-send-geo-city");
      const $school = $form.find("#wag-send-geo-school");
      (opts.states || []).forEach((s) => $state.append(`<option value="${this.esc(s)}">${this.esc(s)}</option>`));
      (opts.districts || []).forEach((d) => $district.append(`<option value="${this.esc(d)}">${this.esc(d)}</option>`));
      (opts.cities || []).forEach((c) => $city.append(`<option value="${this.esc(c)}">${this.esc(c)}</option>`));
      (opts.schools || []).forEach((s) => {
        const label = s.school_name || s.name;
        $school.append(`<option value="${this.esc(s.name)}">${this.esc(label)}</option>`);
      });
    });

    frappe.db.get_list("TAP Language", { fields: ["name", "language_name"], limit: 200 }).then((rows) => {
      this._languageCache = rows;
    });

    const loadPolls = (selectUuid) => {
      this.call("list_wa_polls").then((rows) => {
        this._allPollsCache = rows;
        const $select = $form.find("#wag-send-poll-select");
        $select.empty();
        $select.append(`<option value="">${__("Select a poll")}</option>`);
        rows.forEach((p) => {
          $select.append(`<option value="${this.esc(p.uuid)}">${this.esc(p.label)}</option>`);
        });
        if (selectUuid) $select.val(selectUuid);
        this.refresh_poll_lang_option_lists();
      });
    };
    loadPolls();

    this.addPollLangRow = (lang, pollUuid, isDefault) => {
      const langOptions = (this._languageCache || [])
        .map((l) => `<option value="${this.esc(l.name)}" ${l.name === lang ? "selected" : ""}>${this.esc(l.language_name || l.name)}</option>`)
        .join("");
      const pollOptions = (this._allPollsCache || [])
        .map((p) => `<option value="${this.esc(p.uuid)}" ${p.uuid === pollUuid ? "selected" : ""}>${this.esc(p.label)}</option>`)
        .join("");
      const $row = $(`
        <div class="wag-poll-lang-row" style="display:grid;grid-template-columns:1fr 2fr auto auto;gap:6px;align-items:center;margin-bottom:6px;">
          <select class="form-control input-sm wag-poll-lang-language"><option value="">${__("Language")}</option>${langOptions}</select>
          <select class="form-control input-sm wag-poll-lang-poll"><option value="">${__("Poll")}</option>${pollOptions}</select>
          <label style="white-space:nowrap;"><input type="radio" name="wag-poll-lang-default" class="wag-poll-lang-default" ${isDefault ? "checked" : ""}> ${__("Default")}</label>
          <button class="btn btn-xs btn-default wag-poll-lang-remove">✕</button>
        </div>
      `);
      $row.find(".wag-poll-lang-remove").on("click", () => $row.remove());
      $form.find("#wag-poll-lang-rows").append($row);
    };

    this.refresh_poll_lang_option_lists = () => {
      const langOptions = (lang) => (this._languageCache || [])
        .map((l) => `<option value="${this.esc(l.name)}" ${l.name === lang ? "selected" : ""}>${this.esc(l.language_name || l.name)}</option>`)
        .join("");
      const pollOptions = (pollUuid) => (this._allPollsCache || [])
        .map((p) => `<option value="${this.esc(p.uuid)}" ${p.uuid === pollUuid ? "selected" : ""}>${this.esc(p.label)}</option>`)
        .join("");
      $form.find(".wag-poll-lang-row").each((i, el) => {
        const $el = $(el);
        const curLang = $el.find(".wag-poll-lang-language").val();
        const curPoll = $el.find(".wag-poll-lang-poll").val();
        $el.find(".wag-poll-lang-language").html(`<option value="">${__("Language")}</option>${langOptions(curLang)}`);
        $el.find(".wag-poll-lang-poll").html(`<option value="">${__("Poll")}</option>${pollOptions(curPoll)}`);
      });
    };

    $form.find("#wag-poll-lang-add-row").on("click", () => {
      this.addPollLangRow(null, null, $form.find(".wag-poll-lang-default:checked").length === 0);
    });

    $form.find("#wag-send-poll-multi-lang").on("change", (e) => {
      const multi = e.target.checked;
      $form.find("#wag-send-poll-single-wrap").toggle(!multi);
      $form.find("#wag-send-poll-multi-wrap").toggle(multi);
      if (multi && !$form.find(".wag-poll-lang-row").length) {
        this.addPollLangRow(null, null, true);
      }
    });

    $form.find("#wag-send-poll-new-toggle").on("click", () => {
      $form.find("#wag-send-poll-new-form").toggle();
    });

    $form.find("#wag-poll-new-create").on("click", () => {
      const label = $form.find("#wag-poll-new-label").val();
      const text = $form.find("#wag-poll-new-text").val();
      const options = $form.find(".wag-poll-option").map((i, el) => $(el).val()).get().filter(Boolean);
      const multi = $form.find("#wag-poll-new-multi").is(":checked");
      if (!label || !text || options.length < 2) {
        frappe.show_alert({ message: __("Label, question and at least 2 options are required."), indicator: "orange" });
        return;
      }
      this.call("create_poll", {
        label: label, poll_text: text, options: JSON.stringify(options), allow_multiple_answer: multi,
      }).then((poll) => {
        frappe.show_alert({ message: __("Poll created"), indicator: "green" });
        $form.find("#wag-send-poll-new-form").hide();
        loadPolls(poll.uuid);
      });
    });

    $form.find("#wag-send-target-type").on("change", (e) => {
      const v = e.target.value;
      $form.find("#wag-send-target-field").toggle(v === "Group" || v === "Collection");
      $form.find("#wag-send-geo-field").toggle(v === "Geo");
      this.refresh_send_target_options();
      this.refresh_wave_field_visibility($form);
    });

    $form.find("#wag-send-type").on("change", (e) => {
      const v = e.target.value;
      $form.find("#wag-send-media-field").toggle(v === "Media");
      $form.find("#wag-send-flow-field").toggle(v === "Flow");
      $form.find("#wag-send-poll-field").toggle(v === "Poll");
      $form.find("#wag-send-body-field").toggle(v === "Text" || v === "Media");
    });

    $form.find("#wag-send-mode").on("change", (e) => {
      $form.find("#wag-send-schedule-field").toggle(e.target.value === "schedule");
    });

    const previewGeoCount = () => {
      const district = $form.find("#wag-send-geo-district").val() || null;
      const city = $form.find("#wag-send-geo-city").val() || null;
      const state = $form.find("#wag-send-geo-state").val() || null;
      const school = $form.find("#wag-send-geo-school").val() || null;
      if (!district && !city && !state && !school) {
        $form.find("#wag-send-geo-preview").text("");
        this.refresh_wave_field_visibility($form);
        return;
      }
      this.call("get_wa_groups_for_filter", { district, city, state, school }).then((rows) => {
        $form.find("#wag-send-geo-preview").text(`${rows.length} ${__("groups match")}`);
        $form.data("geoMatchCount", rows.length);
        this.refresh_wave_field_visibility($form);
      });
    };
    $form.find("#wag-send-geo-district, #wag-send-geo-city, #wag-send-geo-state, #wag-send-geo-school")
      .on("change", previewGeoCount);

    $form.find("#wag-send-btn").on("click", () => this.submit_send($form));

    this.load_draft_select($form);
    $form.find("#wag-send-draft-select").on("change", (e) => {
      const batchName = e.target.value || null;
      this.state.send_draft_loaded = batchName;
      if (batchName) {
        this.load_draft_into_form($form, batchName);
      } else {
        this.clear_send_form($form);
      }
    });

    this.load_recent_campaigns(false);
    this._$sendForm = $form;
  }

  apply_pending_draft_load($form) {
    if (!this.state.send_draft_loaded) return;
    $form.find("#wag-send-draft-select").val(this.state.send_draft_loaded);
    this.load_draft_into_form($form, this.state.send_draft_loaded);
  }

  load_draft_select($form) {
    this.call("list_send_batches", { filters: { send_status: ["Draft"] }, start: 0, page_length: 50 }).then((res) => {
      const $select = $form.find("#wag-send-draft-select");
      const current = this.state.send_draft_loaded || "";
      $select.find("option:not(:first)").remove();
      (res.rows || []).forEach((r) => {
        const label = `${r.send_kind} — ${r.target_label || r.name}`;
        $select.append(`<option value="${this.esc(r.name)}">${this.esc(label)}</option>`);
      });
      if (current) $select.val(current);
    });
  }

  clear_send_form($form) {
    $form.find("#wag-send-target-type").val("Group").trigger("change");
    $form.find("#wag-send-type").val("Text").trigger("change");
    $form.find("#wag-send-group").val("");
    $form.find("#wag-send-geo-state, #wag-send-geo-district, #wag-send-geo-city, #wag-send-geo-school").val("");
    $form.find("#wag-send-body").val("");
    $form.find("#wag-send-media-url").val("");
    $form.find("#wag-send-flow-id").val("");
    $form.find("#wag-send-poll-select").val("");
    $form.find("#wag-send-poll-multi-lang").prop("checked", false).trigger("change");
    $form.find("#wag-poll-lang-rows").empty();
    $form.find("#wag-send-mode").val("now").trigger("change");
  }

  load_draft_into_form($form, batchName) {
    frappe.db.get_doc("WA Send Batch", batchName).then((doc) => {
      $form.find("#wag-send-target-type").val(doc.target_type).trigger("change");
      $form.find("#wag-send-type").val(doc.send_kind).trigger("change");

      if (doc.target_type === "Group" || doc.target_type === "Collection") {
        this.refresh_send_target_options();
        setTimeout(() => {
          $form.find("#wag-send-group").val(doc.target_type === "Group" ? doc.wa_group : doc.wa_group_collection);
        }, 300);
      } else {
        $form.find("#wag-send-geo-state").val(doc.state || "");
        $form.find("#wag-send-geo-district").val(doc.district || "");
        $form.find("#wag-send-geo-city").val(doc.city || "");
        $form.find("#wag-send-geo-school").val(doc.school || "");
      }

      $form.find("#wag-send-body").val(doc.message_body || "");
      $form.find("#wag-send-media-url").val(doc.media_url || "");
      $form.find("#wag-send-flow-id").val(doc.glific_flow_id || "");
      $form.find("#wag-send-wave-size").val(doc.wave_size || "");
      $form.find("#wag-send-wave-gap").val(doc.wave_gap_minutes != null ? doc.wave_gap_minutes : "");

      if (doc.send_kind === "Poll") {
        $form.find("#wag-send-poll-multi-lang").prop("checked", !!doc.is_multi_language_poll).trigger("change");
        if (doc.is_multi_language_poll) {
          $form.find("#wag-poll-lang-rows").empty();
          (doc.poll_languages || []).forEach((row) => {
            this.addPollLangRow(row.language, row.poll_uuid, !!row.is_default);
          });
        } else {
          setTimeout(() => $form.find("#wag-send-poll-select").val(doc.poll_uuid || ""), 300);
        }
      }

      frappe.show_alert({ message: __("Draft loaded"), indicator: "blue" });
    });
  }

  refresh_wave_field_visibility($form) {
    const targetType = $form.find("#wag-send-target-type").val();
    const show = targetType === "Collection" || (targetType === "Geo" && (($form.data("geoMatchCount") || 0) > 1));
    $form.find("#wag-send-wave-field").toggle(show);
  }

  refresh_send_target_options() {
    const $form = this._$sendForm || this.$root.find('[data-panel="send"]');
    const targetType = $form.find("#wag-send-target-type").val();
    const $select = $form.find("#wag-send-group");
    $select.empty().append(`<option value="">${__("Select...")}</option>`);

    if (targetType === "Group") {
      (this._allGroupsCache || []).forEach((g) => {
        $select.append(`<option value="${this.esc(g.name)}">${this.esc(g.group_name || g.name)}</option>`);
      });
    } else if (targetType === "Collection") {
      frappe.db.get_list("WA Group Collection", { fields: ["name", "collection_name"], limit: 500 }).then((rows) => {
        rows.forEach((c) => {
          $select.append(`<option value="${this.esc(c.name)}">${this.esc(c.collection_name || c.name)}</option>`);
        });
      });
    }
  }

  submit_send($form) {
    const $btn = $form.find("#wag-send-btn");
    if ($btn.data("sending")) return;

    const targetType = $form.find("#wag-send-target-type").val();
    const sendType = $form.find("#wag-send-type").val();
    const mode = $form.find("#wag-send-mode").val();
    const isMultiLangPoll = sendType === "Poll" && $form.find("#wag-send-poll-multi-lang").is(":checked");
    const loadedDraftName = this.state.send_draft_loaded || null;

    const mediaFile = this._sendMediaAttach ? this._sendMediaAttach.get_value() : null;

    const args = {
      target_type: targetType,
      send_kind: sendType,
      wa_group: null,
      wa_group_collection: null,
      district: null, city: null, state: null, school: null,
      message_body: $form.find("#wag-send-body").val() || null,
      media_file: sendType === "Media" ? (mediaFile || null) : null,
      media_url: sendType === "Media" && !mediaFile ? ($form.find("#wag-send-media-url").val() || null) : null,
      glific_flow_id: sendType === "Flow" ? ($form.find("#wag-send-flow-id").val() || null) : null,
      is_multi_language_poll: isMultiLangPoll ? 1 : 0,
      poll_uuid: isMultiLangPoll ? null : ($form.find("#wag-send-poll-select").val() || null),
      wave_size: parseInt($form.find("#wag-send-wave-size").val(), 10) || null,
      wave_gap_minutes: $form.find("#wag-send-wave-gap").val() !== "" ? parseInt($form.find("#wag-send-wave-gap").val(), 10) : null,
    };

    if (loadedDraftName) args.batch_name = loadedDraftName;

    if (targetType === "Group" || targetType === "Collection") {
      const targetName = $form.find("#wag-send-group").val() || null;
      if (!targetName) {
        frappe.show_alert({ message: __("Select a target first."), indicator: "orange" });
        return;
      }
      if (targetType === "Group") args.wa_group = targetName;
      else args.wa_group_collection = targetName;
    } else {
      args.district = $form.find("#wag-send-geo-district").val() || null;
      args.city = $form.find("#wag-send-geo-city").val() || null;
      args.state = $form.find("#wag-send-geo-state").val() || null;
      args.school = $form.find("#wag-send-geo-school").val() || null;
      if (!args.district && !args.city && !args.state && !args.school) {
        frappe.show_alert({ message: __("Pick at least one of state, district, city or school."), indicator: "orange" });
        return;
      }
    }

    if (sendType === "Flow" && !args.glific_flow_id) {
      frappe.show_alert({ message: __("Glific Flow ID is required for a Flow send."), indicator: "orange" });
      return;
    }
    if (sendType === "Media" && !args.media_file && !args.media_url) {
      frappe.show_alert({ message: __("Attach a file or paste a Media URL first."), indicator: "orange" });
      return;
    }

    let langRows = [];
    if (isMultiLangPoll) {
      langRows = $form.find(".wag-poll-lang-row").map((i, el) => {
        const $el = $(el);
        return {
          language: $el.find(".wag-poll-lang-language").val(),
          poll_uuid: $el.find(".wag-poll-lang-poll").val(),
          is_default: $el.find(".wag-poll-lang-default").is(":checked"),
        };
      }).get().filter((r) => r.language && r.poll_uuid);
      if (langRows.length < 1) {
        frappe.show_alert({ message: __("Add at least one language/poll pair."), indicator: "orange" });
        return;
      }
    } else if (sendType === "Poll" && !args.poll_uuid) {
      frappe.show_alert({ message: __("Select or create a poll first."), indicator: "orange" });
      return;
    }

    if (mode === "schedule" && !$form.find("#wag-send-scheduled-at").val()) {
      frappe.show_alert({ message: __("Pick a scheduled time first."), indicator: "orange" });
      return;
    }

    $btn.data("sending", true).prop("disabled", true).text(__("Submitting..."));

    const runWithLangRows = (batchName) => {
      if (!isMultiLangPoll) return Promise.resolve();
      return this.call("set_batch_poll_languages", { batch_name: batchName, rows: JSON.stringify(langRows) });
    };

    const draftArgs = { ...args };
    draftArgs.poll_languages = null;

    this.call("save_send_batch_draft", draftArgs)
      .then((r) => runWithLangRows(r.name).then(() => r))
      .then((r) => {
        if (mode === "now") {
          return this.call("schedule_send_batch", { batch_name: r.name });
        }
        if (mode === "schedule") {
          return this.call("schedule_send_batch", {
            batch_name: r.name,
            scheduled_send_at: $form.find("#wag-send-scheduled-at").val(),
          });
        }
        return r;
      })
      .then((r) => {
        frappe.show_alert({ message: `${__("Done")}: ${r.name} (${r.status})`, indicator: "green" });
        this.state.send_draft_loaded = mode === "draft" ? r.name : null;
        this.load_draft_select($form);
        this.load_recent_campaigns(false);
        if (mode !== "draft") {
          $form.find("#wag-send-draft-select").val("");
        }
      })
      .always(() => {
        $btn.data("sending", false).prop("disabled", false).text(__("Submit"));
      });
  }

  load_recent_campaigns(append) {
    const s = this.state.send_recent;
    const $wrap = this.$root.find("#wag-recent-campaigns");
    const $loadMore = this.$root.find("#wag-send-recent-pager-more");

    this.call("list_send_batches", { start: s.start, page_length: s.page_length }).then((res) => {
      if (!append) $wrap.empty();
      if (!res.rows.length && !append) {
        $wrap.html(`<div class="wag-empty">${__("No sends yet.")}</div>`);
        if ($loadMore.length) $loadMore.hide();
        return;
      }
      let $table = $wrap.find("table.wag-table");
      if (!$table.length) {
        $table = $(`
          <table class="wag-table">
            <thead><tr>
              <th>${__("Target")}</th><th>${__("Type")}</th><th>${__("Status")}</th>
              <th>${__("Message")}</th>
              <th>${__("Scheduled")}</th><th>${__("Reach")}</th><th></th>
            </tr></thead>
            <tbody></tbody>
          </table>
        `);
        $wrap.append($table);
      }
      const $tbody = $table.find("tbody");
      res.rows.forEach((r) => {
        const target = r.target_label || r.wa_group || r.wa_group_collection
          || [r.state, r.district, r.city, r.school].filter(Boolean).join(" / ") || "";
        const $tr = $(`
          <tr>
            <td>${this.esc(target)}</td>
            <td>${r.send_kind}</td>
            <td>${this.badge(r.status, this.status_color(r.status))}</td>
            <td class="wag-td-wrap">${this.esc(r.message_body || r.media_url || r.glific_flow_id || (r.send_kind === "Poll" ? r.poll_uuid || "" : ""))}</td>
            <td>${r.scheduled_send_at ? frappe.datetime.str_to_user(r.scheduled_send_at) : ""}</td>
            <td>${r.total_groups || ""}</td>
            <td>${r.status === "Draft" ? `<button class="btn btn-xs btn-default wag-recent-edit-draft">${__("Edit")}</button>` : ""}</td>
          </tr>
        `);
        $tr.find(".wag-recent-edit-draft").on("click", () => {
          this.state.send_draft_loaded = r.name;
          this.render_send();
        });
        $tbody.append($tr);
      });
      if ($loadMore.length) $loadMore.toggle(res.has_more);
    });
  }

  status_color(status) {
    if (status === "Sent" || status === "Delivered" || status === "Read") return "success";
    if (status === "Failed" || status === "Cancelled" || status === "Partially Failed") return "failed";
    if (status === "Scheduled" || status === "Throttling" || status === "Pending") return "ready";
    return "neutral";
  }

  turn_status_color(status) {
    const map = { Open: "neutral", Drafted: "pending", "Ready To Go": "ready", Sent: "success", Discarded: "failed", Failed: "failed", Ignored: "neutral" };
    return map[status] || "neutral";
  }

  badge(text, color) {
    return `<span class="wag-badge wag-badge-${color}">${this.esc(text || "")}</span>`;
  }
}