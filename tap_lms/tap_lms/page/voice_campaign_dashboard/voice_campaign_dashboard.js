frappe.pages['voice_campaign_dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Voice AI Operations Dashboard',
        single_column: true
    });

    $(wrapper).find('.page-head').hide();
    wrapper.analytics_dashboard = new VoiceOperationsDashboard(wrapper, page);
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

class VoiceOperationsDashboard {
    constructor(wrapper, page) {
        this.wrapper = wrapper;
        this.page = page;
        this.$wrapper = $(wrapper);
        this.metrics = null;

        this.init();
    }

    init() {
        this.$wrapper.find('.page-head').hide();
        this.setupLayout();
        this.loadMetrics();
    }

    setupLayout() {
        var html = `
        <div class="vcd-analytics-wrapper">
            
            <!-- COMMON TOP NAVBAR -->
            ${getVoiceAINavbarHTML('dashboard')}

            <!-- Dashboard Header -->
            <div class="vcd-dash-header d-flex justify-content-between align-items-center flex-wrap">
                <div>
                    <div class="vcd-dash-title">
                        📊 Voice AI Campaign & Operations Dashboard
                    </div>
                    <div class="vcd-dash-subtitle">
                        Real-time operational monitoring, delivery metrics, cohort language distribution, and live call audit logs.
                    </div>
                </div>
                <div class="d-flex align-items-center gap-2 mt-3 mt-md-0">
                    <button type="button" class="btn btn-sm btn-outline-secondary mr-2" id="vcd-btn-refresh">
                        <i class="fa fa-refresh mr-1"></i> Refresh Metrics
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-primary mr-2" id="vcd-btn-view-scripts">
                        <i class="fa fa-file-text-o mr-1"></i> Scripts Library
                    </button>
                    <button type="button" class="btn btn-sm btn-primary" id="vcd-btn-open-studio" style="background:#2563eb; border:none;">
                        <i class="fa fa-flask mr-1"></i> Open Testing Studio
                    </button>
                </div>
            </div>

            <!-- Top Executive KPI Row -->
            <div class="row mb-4">
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="vcd-metric-card">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="vcd-metric-label">Total Calls Placed</div>
                            <div class="vcd-metric-icon" style="background:#e0f2fe; color:#0284c7;">
                                <i class="fa fa-phone"></i>
                            </div>
                        </div>
                        <div class="vcd-metric-value" id="vcd-kpi-calls">--</div>
                        <div class="text-xs text-muted mt-2">
                            <span class="text-success font-weight-bold"><i class="fa fa-arrow-up"></i> Live</span> background & campaign calls
                        </div>
                    </div>
                </div>

                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="vcd-metric-card">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="vcd-metric-label">Connect Rate</div>
                            <div class="vcd-metric-icon" style="background:#dcfce7; color:#16a34a;">
                                <i class="fa fa-pie-chart"></i>
                            </div>
                        </div>
                        <div class="vcd-metric-value text-success" id="vcd-kpi-connect-rate">--%</div>
                        <div class="text-xs text-muted mt-2">
                            <span id="vcd-kpi-failed-count" class="text-danger font-weight-bold">0</span> failed / DLQ attempts
                        </div>
                    </div>
                </div>

                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="vcd-metric-card">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="vcd-metric-label">Enrolled Students</div>
                            <div class="vcd-metric-icon" style="background:#f3e8ff; color:#7e22ce;">
                                <i class="fa fa-users"></i>
                            </div>
                        </div>
                        <div class="vcd-metric-value" id="vcd-kpi-students">--</div>
                        <div class="text-xs text-muted mt-2">
                            <span id="vcd-kpi-enrollments">--</span> active program enrollments
                        </div>
                    </div>
                </div>

                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="vcd-metric-card">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="vcd-metric-label">Active Call Scripts</div>
                            <div class="vcd-metric-icon" style="background:#fef3c7; color:#d97706;">
                                <i class="fa fa-bullhorn"></i>
                            </div>
                        </div>
                        <div class="vcd-metric-value" id="vcd-kpi-scripts">--</div>
                        <div class="text-xs text-muted mt-2" id="vcd-kpi-scripts-caption">
                            ParentCallConfig templates (Vocallabs voice prompts)
                        </div>
                    </div>
                </div>
            </div>

            <!-- Middle Analytics Row: Language Distribution & Agent Mappings -->
            <div class="row mb-4">
                
                <!-- Left: Language Distribution -->
                <div class="col-md-6 mb-3 mb-md-0">
                    <div class="vcd-panel">
                        <div class="vcd-panel-title">
                            <span><i class="fa fa-language text-primary mr-2"></i> Cohort Language Distribution</span>
                            <span class="badge badge-light border text-muted">Student Demographics</span>
                        </div>
                        <div id="vcd-lang-container" class="pt-2">
                            <div class="text-center py-4 text-muted">
                                <i class="fa fa-spinner fa-spin mr-2"></i> Loading language breakdown...
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right: Active AI Voice Agents -->
                <div class="col-md-6">
                    <div class="vcd-panel">
                        <div class="vcd-panel-title">
                            <span><i class="fa fa-cogs text-success mr-2"></i> Multi-Language Voice Agents</span>
                            <span class="badge badge-success px-2 py-1">VocalLabs Connected</span>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm table-bordered">
                                <thead class="thead-light">
                                    <tr>
                                        <th>Language</th>
                                        <th>Target Agent UUID</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td class="font-weight-bold">Hindi</td>
                                        <td class="font-monospace text-xs">ea8e5749-83a3-47f6-9935-d584ba04f1f0</td>
                                        <td><span class="badge badge-success">Active</span></td>
                                    </tr>
                                    <tr>
                                        <td class="font-weight-bold">English</td>
                                        <td class="font-monospace text-xs">ea8e5749-83a3-47f6-9935-d584ba04f1f0</td>
                                        <td><span class="badge badge-success">Active</span></td>
                                    </tr>
                                    <tr>
                                        <td class="font-weight-bold">Marathi</td>
                                        <td class="font-monospace text-xs">2f5dc3d8-7a0b-418c-b26e-35aa2b8b86a2</td>
                                        <td><span class="badge badge-success">Active</span></td>
                                    </tr>
                                    <tr>
                                        <td class="font-weight-bold">Punjabi</td>
                                        <td class="font-monospace text-xs">d72562b4-0ac6-41d1-a116-f96682470f4b</td>
                                        <td><span class="badge badge-success">Active</span></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <div class="mt-2 text-xs text-muted">
                            <i class="fa fa-info-circle mr-1"></i> Fallback agent routes unmapped dialects to default agent.
                        </div>
                    </div>
                </div>

            </div>

            <!-- Bottom Row: Live Execution Audit Trail -->
            <div class="vcd-panel">
                <div class="vcd-panel-title">
                    <div>
                        <span><i class="fa fa-list-alt text-dark mr-2"></i> Recent Program Event & Voice Call Logs</span>
                        <div class="text-xs text-muted font-weight-normal mt-1">Audit log of escalation voice triggers and automated calling jobs.</div>
                    </div>
                    <div>
                        <button type="button" class="btn btn-xs btn-outline-secondary mr-1" id="vcd-btn-view-program-logs">
                            Full Event Logs &rarr;
                        </button>
                        <button type="button" class="btn btn-xs btn-outline-danger" id="vcd-btn-view-error-logs">
                            DLQ Error Logs &rarr;
                        </button>
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="table vcd-log-table table-hover">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Event Type</th>
                                <th>Student ID</th>
                                <th>Batch / Program</th>
                                <th>Details / Payload</th>
                                <th style="text-align: right;">Status</th>
                            </tr>
                        </thead>
                        <tbody id="vcd-logs-tbody">
                            <tr>
                                <td colspan="6" class="text-center py-4 text-muted">
                                    <i class="fa fa-spinner fa-spin mr-2"></i> Fetching audit logs...
                                </td>
                            </tr>
                        </tbody>
                    </table>
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

        $w.on('click', '#vcd-btn-refresh', function() {
            me.loadMetrics();
        });

        $w.on('click', '#vcd-btn-open-studio', function() {
            frappe.set_route('vocallabs_test_call');
        });

        $w.on('click', '#vcd-btn-view-scripts', function() {
            frappe.set_route('List', 'ParentCallConfig');
        });

        $w.on('click', '#vcd-btn-view-program-logs', function() {
            frappe.set_route('List', 'ProgramEventLog');
        });

        $w.on('click', '#vcd-btn-view-error-logs', function() {
            frappe.set_route('List', 'Error Log');
        });
    }

    loadMetrics() {
        var me = this;
        frappe.call({
            method: 'tap_lms.tap_lms.page.voice_campaign_dashboard.voice_campaign_dashboard.get_dashboard_metrics',
            callback: function(r) {
                if (r && r.message) {
                    me.metrics = r.message;
                    me.renderKPIs();
                    me.renderLanguages();
                    me.renderLogs();
                }
            }
        });
    }

    renderKPIs() {
        var kpis = this.metrics.kpis || {};
        this.$wrapper.find('#vcd-kpi-calls').text(kpis.total_calls_dispatched || 0);
        var rateText = (kpis.connect_rate === null || kpis.connect_rate === undefined)
            ? '—'
            : `${kpis.connect_rate}%`;
        this.$wrapper.find('#vcd-kpi-connect-rate').text(rateText);
        this.$wrapper.find('#vcd-kpi-failed-count').text(kpis.failed_calls || 0);
        this.$wrapper.find('#vcd-kpi-students').text(kpis.total_students || 0);
        this.$wrapper.find('#vcd-kpi-enrollments').text(`${kpis.active_enrollments || 0} enrollments`);
        var scriptCount = kpis.active_campaigns || 0;
        this.$wrapper.find('#vcd-kpi-scripts').text(scriptCount);
        this.$wrapper.find('#vcd-kpi-scripts-caption').text(
            scriptCount + ' active in ParentCallConfig (Vocallabs voice prompts)'
        );
    }

    renderLanguages() {
        var container = this.$wrapper.find('#vcd-lang-container');
        container.empty();

        var langs = this.metrics.language_distribution || [];
        var total = this.metrics.kpis.total_students || 1;

        if (langs.length === 0) {
            container.html('<div class="text-center py-4 text-muted">No student language data available.</div>');
            return;
        }

        var colors = {
            'Hindi': '#0284c7',
            'Marathi': '#d97706',
            'English': '#7e22ce',
            'Punjabi': '#db2777',
            'Unassigned': '#64748b'
        };

        langs.forEach(function(item) {
            var pct = Math.round((item.count / total) * 100);
            var color = colors[item.language] || '#2563eb';
            var html = `
                <div class="vcd-lang-item">
                    <div class="vcd-lang-header">
                        <span>${item.language}</span>
                        <span class="text-muted">${item.count} students (${pct}%)</span>
                    </div>
                    <div class="vcd-progress-bg">
                        <div class="vcd-progress-fill" style="width: ${pct}%; background-color: ${color};"></div>
                    </div>
                </div>
            `;
            container.append(html);
        });
    }

    renderLogs() {
        var tbody = this.$wrapper.find('#vcd-logs-tbody');
        tbody.empty();

        var logs = this.metrics.recent_event_logs || [];
        if (logs.length === 0) {
            var days = (this.metrics && this.metrics.days_back) || 7;
            tbody.html(`
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        No voice call events in the last ${days} days.
                        Dispatches appear as <code>escalation_sent</code> (parent call);
                        outcomes as <code>parent_call_outcome</code> from the Vocallabs webhook.
                    </td>
                </tr>
            `);
            return;
        }

        var badgeClass = {
            success: 'badge-success',
            warning: 'badge-warning',
            danger: 'badge-danger',
            info: 'badge-info',
            secondary: 'badge-secondary',
            primary: 'badge-primary'
        };

        logs.forEach(function(l) {
            var statusCls = badgeClass[l.status_class] || 'badge-secondary';
            var tr = `
                <tr>
                    <td class="text-muted text-xs">${l.creation ? String(l.creation).split('.')[0] : '-'}</td>
                    <td><span class="badge badge-primary">${l.event_type || 'Voice Event'}</span></td>
                    <td class="font-monospace font-weight-bold">${l.student || '-'}</td>
                    <td class="text-secondary text-sm">${l.batch || '-'}</td>
                    <td class="text-muted text-xs">${l.summary || '-'}</td>
                    <td style="text-align: right;"><span class="badge ${statusCls}">${l.status_label || '-'}</span></td>
                </tr>
            `;
            tbody.append(tr);
        });
    }
}
