frappe.pages['vocallabs_test_call'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Voice AI Calling Hub',
        single_column: true
    });

    $(wrapper).find('.page-head').hide();
    wrapper.vocallabs_app = new VocallabsDashboard(wrapper, page);
};

function getVoiceAINavbarHTML(activePage) {
    return `
    <div class="voice-ai-common-navbar">
        <div class="voice-ai-brand" id="nav-brand-home">
            <div class="voice-ai-brand-icon">
                <i class="fa fa-microphone"></i>
            </div>
            <div>
                <div class="voice-ai-brand-text">TAP Voice AI Central</div>
                <div class="voice-ai-brand-sub">The Apprentice Project Calling Operations</div>
            </div>
        </div>

        <div class="voice-ai-nav-links">
            <button type="button" class="voice-ai-nav-btn ${activePage === 'home' ? 'active' : ''}" id="nav-btn-home">
                <i class="fa fa-home"></i> 🏠 Home Hub
            </button>
            <button type="button" class="voice-ai-nav-btn ${activePage === 'dashboard' ? 'active' : ''}" id="nav-btn-dashboard">
                <i class="fa fa-bar-chart"></i> 📊 Analytics Dashboard
            </button>
            <button type="button" class="voice-ai-nav-btn ${activePage === 'studio' ? 'active' : ''}" id="nav-btn-studio">
                <i class="fa fa-flask"></i> 🧪 Testing Studio
            </button>
            
            <div class="voice-ai-nav-divider"></div>

            <button type="button" class="voice-ai-nav-btn" id="nav-btn-scripts">
                <i class="fa fa-file-text-o"></i> 📜 Scripts Library
            </button>
            <button type="button" class="voice-ai-nav-btn" id="nav-btn-settings">
                <i class="fa fa-cog"></i> ⚙️ Voice Settings
            </button>
        </div>
    </div>
    `;
}

function bindVoiceAINavbarEvents($w) {
    $w.on('click', '#nav-brand-home, #nav-btn-home', function() {
        frappe.set_route('voice_ai_home');
    });
    $w.on('click', '#nav-btn-dashboard', function() {
        frappe.set_route('voice_campaign_dashboard');
    });
    $w.on('click', '#nav-btn-studio', function() {
        frappe.set_route('vocallabs_test_call');
    });
    $w.on('click', '#nav-btn-scripts', function() {
        frappe.set_route('List', 'ParentCallConfig');
    });
    $w.on('click', '#nav-btn-settings', function() {
        frappe.set_route('Form', 'VoiceAgentSettings');
    });
}

class VocallabsDashboard {
    constructor(wrapper, page) {
        this.wrapper = wrapper;
        this.page = page;
        this.$wrapper = $(wrapper);
        this.settings = null;
        this.scripts = [];
        this.stats = null;
        this.recentLogs = [];
        this.selectedScript = null;
        this.detectedVariables = {};
        this.isManualEditMode = false;
        this.callHistory = this.loadCallHistory();

        this.init();
    }

    init() {
        this.$wrapper.find('.page-head').hide();
        this.setupLayout();
        this.fetchInitialData();
        this.renderCallHistory();
    }

    loadCallHistory() {
        try {
            var raw = localStorage.getItem('vocallabs_test_call_history');
            return raw ? JSON.parse(raw) : [];
        } catch(e) {
            return [];
        }
    }

    saveCallHistory(entry) {
        this.callHistory.unshift(entry);
        if (this.callHistory.length > 8) {
            this.callHistory = this.callHistory.slice(0, 8);
        }
        try {
            localStorage.setItem('vocallabs_test_call_history', JSON.stringify(this.callHistory));
        } catch(e) {}
        this.renderCallHistory();
    }

    setupLayout() {
        var html = `
        <div class="vocallabs-dashboard-container">
            
            <!-- COMMON TOP NAVBAR -->
            ${getVoiceAINavbarHTML('studio')}

            <!-- Top Dashboard Header -->
            <div class="dashboard-header d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h2 class="dashboard-title mb-1">
                        <i class="fa fa-microphone-slash text-primary mr-2"></i> VocalLabs AI Voice Calling Hub
                    </h2>
                    <p class="text-muted mb-0" style="font-size:13.5px;">
                        Manage campaign prompt scripts, monitor automated escalation calls, and launch interactive test calls.
                    </p>
                </div>
                <div class="d-flex align-items-center">
                    <span id="settings-status-badge">
                        <span class="indicator-pill gray">Checking...</span>
                    </span>
                </div>
            </div>

            <!-- Top Metric Stat Cards -->
            <div class="row metric-cards-row mb-4">
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="card metric-card border-0 shadow-sm p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="metric-label text-uppercase text-muted">Campaign Scripts</span>
                                <h3 class="metric-value font-weight-bold mb-0 text-dark" id="stat-total-scripts">--</h3>
                            </div>
                            <div class="metric-icon-box bg-blue-soft text-primary">
                                <i class="fa fa-file-text-o"></i>
                            </div>
                        </div>
                        <div class="mt-2 text-xs text-muted" id="stat-scripts-subtext">
                            Hindi, English, Marathi, Punjabi
                        </div>
                    </div>
                </div>

                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="card metric-card border-0 shadow-sm p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="metric-label text-uppercase text-muted">Total Voice Calls</span>
                                <h3 class="metric-value font-weight-bold mb-0 text-dark" id="stat-total-calls">--</h3>
                            </div>
                            <div class="metric-icon-box bg-green-soft text-success">
                                <i class="fa fa-phone"></i>
                            </div>
                        </div>
                        <div class="mt-2 text-xs text-success">
                            <i class="fa fa-check-circle mr-1"></i> Escalation & Test Triggers
                        </div>
                    </div>
                </div>

                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="card metric-card border-0 shadow-sm p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="metric-label text-uppercase text-muted">Students Tracked</span>
                                <h3 class="metric-value font-weight-bold mb-0 text-dark" id="stat-total-students">--</h3>
                            </div>
                            <div class="metric-icon-box bg-purple-soft text-purple">
                                <i class="fa fa-users"></i>
                            </div>
                        </div>
                        <div class="mt-2 text-xs text-muted">
                            Active in Summer Program
                        </div>
                    </div>
                </div>

                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="card metric-card border-0 shadow-sm p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="metric-label text-uppercase text-muted">VocalLabs API</span>
                                <h3 class="metric-value font-weight-bold mb-0 text-success" id="stat-api-status">Live</h3>
                            </div>
                            <div class="metric-icon-box bg-emerald-soft text-success">
                                <i class="fa fa-bolt"></i>
                            </div>
                        </div>
                        <div class="mt-2 text-xs text-muted text-truncate" id="stat-api-subtext">
                            https://api.superflow.run
                        </div>
                    </div>
                </div>
            </div>

            <!-- Navigation Tabs -->
            <ul class="nav nav-tabs dashboard-tabs mb-4" id="dashboardTabs" role="tablist">
                <li class="nav-item">
                    <a class="nav-link active font-weight-bold" id="tab-studio-link" data-toggle="tab" href="#tab-studio" role="tab">
                        <i class="fa fa-play-circle mr-1 text-primary"></i> Live Test Studio & Playground
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link font-weight-bold" id="tab-scripts-link" data-toggle="tab" href="#tab-scripts" role="tab">
                        <i class="fa fa-th-large mr-1 text-secondary"></i> Campaign Scripts Explorer (<span id="tab-scripts-count">0</span>)
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link font-weight-bold" id="tab-logs-link" data-toggle="tab" href="#tab-logs" role="tab">
                        <i class="fa fa-history mr-1 text-secondary"></i> Activity & Audit Logs
                    </a>
                </li>
            </ul>

            <!-- Tab Content -->
            <div class="tab-content" id="dashboardTabsContent">
                
                <!-- TAB 1: LIVE TEST STUDIO -->
                <div class="tab-pane fade show active" id="tab-studio" role="tabpanel">
                    <div class="row test-content-grid">
                        <!-- Left Column: Form Controls -->
                        <div class="col-md-5">
                            <div class="card p-4 shadow-sm border-0 mb-4 form-card">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <h5 class="card-title text-dark mb-0 font-weight-bold">
                                        1. Target & Script Source
                                    </h5>
                                    <span class="badge badge-light border text-muted" style="font-size:11px;">Test Setup</span>
                                </div>

                                <div class="form-group mb-3">
                                    <label class="form-label font-weight-bold text-xs text-uppercase text-muted">Target Phone Number <span class="text-danger">*</span></label>
                                    <div class="input-group">
                                        <div class="input-group-prepend">
                                            <span class="input-group-text bg-white border-right-0"><i class="fa fa-phone text-muted"></i></span>
                                        </div>
                                        <input type="text" id="target-phone" class="form-control border-left-0" placeholder="e.g. 9876543210 or +919876543210" value="+918595701049">
                                    </div>
                                    <small class="form-text text-muted">10-digit numbers automatically get prefixed with +91.</small>
                                </div>

                                <div class="form-group mb-3">
                                    <label class="form-label font-weight-bold text-xs text-uppercase text-muted">Student / Contact Name</label>
                                    <input type="text" id="contact-name" class="form-control" placeholder="e.g. Aarav Sharma" value="Nigam">
                                </div>

                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label class="form-label font-weight-bold text-xs text-uppercase text-muted">Language Filter</label>
                                        <select id="select-language" class="form-control form-select">
                                            <option value="All">🌐 All Languages</option>
                                            <option value="Hindi">🇮🇳 Hindi</option>
                                            <option value="English">🇬🇧 English</option>
                                            <option value="Marathi">🚩 Marathi</option>
                                            <option value="Punjabi">🌾 Punjabi</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label class="form-label font-weight-bold text-xs text-uppercase text-muted">Resolved Agent</label>
                                        <div class="form-control bg-light text-truncate" id="resolved-agent-display" style="font-size: 11px; line-height: 1.8;" title="Resolved Agent">
                                            None
                                        </div>
                                    </div>
                                </div>

                                <div class="form-group mb-3">
                                    <label class="form-label font-weight-bold text-xs text-uppercase text-muted">Select Script Template</label>
                                    <select id="select-script" class="form-control form-select"></select>
                                </div>

                                <!-- Dynamic Variables (2-Column Grid) -->
                                <div id="dynamic-variables-section" class="border rounded p-3 bg-light mb-3" style="display:none;">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <label class="font-weight-bold text-secondary mb-0" style="font-size: 11px; text-transform: uppercase;">
                                            <i class="fa fa-sliders mr-1"></i> Detected Script Variables
                                        </label>
                                        <span class="badge badge-light border text-muted" id="var-count-badge">0 variables</span>
                                    </div>
                                    <div class="row" id="dynamic-variables-container"></div>
                                </div>

                                <!-- Advanced toggle -->
                                <div class="advanced-section mt-2">
                                    <button type="button" class="btn btn-link text-secondary font-weight-bold p-0 my-1 d-inline-flex align-items-center" id="btn-toggle-advanced" style="text-decoration:none; font-size:12px; cursor:pointer;">
                                        <i class="fa fa-cog mr-1"></i> Advanced: Custom Overrides (Agent / Prospect ID)
                                    </button>
                                    <div id="advanced-collapse" style="display:none;" class="mt-2">
                                        <div class="p-3 bg-light border rounded">
                                            <div class="form-group mb-2">
                                                <label class="text-muted text-xs">Custom Agent ID Override:</label>
                                                <input type="text" id="override-agent-id" class="form-control form-control-sm" placeholder="e.g. ea8e5749-83a3-47f6-9935-d584ba04f1f0">
                                            </div>
                                            <div class="form-group mb-0">
                                                <label class="text-muted text-xs">Known Prospect ID Override:</label>
                                                <input type="text" id="override-prospect-id" class="form-control form-control-sm" placeholder="e.g. f5c91015-138d-4734-ab32-65ea17c1f404">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                            </div>
                        </div>

                        <!-- Right Column: Live Dual Editor, Trigger Button & Call History -->
                        <div class="col-md-7">
                            <div class="sticky-right-panel">
                                <div class="card p-4 shadow-sm border-0 mb-3 preview-card">
                                    
                                    <!-- SECTION 2A: WELCOME MESSAGE (INITIAL GREETING) -->
                                    <div class="welcome-message-box mb-3 pb-3 border-bottom">
                                        <div class="d-flex justify-content-between align-items-center mb-1">
                                            <label class="font-weight-bold text-dark mb-0 text-sm">
                                                💬 1. Welcome Message (Initial Greeting)
                                            </label>
                                            <span class="badge badge-info" id="welcome-char-count" style="font-family:monospace; font-size:10.5px;">0 chars</span>
                                        </div>
                                        <p class="text-muted mb-2" style="font-size:11.5px;">
                                            Phone connect hote hi AI sabse pehle yeh opening line bolega <code class="text-primary font-weight-bold">({{welcome_greeting}})</code>:
                                        </p>
                                        
                                        <!-- Welcome chips -->
                                        <div class="variable-chips mb-2">
                                            <button type="button" class="btn btn-xs btn-outline-secondary welcome-chip-btn" data-insert="{student_name}">+ student_name</button>
                                            <button type="button" class="btn btn-xs btn-outline-secondary welcome-chip-btn" data-insert="TAP Buddy">+ TAP Buddy</button>
                                            <button type="button" class="btn btn-xs btn-outline-secondary welcome-chip-btn" data-insert="Vidya">+ Vidya</button>
                                        </div>

                                        <textarea id="welcome-editor" class="form-control mb-1" rows="2" style="font-size:12.5px; line-height:1.4;" placeholder="e.g. नमस्कार... मैं TAP Buddy की तरफ़ से बात कर रही हूँ... क्या मैं {student_name} के माता-पिता से बात कर रही हूँ?">नमस्कार... मैं TAP Buddy की तरफ़ से बात कर रही हूँ... क्या मैं {student_name} के माता-पिता से बात कर रही हूँ?</textarea>
                                    </div>

                                    <!-- SECTION 2B: MAIN VOICE PROMPT / AGENT CONTEXT -->
                                    <div class="agent-prompt-box mb-2">
                                        <div class="d-flex justify-content-between align-items-center mb-1">
                                            <label class="font-weight-bold text-dark mb-0 text-sm">
                                                🎙️ 2. Agent Voice Prompt Context (Reason for Call)
                                            </label>
                                            <span class="badge badge-dark" id="char-count" style="font-family:monospace; font-size:10.5px;">0 chars</span>
                                        </div>
                                        <p class="text-muted mb-2" style="font-size:11.5px;">
                                            AI caller is prompt context ko conversation me explain karega <code class="text-secondary font-weight-bold">({{status}})</code>:
                                        </p>

                                        <!-- Variable insert chips -->
                                        <div class="variable-chips mb-2">
                                            <span class="text-muted text-xs mr-1"><i class="fa fa-magic text-warning mr-1"></i>Insert:</span>
                                            <button type="button" class="btn btn-xs btn-outline-secondary chip-btn" data-insert="{student_name}">+ student_name</button>
                                            <button type="button" class="btn btn-xs btn-outline-secondary chip-btn" data-insert="{week}">+ week</button>
                                            <button type="button" class="btn btn-xs btn-outline-secondary chip-btn" data-insert="{task_name}">+ task_name</button>
                                            <button type="button" class="btn btn-xs btn-outline-secondary chip-btn" data-insert="{streak_count}">+ streak_count</button>
                                            <button type="button" class="btn btn-xs btn-outline-secondary chip-btn" data-insert="{grace_deadline}">+ grace_deadline</button>
                                        </div>

                                        <!-- Editable prompt textarea -->
                                        <div class="form-group mb-2 position-relative">
                                            <textarea id="prompt-editor" class="form-control prompt-textarea" rows="5" placeholder="Type or paste your voice prompt context here..."></textarea>
                                        </div>

                                        <div class="d-flex justify-content-between align-items-center mb-3">
                                            <button type="button" id="btn-save-as-script" class="btn btn-sm btn-outline-primary">
                                                <i class="fa fa-save mr-1"></i> Save as New Script in DB
                                            </button>
                                            <button type="button" id="btn-reset-prompt" class="btn btn-sm btn-link text-muted p-0">
                                                <i class="fa fa-undo mr-1"></i> Reset to Template
                                            </button>
                                        </div>
                                    </div>

                                    <button id="btn-trigger-call" class="btn btn-primary btn-lg btn-block font-weight-bold shadow-sm trigger-btn">
                                        <i class="fa fa-phone mr-2"></i> Launch Test Call Now
                                    </button>

                                    <div id="call-result-container" class="mt-3" style="display:none;"></div>
                                </div>

                                <!-- Recent Test Calls Log Card -->
                                <div class="card p-3 shadow-sm border-0 recent-history-card">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <h6 class="font-weight-bold text-dark mb-0" style="font-size:13px;">
                                            <i class="fa fa-history text-secondary mr-1"></i> Recent Session Test Calls
                                        </h6>
                                        <button type="button" id="btn-clear-history" class="btn btn-link btn-xs text-muted p-0" style="font-size:11px;">Clear</button>
                                    </div>
                                    <div id="call-history-list">
                                        <div class="text-muted text-xs font-italic py-2" id="empty-history-msg">No calls made in this session yet.</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- TAB 2: CAMPAIGN SCRIPTS EXPLORER -->
                <div class="tab-pane fade" id="tab-scripts" role="tabpanel">
                    <div class="card p-4 shadow-sm border-0 mb-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h5 class="font-weight-bold mb-1">Parent Call Campaign Scripts Library</h5>
                                <p class="text-muted text-xs mb-0">Browse all 32 pre-configured campaign templates. Click any script to inspect or load directly into Studio.</p>
                            </div>
                            <div class="d-flex align-items-center">
                                <input type="text" id="scripts-search-input" class="form-control form-control-sm mr-2" placeholder="Search scripts..." style="width:200px;">
                                <select id="scripts-filter-lang" class="form-control form-control-sm" style="width:140px;">
                                    <option value="All">All Languages</option>
                                    <option value="Hindi">Hindi</option>
                                    <option value="English">English</option>
                                    <option value="Marathi">Marathi</option>
                                    <option value="Punjabi">Punjabi</option>
                                </select>
                            </div>
                        </div>

                        <div class="row" id="scripts-grid-container"></div>
                    </div>
                </div>

                <!-- TAB 3: ACTIVITY & AUDIT LOGS -->
                <div class="tab-pane fade" id="tab-logs" role="tabpanel">
                    <div class="card p-4 shadow-sm border-0 mb-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h5 class="font-weight-bold mb-1">Program Event & Voice Call Logs</h5>
                                <p class="text-muted text-xs mb-0">Live audit trail of escalation voice calls and triggers registered in <code>ProgramEventLog</code>.</p>
                            </div>
                            <a href="/app/programeventlog" target="_blank" class="btn btn-sm btn-outline-secondary">
                                Open Full DocType List &rarr;
                            </a>
                        </div>

                        <div class="table-responsive">
                            <table class="table table-hover table-striped text-xs" style="font-size:12px;">
                                <thead class="thead-light">
                                    <tr>
                                        <th>Timestamp</th>
                                        <th>Event Type</th>
                                        <th>Student</th>
                                        <th>Batch</th>
                                        <th>Details / Spoken Summary</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody id="event-logs-table-body">
                                    <tr>
                                        <td colspan="6" class="text-center text-muted py-4">Loading logs...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

            </div>
        </div>
        `;

        $(this.wrapper).find('.layout-main-section').html(html);
        this.bindEvents();
    }

    fetchInitialData() {
        var me = this;
        frappe.call({
            method: 'tap_lms.tap_lms.page.vocallabs_test_call.vocallabs_test_call.get_initial_data',
            callback: function(r) {
                if (r.message) {
                    me.settings = r.message.settings;
                    me.scripts = r.message.scripts || [];
                    me.stats = r.message.stats || {};
                    me.recentLogs = r.message.recent_logs || [];
                    
                    me.renderSettingsStatus();
                    me.renderStats();
                    me.populateScriptsDropdown();
                    me.renderScriptsGrid();
                    me.renderLogsTable();
                    me.updateResolvedAgent();
                }
            }
        });
    }

    renderSettingsStatus() {
        var badge = $('#settings-status-badge');
        if (this.settings && this.settings.enabled) {
            badge.html('<span class="indicator-pill green"><span class="indicator-dot green"></span> Vocallabs Active</span>');
        } else {
            badge.html('<span class="indicator-pill red"><span class="indicator-dot red"></span> Vocallabs Disabled</span>');
        }
    }

    renderStats() {
        if (!this.stats) return;
        $('#stat-total-scripts').text(this.stats.total_scripts || '0');
        $('#tab-scripts-count').text(this.stats.total_scripts || '0');
        $('#stat-total-calls').text(this.stats.total_calls || '0');
        $('#stat-total-students').text(this.stats.students_count || '0');

        if (this.stats.lang_counts) {
            var lc = this.stats.lang_counts;
            $('#stat-scripts-subtext').text(`Hindi (${lc.Hindi}), English (${lc.English}), Marathi (${lc.Marathi}), Punjabi (${lc.Punjabi})`);
        }

        if (this.settings && this.settings.service_url) {
            $('#stat-api-subtext').text(this.settings.service_url);
        }
    }

    populateScriptsDropdown() {
        var select = $('#select-script');
        var selectedLang = $('#select-language').val() || 'All';
        var currentVal = select.val();

        select.empty();
        select.append('<option value="__custom__">✍️ Custom Script (Type your own prompt freely)</option>');

        var groups = {
            'Hindi': [],
            'English': [],
            'Marathi': [],
            'Punjabi': [],
            'Other': []
        };

        this.scripts.forEach(function(s) {
            var nameLower = (s.name + ' ' + (s.title || '')).toLowerCase();
            if (nameLower.includes('hindi')) groups['Hindi'].push(s);
            else if (nameLower.includes('english')) groups['English'].push(s);
            else if (nameLower.includes('marathi')) groups['Marathi'].push(s);
            else if (nameLower.includes('punjabi')) groups['Punjabi'].push(s);
            else groups['Other'].push(s);
        });

        var languagesOrder = ['Hindi', 'English', 'Marathi', 'Punjabi', 'Other'];
        if (selectedLang !== 'All' && groups[selectedLang]) {
            languagesOrder = [selectedLang].concat(languagesOrder.filter(l => l !== selectedLang));
        }

        languagesOrder.forEach(function(langKey) {
            var list = groups[langKey];
            if (list && list.length > 0) {
                var optgroup = $(`<optgroup label="📂 ${langKey} Campaigns (${list.length})"></optgroup>`);
                list.forEach(function(s) {
                    var label = s.name;
                    if (s.title && s.title !== s.name) {
                        label = `${s.title} (${s.name})`;
                    }
                    optgroup.append(`<option value="${s.name}">${label}</option>`);
                });
                select.append(optgroup);
            }
        });

        if (currentVal && select.find(`option[value="${currentVal}"]`).length) {
            select.val(currentVal);
        } else if (this.scripts.length > 0) {
            var targetList = (selectedLang !== 'All' && groups[selectedLang] && groups[selectedLang].length > 0) ? groups[selectedLang] : this.scripts;
            select.val(targetList[0].name);
            this.onScriptChange(targetList[0].name);
        } else {
            select.val("__custom__");
            this.onScriptChange("__custom__");
        }
    }

    renderScriptsGrid() {
        var container = $('#scripts-grid-container');
        container.empty();

        if (!this.scripts || this.scripts.length === 0) {
            container.html('<div class="col-12 text-center text-muted py-5">No campaign scripts found. Create one in ParentCallConfig.</div>');
            return;
        }

        var search = ($('#scripts-search-input').val() || '').toLowerCase();
        var langFilter = $('#scripts-filter-lang').val() || 'All';
        var me = this;

        var count = 0;
        this.scripts.forEach(function(s) {
            var name = s.name || '';
            var title = s.title || s.name;
            var text = s.status_text || '';
            var combined = (name + ' ' + title + ' ' + text).toLowerCase();

            if (search && !combined.includes(search)) return;
            if (langFilter !== 'All' && !combined.includes(langFilter.toLowerCase())) return;

            count++;
            var langBadge = "Default";
            var badgeClass = "badge-light text-muted border";
            if (combined.includes('hindi')) { langBadge = "🇮🇳 Hindi"; badgeClass = "badge-warning text-dark"; }
            else if (combined.includes('english')) { langBadge = "🇬🇧 English"; badgeClass = "badge-info"; }
            else if (combined.includes('marathi')) { langBadge = "🚩 Marathi"; badgeClass = "badge-danger"; }
            else if (combined.includes('punjabi')) { langBadge = "🌾 Punjabi"; badgeClass = "badge-success"; }

            var cardHtml = `
                <div class="col-md-4 col-sm-6 mb-3">
                    <div class="card h-100 p-3 script-library-card border shadow-sm">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge ${badgeClass} text-xs font-weight-normal">${langBadge}</span>
                            <span class="text-muted text-xs">${text.length} chars</span>
                        </div>
                        <h6 class="font-weight-bold text-dark text-truncate mb-2" title="${frappe.utils.escape_html(title)}">
                            ${frappe.utils.escape_html(title)}
                        </h6>
                        <p class="text-muted script-body-preview flex-grow-1" style="font-size:11.5px; line-height:1.5;">
                            ${frappe.utils.escape_html(text || 'No status template body configured.')}
                        </p>
                        <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center">
                            <a href="/app/parentcallconfig/${encodeURIComponent(name)}" class="text-muted text-xs" style="text-decoration:none;">
                                <i class="fa fa-edit"></i> Edit Doc
                            </a>
                            <button type="button" class="btn btn-xs btn-primary btn-load-script-studio" data-script="${frappe.utils.escape_html(name)}">
                                <i class="fa fa-play mr-1"></i> Test in Studio
                            </button>
                        </div>
                    </div>
                </div>
            `;
            container.append(cardHtml);
        });

        if (count === 0) {
            container.html('<div class="col-12 text-center text-muted py-5">No matching scripts found for the filter.</div>');
        }

        $('.btn-load-script-studio').on('click', function() {
            var scriptName = $(this).data('script');
            $('#tab-studio-link').tab('show');
            $('#select-script').val(scriptName);
            me.isManualEditMode = false;
            me.onScriptChange(scriptName);
            frappe.show_alert({message: __('Loaded script into Studio.'), indicator: 'green'});
        });
    }

    renderLogsTable() {
        var tbody = $('#event-logs-table-body');
        tbody.empty();

        if (!this.recentLogs || this.recentLogs.length === 0) {
            tbody.html('<tr><td colspan="6" class="text-center text-muted py-4">No recent event logs recorded in database.</td></tr>');
            return;
        }

        var me = this;
        this.recentLogs.forEach(function(l) {
            var d = l.details || {};
            var channel = d.channel || 'N/A';
            var phone = d.phone || 'N/A';
            var rendered = d.rendered_status || (typeof d === 'string' ? d : JSON.stringify(d));

            var row = `
                <tr>
                    <td class="text-muted">${l.created_at ? l.created_at.slice(0, 19) : '--'}</td>
                    <td><span class="badge badge-info">${l.event_type}</span></td>
                    <td><strong>${l.student || '--'}</strong></td>
                    <td><span class="text-muted">${l.batch || '--'}</span></td>
                    <td class="text-truncate" style="max-width:300px;" title="${frappe.utils.escape_html(rendered)}">
                        ${phone !== 'N/A' ? '<strong>' + phone + ':</strong> ' : ''}${frappe.utils.escape_html(rendered)}
                    </td>
                    <td>
                        <a href="/app/programeventlog/${encodeURIComponent(l.name)}" class="btn btn-xs btn-outline-secondary">
                            View Log
                        </a>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });
    }

    bindEvents() {
        var me = this;
        var $w = this.$wrapper;

        bindVoiceAINavbarEvents($w);

        $('#select-script').on('change', function() {
            me.isManualEditMode = false;
            me.onScriptChange($(this).val());
        });

        $('#select-language').on('change', function() {
            var lang = $(this).val();
            me.updateResolvedAgent();
            me.populateScriptsDropdown();
        });

        $('#scripts-search-input, #scripts-filter-lang').on('input change', function() {
            me.renderScriptsGrid();
        });

        $('#target-phone, #contact-name').on('input', function() {
            if (!me.isManualEditMode) {
                me.updateDynamicVariables();
            }
        });

        $('#welcome-editor').on('input', function() {
            me.updateCharCount();
        });

        $('#prompt-editor').on('input', function() {
            me.isManualEditMode = true;
            me.updateCharCount();
        });

        $('.welcome-chip-btn').on('click', function() {
            var token = $(this).data('insert');
            var editor = $('#welcome-editor');
            var val = editor.val();
            editor.val(val + (val.endsWith(' ') || val.length === 0 ? '' : ' ') + token + ' ');
            editor.trigger('input');
        });

        $('.chip-btn').on('click', function() {
            var token = $(this).data('insert');
            var editor = $('#prompt-editor');
            var val = editor.val();
            editor.val(val + (val.endsWith(' ') || val.length === 0 ? '' : ' ') + token + ' ');
            editor.trigger('input');
        });

        $('#btn-reset-prompt').on('click', function() {
            me.isManualEditMode = false;
            me.onScriptChange($('#select-script').val());
        });

        $('#btn-save-as-script').on('click', function() {
            me.openSaveScriptModal();
        });

        $('#btn-toggle-advanced').on('click', function(e) {
            e.preventDefault();
            $('#advanced-collapse').slideToggle(200);
        });

        $('#btn-clear-history').on('click', function() {
            me.callHistory = [];
            localStorage.removeItem('vocallabs_test_call_history');
            me.renderCallHistory();
        });

        $('#btn-trigger-call').on('click', function() {
            me.triggerCall();
        });
    }

    updateResolvedAgent() {
        var lang = $('#select-language').val();
        var agentId = "None";
        if (this.settings) {
            if (this.settings.agents && this.settings.agents.length > 0) {
                var found = this.settings.agents.find(function(a) {
                    return a.language && a.language.toLowerCase() === lang.toLowerCase();
                });
                if (found) agentId = found.agent_id;
            }
            if (agentId === "None" && this.settings.fallback_agent_id) {
                agentId = this.settings.fallback_agent_id + " (Default)";
            }
        }
        $('#resolved-agent-display').text(agentId).attr('title', agentId);
    }

    onScriptChange(scriptName) {
        var me = this;
        var studentName = $('#contact-name').val() || "Nigam";

        if (!scriptName || scriptName === '__custom__') {
            this.selectedScript = null;
            $('#dynamic-variables-section').hide();
            if (!this.isManualEditMode) {
                $('#prompt-editor').val(`Hello, this is TAP Buddy calling for ${studentName}. We noticed you have not completed this week's learning activity yet. Please open WhatsApp and finish your task today!`);
            }
            this.updateCharCount();
            return;
        }

        this.selectedScript = this.scripts.find(function(s) { return s.name === scriptName; });
        if (!this.selectedScript) return;

        var rawText = this.selectedScript.status_text || "";
        var regex = /{([a-zA-Z0-9_]+)}/g;
        var matches = [];
        var match;
        while ((match = regex.exec(rawText)) !== null) {
            if (!matches.includes(match[1])) {
                matches.push(match[1]);
            }
        }

        this.renderVariableInputs(matches);
        this.updateDynamicVariables();
    }

    renderVariableInputs(varList) {
        var container = $('#dynamic-variables-container');
        container.empty();

        if (varList.length === 0) {
            $('#dynamic-variables-section').hide();
            return;
        }

        var me = this;
        var studentName = $('#contact-name').val() || "Nigam";
        $('#var-count-badge').text(varList.length + ' variables');

        varList.forEach(function(v) {
            var defVal = "1";
            if (v === 'student_name') defVal = studentName;
            else if (v === 'week') defVal = "1";
            else if (v === 'reminder_count') defVal = "1";
            else if (v === 'task_name') defVal = "Summer Activity";
            else if (v === 'grace_deadline') defVal = "Sunday 8 PM";
            else if (v === 'streak_count' || v === 'streak') defVal = "3";
            else if (v === 'escalation_order' || v === 'call_attempt') defVal = "1";
            else if (v === 'course') defVal = "Art & Coding";
            else if (v === 'situation') defVal = "pending_task";
            else if (v === 'submission_ask') defVal = "Complete Week 1 activity";
            else if (v === 'last_message') defVal = "Reminder 1";
            else if (v === 'grade_group') defVal = "Grade 6-8";
            else if (v === 'total_points') defVal = "150";
            else if (v === 'submission_count') defVal = "2";

            var inputCol = `
                <div class="col-6 mb-2">
                    <div class="variable-field-group">
                        <label class="text-xs font-weight-bold text-dark mb-1 d-block text-truncate" title="{${v}}" style="font-size:11px;">{${v}}</label>
                        <input type="text" class="form-control form-control-sm script-var-input" data-var="${v}" value="${defVal}">
                    </div>
                </div>
            `;
            container.append(inputCol);
        });

        $('#dynamic-variables-section').show();

        $('.script-var-input').on('input', function() {
            me.isManualEditMode = false;
            me.updateDynamicVariables();
        });
    }

    updateDynamicVariables() {
        var studentName = $('#contact-name').val() || "Nigam";

        // Update welcome editor placeholders
        var welcomeRaw = "नमस्कार... मैं TAP Buddy की तरफ़ से बात कर रही हूँ... क्या मैं {student_name} के माता-पिता से बात कर रही हूँ?";
        if (!$('#welcome-editor').data('user-edited')) {
            $('#welcome-editor').val(welcomeRaw.replace('{student_name}', studentName));
        }

        if (!this.selectedScript) return;

        var variables = {};
        $('.script-var-input').each(function() {
            var key = $(this).data('var');
            var val = $(this).val();
            variables[key] = val;
        });

        if (studentName && !variables['student_name']) {
            variables['student_name'] = studentName;
        }

        this.detectedVariables = variables;

        var rawText = this.selectedScript.status_text || "";
        var rendered = rawText;

        for (var k in variables) {
            rendered = rendered.split('{' + k + '}').join(variables[k]);
        }

        $('#prompt-editor').val(rendered);
        this.updateCharCount();
    }

    updateCharCount() {
        var welcomeText = $('#welcome-editor').val() || "";
        var promptText = $('#prompt-editor').val() || "";
        $('#welcome-char-count').text(welcomeText.length + ' chars');
        $('#char-count').text(promptText.length + ' chars');
    }

    openSaveScriptModal() {
        var me = this;
        var currentPrompt = $('#prompt-editor').val() || "";
        if (!currentPrompt) {
            frappe.msgprint(__('Please enter a prompt first before saving.'));
            return;
        }

        var d = new frappe.ui.Dialog({
            title: __('Save as New ParentCallConfig'),
            fields: [
                {
                    label: __('Script Title / Name'),
                    fieldname: 'title',
                    fieldtype: 'Data',
                    reqd: 1,
                    default: 'Custom-Test-Script-' + frappe.datetime.now_datetime().slice(11, 19).replace(/:/g, '')
                },
                {
                    label: __('Status Template Body'),
                    fieldname: 'status_template',
                    fieldtype: 'Small Text',
                    reqd: 1,
                    default: currentPrompt
                }
            ],
            primary_action_label: __('Save Script'),
            primary_action: function(values) {
                frappe.call({
                    method: 'tap_lms.tap_lms.page.vocallabs_test_call.vocallabs_test_call.save_script',
                    args: {
                        title: values.title,
                        status_template: values.status_template
                    },
                    callback: function(r) {
                        d.hide();
                        if (r.message && r.message.success) {
                            frappe.show_alert({message: __('Script saved successfully!'), indicator: 'green'});
                            me.fetchInitialData();
                        }
                    }
                });
            }
        });
        d.show();
    }

    renderCallHistory() {
        var container = $('#call-history-list');
        var emptyMsg = $('#empty-history-msg');
        container.find('.history-item-row').remove();

        if (this.callHistory.length === 0) {
            emptyMsg.show();
            return;
        }

        emptyMsg.hide();
        var me = this;

        this.callHistory.forEach(function(item, idx) {
            var badgeClass = item.success ? 'badge-success' : 'badge-danger';
            var statusIcon = item.success ? 'fa-check text-success' : 'fa-times text-danger';

            var rowHtml = `
                <div class="history-item-row d-flex justify-content-between align-items-center py-2 border-bottom">
                    <div class="d-flex align-items-center text-truncate mr-2">
                        <i class="fa ${statusIcon} mr-2" style="font-size:12px;"></i>
                        <span class="font-weight-bold text-dark text-xs mr-2">${item.phone}</span>
                        <span class="badge badge-light border text-muted mr-2" style="font-size:10px;">${item.language || 'Default'}</span>
                        <span class="text-muted text-xs text-truncate" style="max-width:220px;" title="${frappe.utils.escape_html(item.prompt)}">${frappe.utils.escape_html(item.prompt)}</span>
                    </div>
                    <div class="d-flex align-items-center flex-shrink-0">
                        <span class="text-muted mr-2" style="font-size:10px;">${item.time}</span>
                        <button type="button" class="btn btn-xs btn-outline-secondary btn-reuse-history" data-idx="${idx}" title="Reload this prompt & phone">
                            <i class="fa fa-repeat"></i> Reuse
                        </button>
                    </div>
                </div>
            `;
            container.append(rowHtml);
        });

        $('.btn-reuse-history').on('click', function() {
            var idx = $(this).data('idx');
            var item = me.callHistory[idx];
            if (item) {
                $('#target-phone').val(item.phone);
                $('#prompt-editor').val(item.prompt);
                if (item.welcome_message) $('#welcome-editor').val(item.welcome_message);
                if (item.language) $('#select-language').val(item.language);
                me.isManualEditMode = true;
                me.updateCharCount();
                frappe.show_alert({message: __('Loaded configuration from history.'), indicator: 'blue'});
            }
        });
    }

    triggerCall() {
        var me = this;
        var phone = $('#target-phone').val();
        var contactName = $('#contact-name').val();
        var language = $('#select-language').val();
        var scriptName = $('#select-script').val();
        var customWelcome = $('#welcome-editor').val();
        var customPrompt = $('#prompt-editor').val();
        var agentOverride = $('#override-agent-id').val();
        var prospectOverride = $('#override-prospect-id').val();

        if (!phone) {
            frappe.msgprint({title: __('Validation'), indicator: 'orange', message: __('Please enter a valid Phone Number.')});
            return;
        }

        if (!customPrompt || !customPrompt.trim()) {
            frappe.msgprint({title: __('Validation'), indicator: 'orange', message: __('Please enter prompt text to speak.')});
            return;
        }

        var btn = $('#btn-trigger-call');
        btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin mr-2"></i> Connecting to Vocallabs AI...');

        var resultBox = $('#call-result-container');
        resultBox.hide().empty();

        frappe.call({
            method: 'tap_lms.tap_lms.page.vocallabs_test_call.vocallabs_test_call.launch_test_call',
            args: {
                phone: phone,
                contact_name: contactName,
                language: (language !== 'All' ? language : 'English'),
                script_name: (scriptName !== '__custom__' ? scriptName : null),
                custom_welcome_message: customWelcome,
                custom_status_text: customPrompt,
                custom_variables: JSON.stringify(me.detectedVariables),
                agent_id_override: agentOverride,
                prospect_id_override: prospectOverride
            },
            callback: function(r) {
                btn.prop('disabled', false).html('<i class="fa fa-phone mr-2"></i> Launch Test Call Now');

                var now = new Date();
                var timeStr = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});

                if (r.message && r.message.success) {
                    var m = r.message;
                    var callId = (m.call_response && m.call_response.call_id) ? m.call_response.call_id : 'N/A';

                    var resHtml = `
                        <div class="call-success-card p-3 rounded shadow-sm border">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="badge badge-success px-2 py-1"><i class="fa fa-check-circle mr-1"></i> Call Initiated Successfully</span>
                                <span class="text-muted text-xs"><i class="fa fa-clock-o mr-1"></i>${timeStr}</span>
                            </div>

                            <div class="row text-xs mb-2">
                                <div class="col-sm-6 mb-1">
                                    <span class="text-muted">Target Phone:</span> <strong class="text-dark">${m.phone}</strong>
                                </div>
                                <div class="col-sm-6 mb-1">
                                    <span class="text-muted">Call ID:</span> <code class="text-primary">${callId}</code>
                                </div>
                                <div class="col-sm-6 mb-1">
                                    <span class="text-muted">Prospect ID:</span> <code class="text-secondary">${m.prospect_id}</code>
                                </div>
                                <div class="col-sm-6 mb-1">
                                    <span class="text-muted">Agent ID:</span> <code class="text-secondary">${m.agent_id}</code>
                                </div>
                            </div>

                            <div class="p-2 bg-light rounded text-xs mt-2 border mb-2">
                                <strong class="text-primary d-block mb-1"><i class="fa fa-commenting-o mr-1"></i> 1. Welcome Greeting Delivered ({{welcome_greeting}}):</strong>
                                <span style="white-space: pre-wrap; font-family: sans-serif; color:#1e293b;">${frappe.utils.escape_html(customWelcome)}</span>
                            </div>

                            <div class="p-2 bg-light rounded text-xs border">
                                <strong class="text-secondary d-block mb-1"><i class="fa fa-volume-up mr-1"></i> 2. Spoken Prompt Context Delivered ({{status}}):</strong>
                                <span style="white-space: pre-wrap; font-family: monospace; color:#1e293b;">${frappe.utils.escape_html(m.rendered_status)}</span>
                            </div>
                        </div>
                    `;
                    resultBox.html(resHtml).fadeIn();

                    me.saveCallHistory({
                        phone: m.phone,
                        prompt: m.rendered_status,
                        welcome_message: customWelcome,
                        language: language,
                        time: timeStr,
                        success: true,
                        call_id: callId
                    });

                } else {
                    var err = (r.message && r.message.error) ? r.message.error : "Unknown error occurred.";
                    var errHtml = `
                        <div class="alert alert-danger border-0 shadow-sm p-3 rounded">
                            <h6 class="font-weight-bold text-danger mb-1"><i class="fa fa-exclamation-triangle mr-1"></i> Call Failed</h6>
                            <p class="mb-0 text-xs">${frappe.utils.escape_html(err)}</p>
                        </div>
                    `;
                    resultBox.html(errHtml).fadeIn();

                    me.saveCallHistory({
                        phone: phone,
                        prompt: customPrompt,
                        welcome_message: customWelcome,
                        language: language,
                        time: timeStr,
                        success: false,
                        error: err
                    });
                }
            },
            error: function(err) {
                btn.prop('disabled', false).html('<i class="fa fa-phone mr-2"></i> Launch Test Call Now');
                resultBox.html(`<div class="alert alert-danger p-3 text-xs">Server execution failed. Check Frappe error logs.</div>`).fadeIn();
            }
        });
    }
}
