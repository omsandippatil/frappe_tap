frappe.pages['voice_ai_home'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Voice AI Home',
        single_column: true
    });

    $(wrapper).find('.page-head').hide();
    wrapper.home_app = new VoiceAIHome(wrapper, page);
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

class VoiceAIHome {
    constructor(wrapper, page) {
        this.wrapper = wrapper;
        this.page = page;
        this.$wrapper = $(wrapper);
        this.summary = null;

        this.init();
    }

    init() {
        this.$wrapper.find('.page-head').hide();
        this.setupLayout();
        this.loadSummary();
    }

    setupLayout() {
        var html = `
        <div class="vcd-home-page-wrapper">
            
            <!-- COMMON TOP NAVBAR -->
            ${getVoiceAINavbarHTML('home')}

            <!-- Hero Welcome Header -->
            <div class="vcd-home-hero d-flex justify-content-between align-items-center flex-wrap">
                <div>
                    <div class="vcd-home-hero-title">
                        🎙️ TAP Voice AI Calling Central
                    </div>
                    <div class="vcd-home-hero-desc">
                        Operations & Calling Hub for The Apprentice Project. Monitor automated parent escalation calls, manage multi-language script templates, and test dynamic AI voice prompts.
                    </div>
                </div>
                <div class="d-flex align-items-center gap-2 mt-3 mt-md-0">
                    <span class="badge badge-success px-3 py-2 font-weight-bold" style="font-size:13.5px;">
                        <i class="fa fa-circle mr-1" style="font-size:8px;"></i> VocalLabs Engine Active
                    </span>
                </div>
            </div>

            <!-- PRIMARY LAUNCHPAD CARDS (DASHBOARD & TESTING STUDIO) -->
            <div class="row mb-4">
                
                <!-- Launchpad 1: Operations Dashboard -->
                <div class="col-md-6 mb-3 mb-md-0">
                    <div class="vcd-launchpad-card" id="btn-launch-dashboard">
                        <div>
                            <div class="vcd-launchpad-icon" style="background:#eff6ff; color:#2563eb;">
                                <i class="fa fa-bar-chart"></i>
                            </div>
                            <div class="vcd-launchpad-title">
                                📊 Voice AI Operations & Analytics Dashboard
                            </div>
                            <div class="vcd-launchpad-desc">
                                Real-time monitoring of automated parent calls, delivery & connect rates, cohort language demographics (Hindi, Marathi, English, Punjabi), and live execution audit logs.
                            </div>
                        </div>
                        <div>
                            <button type="button" class="btn btn-primary vcd-launchpad-btn w-100" style="background:#2563eb; border:none;">
                                Open Analytics Dashboard &rarr;
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Launchpad 2: Testing Studio -->
                <div class="col-md-6">
                    <div class="vcd-launchpad-card" id="btn-launch-studio">
                        <div>
                            <div class="vcd-launchpad-icon" style="background:#fef3c7; color:#d97706;">
                                <i class="fa fa-flask"></i>
                            </div>
                            <div class="vcd-launchpad-title">
                                🧪 Voice AI Testing Studio (Sandbox)
                            </div>
                            <div class="vcd-launchpad-desc">
                                Interactive testing sandbox for developers & operations. Test single phone numbers with custom Welcome Greetings, Agent Voice Prompts, dynamic variable chips, and raw API inspection.
                            </div>
                        </div>
                        <div>
                            <button type="button" class="btn btn-warning text-dark vcd-launchpad-btn w-100" style="background:#fbbf24; border:none; font-weight:700;">
                                Launch Testing Studio &rarr;
                            </button>
                        </div>
                    </div>
                </div>

            </div>

            <!-- SECTION: CORE OPERATIONS MODULES -->
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="font-weight-bold mb-0 text-dark">
                    📁 Core Operations & Configuration Modules
                </h5>
                <span class="text-muted text-xs">Direct links to manage LMS data</span>
            </div>

            <div class="row mb-4">
                
                <!-- Module 1: Students -->
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="vcd-module-card">
                        <div>
                            <div class="d-flex align-items-center">
                                <div class="vcd-module-icon" style="background:#e0f2fe; color:#0284c7;">
                                    <i class="fa fa-users"></i>
                                </div>
                                <div class="vcd-module-count text-primary" id="vcd-home-students">--</div>
                            </div>
                            <div class="vcd-module-title">Student Records</div>
                            <div class="vcd-module-desc">Manage enrolled students, parent phone numbers, and language preferences.</div>
                        </div>
                        <div class="pt-2 border-top d-flex justify-content-between">
                            <button type="button" class="btn btn-xs btn-outline-primary" id="vcd-btn-view-students">View All</button>
                            <button type="button" class="btn btn-xs btn-link text-muted" id="vcd-btn-add-student">+ Add</button>
                        </div>
                    </div>
                </div>

                <!-- Module 2: Campaign Scripts -->
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="vcd-module-card">
                        <div>
                            <div class="d-flex align-items-center">
                                <div class="vcd-module-icon" style="background:#fef3c7; color:#d97706;">
                                    <i class="fa fa-file-text-o"></i>
                                </div>
                                <div class="vcd-module-count text-warning" id="vcd-home-scripts">--</div>
                            </div>
                            <div class="vcd-module-title">Campaign Scripts</div>
                            <div class="vcd-module-desc">32+ pre-configured templates for weekly escalations, streak reminders & re-engagement.</div>
                        </div>
                        <div class="pt-2 border-top d-flex justify-content-between">
                            <button type="button" class="btn btn-xs btn-outline-warning text-dark" id="vcd-btn-view-scripts">Browse Scripts</button>
                            <button type="button" class="btn btn-xs btn-link text-muted" id="vcd-btn-add-script">+ New</button>
                        </div>
                    </div>
                </div>

                <!-- Module 3: Program Enrollments -->
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="vcd-module-card">
                        <div>
                            <div class="d-flex align-items-center">
                                <div class="vcd-module-icon" style="background:#f3e8ff; color:#7e22ce;">
                                    <i class="fa fa-graduation-cap"></i>
                                </div>
                                <div class="vcd-module-count text-purple" id="vcd-home-enrollments">--</div>
                            </div>
                            <div class="vcd-module-title">Program Enrollments</div>
                            <div class="vcd-module-desc">Track cohort progress across weekly milestones and active escalation stages.</div>
                        </div>
                        <div class="pt-2 border-top">
                            <button type="button" class="btn btn-xs btn-outline-secondary w-100" id="vcd-btn-view-enrollments">View Enrollments &rarr;</button>
                        </div>
                    </div>
                </div>

                <!-- Module 4: Settings -->
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="vcd-module-card">
                        <div>
                            <div class="d-flex align-items-center">
                                <div class="vcd-module-icon" style="background:#dcfce7; color:#16a34a;">
                                    <i class="fa fa-cogs"></i>
                                </div>
                                <div class="vcd-module-count text-success"><i class="fa fa-check"></i></div>
                            </div>
                            <div class="vcd-module-title">Voice Settings</div>
                            <div class="vcd-module-desc">Configure VocalLabs API credentials, fallback agent, and language agent mappings.</div>
                        </div>
                        <div class="pt-2 border-top">
                            <button type="button" class="btn btn-xs btn-outline-success w-100" id="vcd-btn-view-settings">Configure Settings &rarr;</button>
                        </div>
                    </div>
                </div>

            </div>

            <!-- SYSTEM INTEGRATION HEALTH FOOTER -->
            <div class="vcd-health-card d-flex justify-content-between align-items-center flex-wrap">
                <div class="d-flex align-items-center mb-2 mb-md-0">
                    <div class="mr-4">
                        <span class="text-xs text-muted text-uppercase font-weight-bold d-block">Service URL</span>
                        <span class="font-monospace text-dark font-weight-bold" id="vcd-home-service-url">https://api.superflow.run</span>
                    </div>
                    <div class="mr-4">
                        <span class="text-xs text-muted text-uppercase font-weight-bold d-block">Default Fallback Agent</span>
                        <span class="font-monospace text-dark font-weight-bold" id="vcd-home-agent-id">ea8e5749-83a3-47f6-9935-d584ba04f1f0</span>
                    </div>
                    <div>
                        <span class="text-xs text-muted text-uppercase font-weight-bold d-block">Operating Window</span>
                        <span class="text-success font-weight-bold">24x7 / DND Active Schedule</span>
                    </div>
                </div>
                <div>
                    <span class="badge badge-light border text-muted px-3 py-2">
                        TAP LMS v14 &bull; Vocallabs Calling Hub
                    </span>
                </div>
            </div>

        </div>
        `;

        this.$wrapper.find('.layout-main-section').html(html);
        this.bindEvents();
    }

    bindEvents() {
        var me = this;
        var $w = this.$wrapper;

        // Common Navbar events
        bindVoiceAINavbarEvents($w);

        // Launchpad 1: Dashboard
        $w.on('click', '#btn-launch-dashboard', function() {
            frappe.set_route('voice_campaign_dashboard');
        });

        // Launchpad 2: Testing Studio
        $w.on('click', '#btn-launch-studio', function() {
            frappe.set_route('vocallabs_test_call');
        });

        // Module Buttons
        $w.on('click', '#vcd-btn-view-students', function() {
            frappe.set_route('List', 'Student');
        });
        $w.on('click', '#vcd-btn-add-student', function() {
            frappe.new_doc('Student');
        });

        $w.on('click', '#vcd-btn-view-scripts', function() {
            frappe.set_route('List', 'ParentCallConfig');
        });
        $w.on('click', '#vcd-btn-add-script', function() {
            frappe.new_doc('ParentCallConfig');
        });

        $w.on('click', '#vcd-btn-view-enrollments', function() {
            frappe.set_route('List', 'ProgramEnrollment');
        });

        $w.on('click', '#vcd-btn-view-settings', function() {
            frappe.set_route('Form', 'VoiceAgentSettings');
        });
    }

    loadSummary() {
        var me = this;
        frappe.call({
            method: 'tap_lms.tap_lms.page.voice_ai_home.voice_ai_home.get_home_summary',
            callback: function(r) {
                if (r && r.message) {
                    me.summary = r.message;
                    me.$wrapper.find('#vcd-home-students').text(r.message.total_students || 0);
                    me.$wrapper.find('#vcd-home-scripts').text(r.message.total_scripts || 0);
                    me.$wrapper.find('#vcd-home-enrollments').text(r.message.total_enrollments || 0);

                    if (r.message.settings) {
                        me.$wrapper.find('#vcd-home-service-url').text(r.message.settings.service_url || 'https://api.superflow.run');
                        me.$wrapper.find('#vcd-home-agent-id').text(r.message.settings.fallback_agent_id || 'ea8e5749-83a3-47f6-9935-d584ba04f1f0');
                    }
                }
            }
        });
    }
}
