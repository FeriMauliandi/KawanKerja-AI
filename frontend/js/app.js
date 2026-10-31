/**
 * KawanKerja AI - Core Application Logic
 * Modern, responsive, decoupled REST client for PP No. 35/2021 Legal Assistant
 * Palette:
 * --text: #e0fff6;
 * --background: #00140f;
 * --primary: #04e797;
 * --secondary: #480297;
 * --accent: #a703b0;
 * Auxiliary: #06b6d4 (cyan), #f59e0b (amber), #f43f5e (rose), #6366f1 (indigo)
 */

(function () {
    'use strict';

    // State
    const AppState = {
        backendUrl: localStorage.getItem('kawankerja_backend_url') || 'http://127.0.0.1:8000',
        sessions: JSON.parse(localStorage.getItem('kawankerja_sessions') || '[]'),
        activeSessionId: null,
        isGenerating: false,
        abortController: null,
        backendOnline: false,
        speakingUtterance: null,
        speechRecognizer: null,
        isListening: false
    };

    // DOM Elements Cache
    const DOM = {
        html: document.documentElement,
        body: document.body,
        landingView: document.getElementById('landing-view'),
        chatView: document.getElementById('chat-view'),
        backToLandingBtn: document.getElementById('back-to-landing-btn'),

        chatContainer: document.getElementById('chat-messages'),
        scrollBottomBtn: document.getElementById('scroll-bottom-btn'),
        chatForm: document.getElementById('chat-form'),
        userInput: document.getElementById('user-input'),
        sendBtn: document.getElementById('send-btn'),
        stopBtn: document.getElementById('stop-btn'),
        micBtn: document.getElementById('mic-btn'),
        welcomeHero: document.getElementById('welcome-hero'),
        sessionList: document.getElementById('session-list'),
        newChatBtn: document.getElementById('new-chat-btn'),
        mobileSidebarBtn: document.getElementById('mobile-sidebar-btn'),
        sidebar: document.getElementById('sidebar'),
        sidebarBackdrop: document.getElementById('sidebar-backdrop'),
        statusBadge: document.getElementById('backend-status-badge'),
        statusText: document.getElementById('backend-status-text'),
        statusPing: document.getElementById('backend-status-ping'),
        exportChatBtn: document.getElementById('export-chat-btn'),
        clearChatBtn: document.getElementById('clear-chat-btn'),
        
        // Modals
        calcModal: document.getElementById('calc-modal'),
        calcOpenBtn: document.getElementById('calc-open-btn'),
        calcCloseBtn: document.getElementById('calc-close-btn'),
        settingsModal: document.getElementById('settings-modal'),
        settingsOpenBtn: document.getElementById('settings-open-btn'),
        settingsCloseBtn: document.getElementById('settings-close-btn'),
        settingsBackendUrl: document.getElementById('settings-backend-url'),
        settingsSaveBtn: document.getElementById('settings-save-btn'),
        settingsTestPingBtn: document.getElementById('settings-test-ping-btn'),
        settingsPingResult: document.getElementById('settings-ping-result'),
        sourceModal: document.getElementById('source-modal'),
        sourceModalClose: document.getElementById('source-modal-close'),
        sourceModalContent: document.getElementById('source-modal-content'),
        sourceModalTitle: document.getElementById('source-modal-title')
    };

    // Initialize Markdown Parser
    if (window.marked) {
        window.marked.setOptions({
            breaks: true,
            gfm: true
        });
    }

    // View Routing: Landing Page vs Chatbot View
    let canvasAnimationController = null;

    function switchToChatView(initialPrompt = null) {
        if (canvasAnimationController) canvasAnimationController.stop();
        if (DOM.landingView) DOM.landingView.classList.add('hidden');
        if (DOM.chatView) DOM.chatView.classList.remove('hidden');
        DOM.body.classList.add('overflow-hidden');
        window.location.hash = '#chat';

        if (initialPrompt) {
            setTimeout(() => {
                DOM.userInput.value = initialPrompt;
                autoResizeTextarea();
                handleUserSubmit();
            }, 120);
        } else {
            DOM.userInput.focus();
        }

        if (window.lucide) window.lucide.createIcons();
        scrollToBottom();
    }

    function switchToLandingView() {
        if (DOM.chatView) DOM.chatView.classList.add('hidden');
        if (DOM.landingView) DOM.landingView.classList.remove('hidden');
        DOM.body.classList.remove('overflow-hidden');
        window.location.hash = '#landing';
        if (canvasAnimationController) canvasAnimationController.start();
        if (window.lucide) window.lucide.createIcons();
        triggerScrollAnimations();
    }

    // =========================================================================
    // Legal & Employment Topic Animation — CONFINED TO PAGE 1 / HERO SECTION ONLY
    // Theme: Timbangan Keadilan (Scales of Justice) & Segel Regulasi PP 35/2021
    // =========================================================================
    function initLegalHeroAnimation() {
        const canvas = document.getElementById('legal-hero-canvas');
        const heroSection = document.getElementById('hero');
        if (!canvas || !heroSection) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let width = 0;
        let height = 0;
        let dpr = window.devicePixelRatio || 1;
        let animFrameId = null;
        let isRunning = false;
        let isHeroInView = true;

        // Interactive mouse tracking confined to Hero section
        const mouse = {
            x: -2000,
            y: -2000,
            normX: 0,
            active: false
        };

        heroSection.addEventListener('mousemove', (e) => {
            const rect = heroSection.getBoundingClientRect();
            mouse.x = e.clientX - rect.left;
            mouse.y = e.clientY - rect.top;
            mouse.normX = ((mouse.x / (rect.width || 1)) * 2 - 1); // -1 to +1
            mouse.active = true;
        });

        heroSection.addEventListener('mouseleave', () => {
            mouse.active = false;
            mouse.normX = 0;
        });

        function resize() {
            width = heroSection.clientWidth || window.innerWidth;
            height = heroSection.clientHeight || 750;
            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            canvas.style.width = width + 'px';
            canvas.style.height = height + 'px';
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        resize();
        window.addEventListener('resize', resize);

        // Official Notarized Legal Seals / Articles orbiting in Hero
        const LEGAL_SEALS = [
            { label: 'PP No. 35/2021', sub: 'Lembaran Negara RI No. 45', color: '#04e797', isHub: true },
            { label: 'Pasal 8 PKWT', sub: 'Batas Total 5 Tahun', color: '#06b6d4', isHub: false },
            { label: 'Pasal 15 Kompensasi', sub: '(Masa Kerja/12) × Upah', color: '#04e797', isHub: false },
            { label: 'Pasal 26 Lembur', sub: 'Maks. 4 Jam/Hari & 18 Jam/Mg', color: '#f59e0b', isHub: false },
            { label: 'Pasal 31 Upah Lembur', sub: 'Rumus Baku 1/173 Upah', color: '#f59e0b', isHub: false },
            { label: 'Pasal 40 Pesangon PHK', sub: 'Formula UP & UPMK', color: '#f43f5e', isHub: false },
            { label: 'Kepatuhan Regulasi', sub: 'Transparansi Hubungan Kerja', color: '#6366f1', isHub: false }
        ];

        // Instantiate seals with distributed starting positions inside Hero
        const seals = LEGAL_SEALS.map((item, i) => {
            const angle = (i / LEGAL_SEALS.length) * Math.PI * 2;
            const rx = Math.min(width * 0.38, 420);
            const ry = Math.min(height * 0.34, 230);
            return {
                ...item,
                id: i,
                x: width * 0.5 + Math.cos(angle) * rx,
                y: height * 0.45 + Math.sin(angle) * ry,
                baseAngle: angle,
                orbitRadiusX: rx,
                orbitRadiusY: ry,
                orbitSpeed: 0.0015 + (i % 3) * 0.0006,
                pulseOffset: Math.random() * Math.PI
            };
        });

        let currentTilt = 0;
        let targetTilt = 0;
        let time = 0;

        function render() {
            if (!isRunning) return;

            time += 0.016;
            ctx.clearRect(0, 0, width, height);

            // =================================================================
            // 1. Guilloche Security Wave Ribbons (Lembaran Negara RI Pattern)
            // =================================================================
            const waveY = height * 0.38;
            ctx.lineWidth = 1;
            for (let w = 0; w < 3; w++) {
                ctx.beginPath();
                const freq = 0.0035 + w * 0.0015;
                const amp = 26 - w * 6;
                const phase = time * (0.4 + w * 0.2);

                for (let x = 0; x <= width; x += 12) {
                    const y = waveY + Math.sin(x * freq + phase) * amp + Math.cos(x * 0.002 - phase * 0.5) * (amp * 0.4);
                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.strokeStyle = w === 0 ? 'rgba(4, 231, 151, 0.07)' : (w === 1 ? 'rgba(6, 182, 212, 0.05)' : 'rgba(72, 2, 151, 0.08)');
                ctx.stroke();
            }

            // =================================================================
            // 2. The Scales of Justice (Timbangan Hukum Ketenagakerjaan)
            // =================================================================
            const scaleCenterX = width * 0.5;
            const scaleCenterY = Math.min(height * 0.32, 250);
            const beamLength = Math.min(width * 0.58, 380);
            const halfBeam = beamLength * 0.5;

            // Natural balance harmonic oscillation + mouse influence
            const naturalSway = Math.sin(time * 0.9) * 0.032;
            targetTilt = naturalSway + (mouse.active ? mouse.normX * 0.07 : 0);
            currentTilt += (targetTilt - currentTilt) * 0.06; // smooth spring lerp

            // Central Law Pillar (Tiang Keadilan)
            ctx.save();
            ctx.strokeStyle = 'rgba(4, 231, 151, 0.22)';
            ctx.fillStyle = 'rgba(4, 231, 151, 0.12)';
            ctx.lineWidth = 1.5;

            // Pillar base
            const pillarBottom = scaleCenterY + 110;
            ctx.beginPath();
            ctx.moveTo(scaleCenterX - 28, pillarBottom);
            ctx.lineTo(scaleCenterX + 28, pillarBottom);
            ctx.lineTo(scaleCenterX + 16, pillarBottom - 12);
            ctx.lineTo(scaleCenterX - 16, pillarBottom - 12);
            ctx.closePath();
            ctx.stroke();

            // Pillar column
            ctx.beginPath();
            ctx.moveTo(scaleCenterX - 4, pillarBottom - 12);
            ctx.lineTo(scaleCenterX - 3, scaleCenterY - 14);
            ctx.lineTo(scaleCenterX + 3, scaleCenterY - 14);
            ctx.lineTo(scaleCenterX + 4, pillarBottom - 12);
            ctx.stroke();

            // Fulcrum Top Ring
            ctx.beginPath();
            ctx.arc(scaleCenterX, scaleCenterY - 14, 8, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(4, 231, 151, 0.45)';
            ctx.stroke();

            // Balancing Crossbeam (Lengan Timbangan)
            const leftX = scaleCenterX - Math.cos(currentTilt) * halfBeam;
            const leftY = scaleCenterY - 14 - Math.sin(currentTilt) * halfBeam;
            const rightX = scaleCenterX + Math.cos(currentTilt) * halfBeam;
            const rightY = scaleCenterY - 14 + Math.sin(currentTilt) * halfBeam;

            ctx.beginPath();
            ctx.moveTo(leftX, leftY);
            ctx.lineTo(rightX, rightY);
            ctx.strokeStyle = 'rgba(4, 231, 151, 0.35)';
            ctx.lineWidth = 2.2;
            ctx.stroke();

            // Left Pan: "HAK PEKERJA" (Kompensasi, Lembur, Pesangon)
            const leftPanY = leftY + 68 + Math.cos(time * 0.9) * 4;
            const panWidth = 46;

            // 3 Suspension strings
            ctx.lineWidth = 0.85;
            ctx.strokeStyle = 'rgba(4, 231, 151, 0.25)';
            ctx.beginPath();
            ctx.moveTo(leftX, leftY); ctx.lineTo(leftX - panWidth * 0.5, leftPanY);
            ctx.moveTo(leftX, leftY); ctx.lineTo(leftX, leftPanY);
            ctx.moveTo(leftX, leftY); ctx.lineTo(leftX + panWidth * 0.5, leftPanY);
            ctx.stroke();

            // Pan dish
            ctx.beginPath();
            ctx.arc(leftX, leftPanY - 4, panWidth * 0.5, 0.15, Math.PI - 0.15);
            ctx.strokeStyle = 'rgba(4, 231, 151, 0.45)';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Left Plaque Text
            ctx.font = '600 9.5px "Plus Jakarta Sans", sans-serif';
            ctx.fillStyle = 'rgba(4, 231, 151, 0.65)';
            ctx.textAlign = 'center';
            ctx.fillText('HAK PEKERJA', leftX, leftPanY + 16);

            // Right Pan: "KEPASTIAN USAHA" (PKWT, Kepatuhan PP 35/2021)
            const rightPanY = rightY + 68 - Math.cos(time * 0.9) * 4;

            // 3 Suspension strings
            ctx.lineWidth = 0.85;
            ctx.strokeStyle = 'rgba(6, 182, 212, 0.25)';
            ctx.beginPath();
            ctx.moveTo(rightX, rightY); ctx.lineTo(rightX - panWidth * 0.5, rightPanY);
            ctx.moveTo(rightX, rightY); ctx.lineTo(rightX, rightPanY);
            ctx.moveTo(rightX, rightY); ctx.lineTo(rightX + panWidth * 0.5, rightPanY);
            ctx.stroke();

            // Pan dish
            ctx.beginPath();
            ctx.arc(rightX, rightPanY - 4, panWidth * 0.5, 0.15, Math.PI - 0.15);
            ctx.strokeStyle = 'rgba(6, 182, 212, 0.45)';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Right Plaque Text
            ctx.font = '600 9.5px "Plus Jakarta Sans", sans-serif';
            ctx.fillStyle = 'rgba(6, 182, 212, 0.65)';
            ctx.textAlign = 'center';
            ctx.fillText('KEPASTIAN HUKUM', rightX, rightPanY + 16);

            ctx.restore();

            // =================================================================
            // 3. Floating Notarized Article Seals (Pasal-Pasal Resmi PP 35/2021)
            // =================================================================
            for (let i = 0; i < seals.length; i++) {
                const seal = seals[i];

                // Slow, graceful orbital drift within hero
                seal.baseAngle += seal.orbitSpeed;
                const targetX = width * 0.5 + Math.cos(seal.baseAngle) * seal.orbitRadiusX;
                const targetY = height * 0.46 + Math.sin(seal.baseAngle) * seal.orbitRadiusY;

                seal.x += (targetX - seal.x) * 0.05;
                seal.y += (targetY - seal.y) * 0.05;

                // Fine vector thread connecting seal to the Scales of Justice beam
                const beamAnchorX = i % 2 === 0 ? leftX : rightX;
                const beamAnchorY = i % 2 === 0 ? leftY : rightY;

                ctx.beginPath();
                ctx.moveTo(beamAnchorX, beamAnchorY);
                ctx.lineTo(seal.x, seal.y);
                ctx.strokeStyle = 'rgba(4, 231, 151, 0.09)';
                ctx.lineWidth = 0.75;
                ctx.stroke();

                // Draw Legal Seal Card
                const cardW = seal.isHub ? 150 : 138;
                const cardH = 34;
                const cardX = seal.x - cardW * 0.5;
                const cardY = seal.y - cardH * 0.5;

                // Outer seal background
                ctx.save();
                ctx.fillStyle = 'rgba(2, 33, 25, 0.78)';
                ctx.strokeStyle = seal.color;
                ctx.lineWidth = 1;
                ctx.shadowBlur = seal.isHub ? 10 : 6;
                ctx.shadowColor = seal.color;

                // Rounded badge
                ctx.beginPath();
                ctx.roundRect(cardX, cardY, cardW, cardH, 8);
                ctx.fill();
                ctx.stroke();
                ctx.shadowBlur = 0;

                // Inner double-border ring (notary seal feel)
                ctx.strokeStyle = 'rgba(224, 255, 246, 0.15)';
                ctx.lineWidth = 0.5;
                ctx.beginPath();
                ctx.roundRect(cardX + 2.5, cardY + 2.5, cardW - 5, cardH - 5, 6);
                ctx.stroke();

                // Mini legal pip
                ctx.beginPath();
                ctx.arc(cardX + 11, seal.y, 3, 0, Math.PI * 2);
                ctx.fillStyle = seal.color;
                ctx.fill();

                // Typography
                ctx.textAlign = 'left';
                ctx.font = '700 10px "JetBrains Mono", monospace';
                ctx.fillStyle = '#e0fff6';
                ctx.fillText(seal.label, cardX + 20, seal.y - 2);

                ctx.font = '500 8.5px "Plus Jakarta Sans", sans-serif';
                ctx.fillStyle = 'rgba(224, 255, 246, 0.55)';
                ctx.fillText(seal.sub, cardX + 20, seal.y + 9);

                ctx.restore();
            }

            animFrameId = requestAnimationFrame(render);
        }

        function start() {
            if (!isRunning && isHeroInView) {
                isRunning = true;
                animFrameId = requestAnimationFrame(render);
            }
        }

        function stop() {
            isRunning = false;
            if (animFrameId) {
                cancelAnimationFrame(animFrameId);
                animFrameId = null;
            }
        }

        // IntersectionObserver: Pause when Hero section is out of viewport!
        if ('IntersectionObserver' in window) {
            const heroObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    isHeroInView = entry.isIntersecting;
                    if (isHeroInView) {
                        if (!DOM.landingView.classList.contains('hidden')) start();
                    } else {
                        stop();
                    }
                });
            }, { threshold: 0.05 });

            heroObserver.observe(heroSection);
        }

        // Visibility listener (pause when tab hidden)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                stop();
            } else if (!DOM.landingView.classList.contains('hidden') && isHeroInView) {
                start();
            }
        });

        // Controller for external callers
        canvasAnimationController = { start, stop, resize };
        start();
    }

    // Landing Page Smooth Scrolling
    function initSmoothScrolling() {
        document.querySelectorAll('a.landing-nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                const targetId = link.getAttribute('href');
                if (targetId && targetId.startsWith('#')) {
                    e.preventDefault();
                    if (DOM.landingView && DOM.landingView.classList.contains('hidden')) {
                        switchToLandingView();
                    }
                    const targetEl = document.querySelector(targetId);
                    if (targetEl) {
                        targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            });
        });
    }

    // Entrance Animations on Scroll
    let scrollObserver = null;
    function initScrollAnimations() {
        if ('IntersectionObserver' in window) {
            scrollObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '0px 0px -40px 0px'
            });

            triggerScrollAnimations();
        } else {
            // Fallback for older browsers
            document.querySelectorAll('.reveal-on-scroll').forEach(el => {
                el.classList.add('is-visible');
            });
        }
    }

    function triggerScrollAnimations() {
        if (scrollObserver) {
            document.querySelectorAll('.reveal-on-scroll').forEach(el => {
                scrollObserver.observe(el);
            });
        }
    }

    // Health Check Backend
    async function checkBackendHealth() {
        const startTime = Date.now();
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3500);

            const res = await fetch(`${AppState.backendUrl}/health`, {
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (res.ok) {
                const data = await res.json();
                const latency = Date.now() - startTime;
                AppState.backendOnline = data.status === 'healthy' || data.model_loaded;
                updateStatusUI(AppState.backendOnline, latency);
                return { success: true, latency };
            }
        } catch (err) {
            AppState.backendOnline = false;
            updateStatusUI(false);
            return { success: false, error: err.message };
        }
        AppState.backendOnline = false;
        updateStatusUI(false);
        return { success: false };
    }

    function updateStatusUI(online, latency) {
        if (DOM.statusBadge && DOM.statusText && DOM.statusPing) {
            if (online) {
                DOM.statusBadge.className = 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#04e797]/15 text-[#04e797] border border-[#04e797]/30';
                DOM.statusPing.className = 'w-2 h-2 rounded-full bg-[#04e797] pulse-ring';
                DOM.statusText.textContent = `Online (${latency || '<50'}ms)`;
            } else {
                DOM.statusBadge.className = 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30';
                DOM.statusPing.className = 'w-2 h-2 rounded-full bg-rose-500';
                DOM.statusText.textContent = 'Backend Offline';
            }
        }

        // Also update landing badges if present
        document.querySelectorAll('.landing-status-badge').forEach(badge => {
            if (online) {
                badge.className = 'landing-status-badge hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#04e797]/10 text-[#04e797] border border-[#04e797]/30';
                badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-[#04e797] pulse-ring"></span><span>AI Engine Siap (${latency || '<50'}ms)</span>`;
            } else {
                badge.className = 'landing-status-badge hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30';
                badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-500"></span><span>Server Offline</span>`;
            }
        });
    }

    // Session Management
    function createNewSession() {
        const newSession = {
            id: 'session_' + Date.now(),
            title: 'Percakapan Baru',
            createdAt: new Date().toISOString(),
            messages: []
        };
        AppState.sessions.unshift(newSession);
        AppState.activeSessionId = newSession.id;
        saveSessions();
        renderSessionList();
        renderMessages();
        DOM.userInput.focus();
    }

    function saveSessions() {
        localStorage.setItem('kawankerja_sessions', JSON.stringify(AppState.sessions));
    }

    function getActiveSession() {
        return AppState.sessions.find(s => s.id === AppState.activeSessionId);
    }

    function renderSessionList() {
        if (!DOM.sessionList) return;
        DOM.sessionList.innerHTML = '';

        if (AppState.sessions.length === 0) {
            DOM.sessionList.innerHTML = `
                <div class="px-3 py-4 text-xs text-[#e0fff6]/50 text-center">
                    Belum ada riwayat percakapan.
                </div>
            `;
            return;
        }

        AppState.sessions.forEach(session => {
            const isActive = session.id === AppState.activeSessionId;
            const item = document.createElement('div');
            item.className = `group flex items-center justify-between px-3 py-2.5 rounded-xl text-sm transition-all cursor-pointer ${
                isActive 
                    ? 'bg-gradient-to-r from-cyan-500/20 to-[#04e797]/15 text-cyan-300 border border-cyan-400/40 font-bold' 
                    : 'text-[#e0fff6]/70 hover:bg-[#022119] hover:text-[#e0fff6]'
            }`;

            item.innerHTML = `
                <div class="flex items-center gap-2.5 min-w-0 flex-1">
                    <i data-lucide="${isActive ? 'message-square-text' : 'message-square'}" class="w-4 h-4 shrink-0 ${isActive ? 'text-cyan-400' : 'text-[#04e797]/60'}"></i>
                    <span class="truncate">${escapeHtml(session.title || 'Percakapan')}</span>
                </div>
                <button class="delete-session-btn opacity-0 group-hover:opacity-100 hover:text-rose-400 p-1 transition-opacity" title="Hapus Chat">
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                </button>
            `;

            item.addEventListener('click', (e) => {
                if (e.target.closest('.delete-session-btn')) return;
                switchSession(session.id);
            });

            const delBtn = item.querySelector('.delete-session-btn');
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteSession(session.id);
            });

            DOM.sessionList.appendChild(item);
        });

        if (window.lucide) window.lucide.createIcons();
    }

    function switchSession(id) {
        if (AppState.isGenerating) return;
        AppState.activeSessionId = id;
        renderSessionList();
        renderMessages();
        closeMobileSidebar();
    }

    function deleteSession(id) {
        AppState.sessions = AppState.sessions.filter(s => s.id !== id);
        saveSessions();
        if (AppState.activeSessionId === id) {
            if (AppState.sessions.length > 0) {
                AppState.activeSessionId = AppState.sessions[0].id;
            } else {
                createNewSession();
                return;
            }
        }
        renderSessionList();
        renderMessages();
    }

    // Message Rendering with Multi-Color Aesthetics
    function renderMessages() {
        const session = getActiveSession();
        if (!session || session.messages.length === 0) {
            DOM.chatContainer.innerHTML = '';
            if (DOM.welcomeHero) {
                DOM.welcomeHero.classList.remove('hidden');
                DOM.chatContainer.appendChild(DOM.welcomeHero);
            }
            return;
        }

        if (DOM.welcomeHero) {
            DOM.welcomeHero.classList.add('hidden');
        }
        DOM.chatContainer.innerHTML = '';

        session.messages.forEach((msg, idx) => {
            appendMessageToUI(msg, idx);
        });

        scrollToBottom();
    }

    function appendMessageToUI(msg, index) {
        if (DOM.welcomeHero && DOM.welcomeHero.parentNode === DOM.chatContainer) {
            DOM.welcomeHero.classList.add('hidden');
            DOM.chatContainer.removeChild(DOM.welcomeHero);
        }

        const messageEl = document.createElement('div');
        messageEl.className = 'w-full max-w-4xl mx-auto py-3 px-2 sm:px-4';
        messageEl.dataset.index = index;

        if (msg.role === 'user') {
            messageEl.innerHTML = `
                <div class="flex items-start justify-end gap-3">
                    <div class="max-w-[85%] sm:max-w-[75%] rounded-2xl rounded-tr-sm bg-[#062019] text-[#e0fff6] px-4 py-3 shadow-md text-sm sm:text-base leading-relaxed border border-[#04e797]/30">
                        ${escapeHtml(msg.content)}
                    </div>
                    <div class="w-8 h-8 rounded-full bg-[#022119] border border-[#04e797]/35 flex items-center justify-center shrink-0 text-[#04e797] shadow-sm">
                        <i data-lucide="user" class="w-4 h-4"></i>
                    </div>
                </div>
            `;
        } else {
            // Assistant Message with Clean Legal Hierarchy
            const safeHtml = formatMarkdown(msg.content);
            const standaloneSnippet = msg.standalone && msg.standalone !== msg.original_question
                ? `<div class="mb-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#00140f] text-cyan-300 border border-cyan-500/30 shadow-sm">
                    <i data-lucide="git-branch" class="w-3.5 h-3.5 text-cyan-400"></i>
                    <span>Konteks Pertanyaan: <em class="text-amber-200 font-medium">${escapeHtml(msg.standalone)}</em></span>
                   </div>`
                : '';

            // Sources list with Official Legal Citations
            let sourcesSnippet = '';
            if (msg.sources && msg.sources.length > 0) {
                const sourceCards = msg.sources.map((s, sIdx) => `
                    <button class="source-chip text-left flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs bg-[#00140f] hover:bg-cyan-500/15 text-[#e0fff6] border border-cyan-500/30 hover:border-cyan-400 transition-all shadow-sm group cursor-pointer" data-src-idx="${sIdx}">
                        <i data-lucide="file-check-2" class="w-3.5 h-3.5 text-cyan-400 shrink-0 group-hover:scale-110 transition-transform"></i>
                        <span class="font-medium text-[#e0fff6] truncate max-w-[150px] sm:max-w-[200px]">${escapeHtml(s.source)}</span>
                        <span class="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono text-[10px] font-bold">Hal. ${s.page}</span>
                    </button>
                `).join('');

                sourcesSnippet = `
                    <div class="mt-4 pt-3 border-t border-[#04e797]/20">
                        <div class="flex items-center gap-1.5 text-xs font-semibold text-[#04e797] mb-2">
                            <i data-lucide="scale" class="w-3.5 h-3.5"></i>
                            <span>Rujukan Regulasi Resmi PP No. 35/2021 (${msg.sources.length} Dokumen):</span>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            ${sourceCards}
                        </div>
                    </div>
                `;
            }

            messageEl.innerHTML = `
                <div class="flex items-start gap-3">
                    <div class="w-8 h-8 rounded-full bg-[#022119] border border-[#04e797]/40 text-[#04e797] font-bold flex items-center justify-center shrink-0 shadow-md shadow-[#04e797]/15">
                        <i data-lucide="scale" class="w-4 h-4"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="glass-card rounded-2xl rounded-tl-sm p-4 sm:p-5 shadow-lg border border-[#04e797]/25 bg-[#022119]/85 relative overflow-hidden">
                            <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#04e797] via-[#06b6d4] to-transparent"></div>
                            ${standaloneSnippet}
                            <div class="markdown-body text-[#e0fff6]">
                                ${safeHtml}
                            </div>
                            ${sourcesSnippet}
                        </div>
                        <!-- Action Bar -->
                        <div class="flex items-center gap-1 mt-1.5 px-2 text-xs text-[#e0fff6]/50">
                            <button class="copy-btn hover:text-cyan-300 p-1.5 rounded-lg hover:bg-[#022119] transition" title="Salin Jawaban">
                                <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                            </button>
                            <button class="tts-btn hover:text-amber-300 p-1.5 rounded-lg hover:bg-[#022119] transition" title="Dengarkan Suara (TTS)">
                                <i data-lucide="volume-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <span class="text-[11px] text-[#04e797] ml-auto flex items-center gap-1 font-semibold">
                                <i data-lucide="check-check" class="w-3 h-3 text-[#04e797]"></i> Terverifikasi PP No. 35/2021
                            </span>
                        </div>
                    </div>
                </div>
            `;

            // Setup listeners for copy and tts
            const copyBtn = messageEl.querySelector('.copy-btn');
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(msg.content);
                copyBtn.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5 text-[#04e797]"></i>';
                if (window.lucide) window.lucide.createIcons();
                setTimeout(() => {
                    copyBtn.innerHTML = '<i data-lucide="copy" class="w-3.5 h-3.5"></i>';
                    if (window.lucide) window.lucide.createIcons();
                }, 2000);
            });

            const ttsBtn = messageEl.querySelector('.tts-btn');
            ttsBtn.addEventListener('click', () => {
                playTextToSpeech(msg.content, ttsBtn);
            });

            // Source click listeners
            if (msg.sources) {
                const sourceChips = messageEl.querySelectorAll('.source-chip');
                sourceChips.forEach(chip => {
                    chip.addEventListener('click', () => {
                        const sIdx = parseInt(chip.dataset.srcIdx, 10);
                        openSourceModal(msg.sources[sIdx]);
                    });
                });
            }
        }

        DOM.chatContainer.appendChild(messageEl);
        if (window.lucide) window.lucide.createIcons();
    }

    // Scroll chat to bottom with requestAnimationFrame
    function scrollToBottom(smooth = true) {
        if (!DOM.chatContainer) return;
        requestAnimationFrame(() => {
            DOM.chatContainer.scrollTo({
                top: DOM.chatContainer.scrollHeight,
                behavior: smooth ? 'smooth' : 'auto'
            });
        });
    }

    // Text to Speech
    function playTextToSpeech(text, btnElement) {
        if (!('speechSynthesis' in window)) {
            alert('Browser Anda tidak mendukung Speech Synthesis.');
            return;
        }

        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            if (AppState.speakingUtterance === text) {
                AppState.speakingUtterance = null;
                btnElement.innerHTML = '<i data-lucide="volume-2" class="w-3.5 h-3.5"></i>';
                if (window.lucide) window.lucide.createIcons();
                return;
            }
        }

        const plainText = text.replace(/[*#`_\[\]()>-]/g, ' ').replace(/\s+/g, ' ');
        const utterance = new SpeechSynthesisUtterance(plainText);
        utterance.lang = 'id-ID';
        utterance.rate = 1.0;

        AppState.speakingUtterance = text;
        btnElement.innerHTML = '<i data-lucide="square" class="w-3.5 h-3.5 text-rose-500"></i>';
        if (window.lucide) window.lucide.createIcons();

        utterance.onend = () => {
            AppState.speakingUtterance = null;
            btnElement.innerHTML = '<i data-lucide="volume-2" class="w-3.5 h-3.5"></i>';
            if (window.lucide) window.lucide.createIcons();
        };

        utterance.onerror = () => {
            AppState.speakingUtterance = null;
            btnElement.innerHTML = '<i data-lucide="volume-2" class="w-3.5 h-3.5"></i>';
            if (window.lucide) window.lucide.createIcons();
        };

        window.speechSynthesis.speak(utterance);
    }

    // Speech to Text (Microphone)
    function initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            DOM.micBtn.style.display = 'none';
            return;
        }

        const recognizer = new SpeechRecognition();
        recognizer.lang = 'id-ID';
        recognizer.continuous = false;
        recognizer.interimResults = false;

        recognizer.onstart = () => {
            AppState.isListening = true;
            DOM.micBtn.classList.add('text-rose-400', 'animate-pulse');
            DOM.userInput.placeholder = 'Sedang mendengarkan suara Anda...';
        };

        recognizer.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            DOM.userInput.value = transcript;
            autoResizeTextarea();
        };

        recognizer.onend = () => {
            AppState.isListening = false;
            DOM.micBtn.classList.remove('text-rose-400', 'animate-pulse');
            DOM.userInput.placeholder = 'Tanyakan tentang batas PKWT, kompensasi, jam lembur, pesangon PHK...';
        };

        recognizer.onerror = () => {
            AppState.isListening = false;
            DOM.micBtn.classList.remove('text-rose-400', 'animate-pulse');
            DOM.userInput.placeholder = 'Tanyakan tentang batas PKWT, kompensasi, jam lembur, pesangon PHK...';
        };

        AppState.speechRecognizer = recognizer;
    }

    function toggleSpeechRecognition() {
        if (!AppState.speechRecognizer) return;
        if (AppState.isListening) {
            AppState.speechRecognizer.stop();
        } else {
            AppState.speechRecognizer.start();
        }
    }

    // Format Markdown safely
    function formatMarkdown(text) {
        if (!text) return '';
        if (window.marked) {
            const rawHtml = window.marked.parse(text);
            if (window.DOMPurify) {
                return window.DOMPurify.sanitize(rawHtml);
            }
            return rawHtml;
        }
        return escapeHtml(text);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Handle Form Submit & Messaging
    async function handleUserSubmit(e) {
        if (e) e.preventDefault();
        const text = DOM.userInput.value.trim();
        if (!text || AppState.isGenerating) return;

        let session = getActiveSession();
        if (!session) {
            createNewSession();
            session = getActiveSession();
        }

        // Set session title if first user message
        if (session.messages.length === 0) {
            session.title = text.slice(0, 32) + (text.length > 32 ? '...' : '');
            renderSessionList();
        }

        // Append User Message
        const userMsg = {
            role: 'user',
            content: text,
            timestamp: new Date().toISOString()
        };
        session.messages.push(userMsg);
        saveSessions();
        appendMessageToUI(userMsg, session.messages.length - 1);

        // Reset input
        DOM.userInput.value = '';
        DOM.userInput.style.height = 'auto';
        scrollToBottom();

        // Send to Backend with full legal citations (/api/chat)
        await handleStandardQuery(text, session);
    }

    // Standard JSON Query (/api/chat)
    async function handleStandardQuery(question, session) {
        setGeneratingState(true);
        const thinkingEl = createThinkingPlaceholder();
        DOM.chatContainer.appendChild(thinkingEl);
        scrollToBottom();

        const historyPayload = session.messages.slice(0, -1).map(m => ({
            role: m.role,
            content: m.content
        }));

        AppState.abortController = new AbortController();

        try {
            const resp = await fetch(`${AppState.backendUrl}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    chat_history: historyPayload
                }),
                signal: AppState.abortController.signal
            });

            if (!resp.ok) {
                const errDetail = await resp.text();
                throw new Error(`Server status ${resp.status}: ${errDetail}`);
            }

            const data = await resp.json();
            thinkingEl.remove();

            const assistantMsg = {
                role: 'assistant',
                content: data.answer,
                standalone: data.standalone_question,
                original_question: question,
                sources: data.sources || [],
                timestamp: new Date().toISOString()
            };

            session.messages.push(assistantMsg);
            saveSessions();
            appendMessageToUI(assistantMsg, session.messages.length - 1);
            scrollToBottom();

        } catch (err) {
            thinkingEl.remove();
            if (err.name === 'AbortError') {
                console.log('Permintaan dibatalkan pengguna.');
            } else {
                appendErrorUI(err.message);
            }
        } finally {
            setGeneratingState(false);
            AppState.abortController = null;
        }
    }

    // Thinking Indicator with Grounded Legal Scale Accent
    function createThinkingPlaceholder() {
        const el = document.createElement('div');
        el.className = 'w-full max-w-4xl mx-auto py-3 px-2 sm:px-4';
        el.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-full bg-[#022119] border border-[#04e797]/40 text-[#04e797] font-bold flex items-center justify-center shrink-0 shadow-md shadow-[#04e797]/15">
                    <i data-lucide="scale" class="w-4 h-4 text-[#04e797]"></i>
                </div>
                <div class="glass-card rounded-2xl rounded-tl-sm p-4 sm:p-5 shadow-lg max-w-md w-full border border-[#04e797]/30 bg-[#022119] relative overflow-hidden">
                    <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#04e797] via-cyan-400 to-transparent animate-pulse"></div>
                    <div class="flex items-center gap-2 mb-3">
                        <div class="flex items-center gap-1">
                            <span class="w-2 h-2 rounded-full bg-[#04e797] animate-ping"></span>
                            <span class="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                            <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                        </div>
                        <span class="text-xs font-semibold text-[#04e797]">Mencari rujukan pasal PP No. 35/2021 & menalar...</span>
                    </div>
                    <div class="space-y-2">
                        <div class="h-3 rounded-md skeleton-shimmer w-3/4"></div>
                        <div class="h-3 rounded-md skeleton-shimmer w-full"></div>
                        <div class="h-3 rounded-md skeleton-shimmer w-5/6"></div>
                    </div>
                </div>
            </div>
        `;
        if (window.lucide) window.lucide.createIcons();
        return el;
    }

    function appendErrorUI(message) {
        const errorEl = document.createElement('div');
        errorEl.className = 'w-full max-w-4xl mx-auto py-3 px-2 sm:px-4';
        errorEl.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-full bg-rose-600 text-white flex items-center justify-center shrink-0 shadow-md shadow-rose-600/30">
                    <i data-lucide="alert-triangle" class="w-4 h-4"></i>
                </div>
                <div class="glass-card rounded-2xl rounded-tl-sm p-4 border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm max-w-lg">
                    <div class="font-bold mb-1 text-rose-400">Gagal Menghubungi Mesin AI</div>
                    <p class="text-xs leading-relaxed opacity-90">${escapeHtml(message)}</p>
                    <div class="mt-2.5 pt-2 border-t border-rose-500/20 text-xs text-[#e0fff6]/60">
                        Pastikan backend FastAPI sudah berjalan di terminal:
                        <code class="block mt-1 p-1.5 rounded bg-[#00140f] text-[#04e797] font-mono text-[11px] border border-[#04e797]/20">uvicorn backend.api:app --reload</code>
                    </div>
                </div>
            </div>
        `;
        DOM.chatContainer.appendChild(errorEl);
        if (window.lucide) window.lucide.createIcons();
        scrollToBottom();
    }

    function setGeneratingState(generating) {
        AppState.isGenerating = generating;
        if (generating) {
            DOM.sendBtn.classList.add('hidden');
            DOM.stopBtn.classList.remove('hidden');
        } else {
            DOM.sendBtn.classList.remove('hidden');
            DOM.stopBtn.classList.add('hidden');
        }
    }

    function stopGeneration() {
        if (AppState.abortController) {
            AppState.abortController.abort();
            AppState.abortController = null;
        }
        setGeneratingState(false);
    }

    // Source Reference Modal
    function openSourceModal(source) {
        if (!DOM.sourceModal || !DOM.sourceModalContent || !DOM.sourceModalTitle) return;
        DOM.sourceModalTitle.textContent = `${source.source} — Halaman ${source.page}`;
        DOM.sourceModalContent.textContent = source.snippet;
        DOM.sourceModal.classList.remove('hidden');
    }

    function closeSourceModal() {
        if (DOM.sourceModal) DOM.sourceModal.classList.add('hidden');
    }

    // Auto resize textarea
    function autoResizeTextarea() {
        DOM.userInput.style.height = 'auto';
        const newHeight = Math.min(DOM.userInput.scrollHeight, 180);
        DOM.userInput.style.height = newHeight + 'px';
    }

    // Mobile Sidebar Drawer
    function openMobileSidebar() {
        DOM.sidebar.classList.remove('-translate-x-full');
        DOM.sidebarBackdrop.classList.remove('hidden');
    }

    function closeMobileSidebar() {
        DOM.sidebar.classList.add('-translate-x-full');
        DOM.sidebarBackdrop.classList.add('hidden');
    }

    // Export Chat to Markdown
    function exportChatAsMarkdown() {
        const session = getActiveSession();
        if (!session || session.messages.length === 0) {
            alert('Tidak ada percakapan untuk diekspor.');
            return;
        }

        let md = `# ${session.title}\n`;
        md += `_Diekspor dari KawanKerja AI (PP No. 35/2021) pada ${new Date().toLocaleString('id-ID')}_\n\n---\n\n`;

        session.messages.forEach(msg => {
            if (msg.role === 'user') {
                md += `### 👤 Pertanyaan:\n${msg.content}\n\n`;
            } else {
                md += `### 💼 Jawaban KawanKerja AI:\n${msg.content}\n\n`;
                if (msg.sources && msg.sources.length > 0) {
                    md += `**Rujukan Dokumen:**\n`;
                    msg.sources.forEach(s => {
                        md += `- **${s.source}** (Hal. ${s.page}): _"${s.snippet}"_\n`;
                    });
                    md += `\n`;
                }
                md += `---\n\n`;
            }
        });

        const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `KawanKerja_Konsultasi_${Date.now()}.md`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // Settings Modal
    function openSettingsModal() {
        DOM.settingsBackendUrl.value = AppState.backendUrl;
        DOM.settingsPingResult.textContent = '';
        DOM.settingsModal.classList.remove('hidden');
    }

    function closeSettingsModal() {
        DOM.settingsModal.classList.add('hidden');
    }

    async function testBackendPing() {
        DOM.settingsPingResult.textContent = 'Mengecek koneksi...';
        DOM.settingsPingResult.className = 'text-xs text-amber-400 font-bold';

        const testUrl = DOM.settingsBackendUrl.value.trim().replace(/\/$/, '');
        const start = Date.now();
        try {
            const res = await fetch(`${testUrl}/health`, { signal: AbortSignal.timeout(3500) });
            if (res.ok) {
                const latency = Date.now() - start;
                DOM.settingsPingResult.textContent = `✅ Tersambung (${latency}ms)`;
                DOM.settingsPingResult.className = 'text-xs text-[#04e797] font-bold';
            } else {
                DOM.settingsPingResult.textContent = `❌ Server merespons ${res.status}`;
                DOM.settingsPingResult.className = 'text-xs text-rose-400 font-bold';
            }
        } catch (e) {
            DOM.settingsPingResult.textContent = `❌ Gagal: ${e.message}`;
            DOM.settingsPingResult.className = 'text-xs text-rose-400 font-bold';
        }
    }

    function saveSettings() {
        const newUrl = DOM.settingsBackendUrl.value.trim().replace(/\/$/, '');
        if (newUrl) {
            AppState.backendUrl = newUrl;
            localStorage.setItem('kawankerja_backend_url', newUrl);
            checkBackendHealth();
        }
        closeSettingsModal();
    }

    // Calculator Modal & Bindings
    function initCalculator() {
        // Tab switching
        const tabs = document.querySelectorAll('.calc-tab-btn');
        const contents = document.querySelectorAll('.calc-tab-content');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => {
                    t.classList.remove('active', 'border-[#04e797]', 'text-[#04e797]', 'border-amber-400', 'text-amber-300', 'border-rose-400', 'text-rose-300');
                    t.classList.add('border-transparent', 'text-[#e0fff6]/60');
                });

                const target = tab.dataset.target;
                if (target === 'tab-pkwt') {
                    tab.classList.add('active', 'border-[#04e797]', 'text-[#04e797]');
                } else if (target === 'tab-lembur') {
                    tab.classList.add('active', 'border-amber-400', 'text-amber-300');
                } else {
                    tab.classList.add('active', 'border-rose-400', 'text-rose-300');
                }
                tab.classList.remove('border-transparent', 'text-[#e0fff6]/60');

                contents.forEach(c => {
                    if (c.id === target) c.classList.remove('hidden');
                    else c.classList.add('hidden');
                });
            });
        });

        // 1. PKWT Calc (Modal)
        const pkwtMonths = document.getElementById('calc-pkwt-months');
        const pkwtWage = document.getElementById('calc-pkwt-wage');
        const pkwtResult = document.getElementById('calc-pkwt-result');
        const pkwtFormula = document.getElementById('calc-pkwt-formula');
        const pkwtAskAi = document.getElementById('calc-pkwt-ask-ai');

        function updatePKWT() {
            const m = parseFloat(pkwtMonths.value) || 0;
            const w = parseFloat(pkwtWage.value) || 0;
            const res = window.LegalCalculator.calculatePKWTCompensation(m, w);
            pkwtResult.textContent = window.LegalCalculator.formatRupiah(res.amount);
            pkwtFormula.textContent = res.formula + (res.reason ? ` (${res.reason})` : '');
        }

        if (pkwtMonths && pkwtWage) {
            pkwtMonths.addEventListener('input', updatePKWT);
            pkwtWage.addEventListener('input', updatePKWT);
        }

        if (pkwtAskAi) {
            pkwtAskAi.addEventListener('click', () => {
                const m = pkwtMonths.value;
                const w = window.LegalCalculator.formatRupiah(parseFloat(pkwtWage.value) || 0);
                const prompt = `Berdasarkan PP No. 35 Tahun 2021 Pasal 15, berapa uang kompensasi PKWT untuk masa kerja ${m} bulan dengan upah bulanan ${w}? Bagaimana aturan waktu pembayarannya?`;
                DOM.calcModal.classList.add('hidden');
                switchToChatView(prompt);
            });
        }

        // 2. Overtime Calc (Amber Theme)
        const otWage = document.getElementById('calc-ot-wage');
        const otHours = document.getElementById('calc-ot-hours');
        const otType = document.getElementById('calc-ot-type');
        const otResult = document.getElementById('calc-ot-result');
        const otHourly = document.getElementById('calc-ot-hourly');
        const otBreakdown = document.getElementById('calc-ot-breakdown');
        const otAskAi = document.getElementById('calc-ot-ask-ai');

        function updateOvertime() {
            const w = parseFloat(otWage.value) || 0;
            const h = parseFloat(otHours.value) || 0;
            const type = otType.value;
            const res = window.LegalCalculator.calculateOvertimeWage(w, h, type);

            otResult.textContent = window.LegalCalculator.formatRupiah(res.totalPay);
            otHourly.textContent = `Upah 1 Jam (1/173): ${window.LegalCalculator.formatRupiah(res.hourlyRate)}`;
            otBreakdown.innerHTML = res.breakdown.map(b => `<li>${b}</li>`).join('');
        }

        if (otWage && otHours && otType) {
            otWage.addEventListener('input', updateOvertime);
            otHours.addEventListener('input', updateOvertime);
            otType.addEventListener('change', updateOvertime);
        }

        if (otAskAi) {
            otAskAi.addEventListener('click', () => {
                const w = window.LegalCalculator.formatRupiah(parseFloat(otWage.value) || 0);
                const h = otHours.value;
                const typeStr = otType.value === 'workday' ? 'hari kerja biasa' : 'hari libur resmi';
                const prompt = `Bagaimana cara menghitung upah lembur ${h} jam pada ${typeStr} dengan gaji sebulan ${w} sesuai Pasal 31-32 PP 35/2021?`;
                DOM.calcModal.classList.add('hidden');
                switchToChatView(prompt);
            });
        }

        // 3. Severance PHK Calc (Rose Theme)
        const phkYears = document.getElementById('calc-phk-years');
        const phkWage = document.getElementById('calc-phk-wage');
        const phkReason = document.getElementById('calc-phk-reason');
        const phkResult = document.getElementById('calc-phk-result');
        const phkDetail = document.getElementById('calc-phk-detail');
        const phkAskAi = document.getElementById('calc-phk-ask-ai');

        function updateSeverance() {
            const y = parseFloat(phkYears.value) || 0;
            const w = parseFloat(phkWage.value) || 0;
            const mult = parseFloat(phkReason.value) || 1.0;
            const res = window.LegalCalculator.calculateSeverance(y, w, mult);

            phkResult.textContent = window.LegalCalculator.formatRupiah(res.totalEstimate);
            phkDetail.textContent = `Pesangon (${res.pesangonMonths} bln × ${mult}x): ${window.LegalCalculator.formatRupiah(res.totalPesangon)} | UPMK (${res.upmkMonths} bln): ${window.LegalCalculator.formatRupiah(res.totalUPMK)}`;
        }

        if (phkYears && phkWage && phkReason) {
            phkYears.addEventListener('input', updateSeverance);
            phkWage.addEventListener('input', updateSeverance);
            phkReason.addEventListener('change', updateSeverance);
        }

        if (phkAskAi) {
            phkAskAi.addEventListener('click', () => {
                const y = phkYears.value;
                const w = window.LegalCalculator.formatRupiah(parseFloat(phkWage.value) || 0);
                const reasonText = phkReason.options[phkReason.selectedIndex].text;
                const prompt = `Karyawan mengalami PHK dengan masa kerja ${y} tahun, upah sebulan ${w}, alasan: "${reasonText}". Hitung hak Pesangon & UPMK berdasarkan Pasal 40-59 PP 35/2021.`;
                DOM.calcModal.classList.add('hidden');
                switchToChatView(prompt);
            });
        }

        // 4. Landing Page Embedded Calculator
        const lMonths = document.getElementById('landing-calc-months');
        const lWage = document.getElementById('landing-calc-wage');
        const lResult = document.getElementById('landing-calc-result');
        const lFormula = document.getElementById('landing-calc-formula');
        const lAskBtn = document.getElementById('landing-calc-ask-btn');

        if (lMonths && lWage && lResult) {
            function updateLandingCalc() {
                const m = parseFloat(lMonths.value) || 0;
                const w = parseFloat(lWage.value) || 0;
                const res = window.LegalCalculator.calculatePKWTCompensation(m, w);
                lResult.textContent = window.LegalCalculator.formatRupiah(res.amount);
                lFormula.textContent = res.formula + (res.reason ? ` (${res.reason})` : '');
            }

            lMonths.addEventListener('input', updateLandingCalc);
            lWage.addEventListener('input', updateLandingCalc);

            if (lAskBtn) {
                lAskBtn.addEventListener('click', () => {
                    const m = lMonths.value;
                    const w = window.LegalCalculator.formatRupiah(parseFloat(lWage.value) || 0);
                    const prompt = `Berdasarkan PP No. 35 Tahun 2021 Pasal 15, berapa uang kompensasi PKWT untuk masa kerja ${m} bulan dengan upah bulanan ${w}? Bagaimana aturan waktu pembayarannya?`;
                    switchToChatView(prompt);
                });
            }
        }
    }

    // Setup Event Listeners
    function setupEventListeners() {
        // Landing navigation & Enter Chat buttons
        document.querySelectorAll('.enter-chat-btn').forEach(btn => {
            btn.addEventListener('click', () => switchToChatView());
        });

        document.querySelectorAll('.landing-prompt-card').forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.dataset.prompt;
                switchToChatView(prompt);
            });
        });

        if (DOM.backToLandingBtn) {
            DOM.backToLandingBtn.addEventListener('click', switchToLandingView);
        }

        // Scroll-to-bottom floating button
        if (DOM.chatContainer && DOM.scrollBottomBtn) {
            DOM.chatContainer.addEventListener('scroll', () => {
                const distFromBottom = DOM.chatContainer.scrollHeight - DOM.chatContainer.scrollTop - DOM.chatContainer.clientHeight;
                if (distFromBottom > 160) {
                    DOM.scrollBottomBtn.classList.remove('hidden');
                } else {
                    DOM.scrollBottomBtn.classList.add('hidden');
                }
            });

            DOM.scrollBottomBtn.addEventListener('click', () => {
                scrollToBottom(true);
            });
        }

        // Sidebar & Session
        DOM.newChatBtn.addEventListener('click', createNewSession);
        DOM.mobileSidebarBtn.addEventListener('click', openMobileSidebar);
        DOM.sidebarBackdrop.addEventListener('click', closeMobileSidebar);

        // Clear Chat
        DOM.clearChatBtn.addEventListener('click', () => {
            const session = getActiveSession();
            if (session && confirm('Hapus semua pesan dalam percakapan ini?')) {
                session.messages = [];
                saveSessions();
                renderMessages();
            }
        });

        // Export Chat
        DOM.exportChatBtn.addEventListener('click', exportChatAsMarkdown);

        // Chat Form
        DOM.chatForm.addEventListener('submit', handleUserSubmit);
        DOM.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleUserSubmit();
            }
        });
        DOM.userInput.addEventListener('input', autoResizeTextarea);

        // Stop generation
        DOM.stopBtn.addEventListener('click', stopGeneration);

        // Mic
        DOM.micBtn.addEventListener('click', toggleSpeechRecognition);

        // Modals
        DOM.calcOpenBtn.addEventListener('click', () => DOM.calcModal.classList.remove('hidden'));
        DOM.calcCloseBtn.addEventListener('click', () => DOM.calcModal.classList.add('hidden'));
        DOM.settingsOpenBtn.addEventListener('click', openSettingsModal);
        DOM.settingsCloseBtn.addEventListener('click', closeSettingsModal);
        DOM.settingsTestPingBtn.addEventListener('click', testBackendPing);
        DOM.settingsSaveBtn.addEventListener('click', saveSettings);
        DOM.sourceModalClose.addEventListener('click', closeSourceModal);

        // Quick prompt chips in welcome hero & quick consultation
        document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const prompt = btn.getAttribute('data-prompt') || btn.innerText.trim();
                DOM.userInput.value = prompt;
                autoResizeTextarea();
                handleUserSubmit();
            });
        });

        // Close modals on clicking backdrop
        window.addEventListener('click', (e) => {
            if (e.target === DOM.calcModal) DOM.calcModal.classList.add('hidden');
            if (e.target === DOM.settingsModal) DOM.settingsModal.classList.add('hidden');
            if (e.target === DOM.sourceModal) DOM.sourceModal.classList.add('hidden');
        });

        // Browser Hash Navigation
        window.addEventListener('hashchange', () => {
            if (window.location.hash === '#chat') {
                switchToChatView();
            } else {
                switchToLandingView();
            }
        });
    }

    // App Initialization
    function init() {
        localStorage.removeItem('kawankerja_stream_mode');
        initSpeechRecognition();
        initCalculator();
        initSmoothScrolling();
        initScrollAnimations();
        initLegalHeroAnimation();
        setupEventListeners();

        // Load or create initial session
        if (AppState.sessions.length === 0) {
            createNewSession();
        } else {
            AppState.activeSessionId = AppState.sessions[0].id;
            renderSessionList();
            renderMessages();
        }

        // Route check on load
        if (window.location.hash === '#chat') {
            switchToChatView();
        } else {
            switchToLandingView();
        }

        // Check backend health immediately and every 30s
        checkBackendHealth();
        setInterval(checkBackendHealth, 30000);

        // Create lucide icons
        if (window.lucide) window.lucide.createIcons();
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
