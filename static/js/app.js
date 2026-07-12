/**
 * AI Code Reviewer - Client-Side Application Logic
 * Merges Accordion Professional Report UI with Real-Time Backend Polling.
 */
document.addEventListener('DOMContentLoaded', () => {
    // ==========================================
    // 1. OLLAMA STATUS LOGIC
    // ==========================================
    const ollamaIndicator = document.getElementById('ollama-status-indicator');
    const ollamaStatusText = document.getElementById('ollama-status-text');
    const ollamaDetails = document.getElementById('ollama-details');
    const ollamaDefaultModel = document.getElementById('ollama-default-model');
    const ollamaModelsList = document.getElementById('ollama-models-list');

    async function fetchOllamaStatus() {
        try {
            const response = await fetch('/ollama/health');
            if (!response.ok) throw new Error('Server unreachable');
            const data = await response.json();
            if (data.connected) {
                ollamaIndicator.classList.remove('disconnected');
                ollamaStatusText.textContent = 'Connected';
                ollamaDetails.classList.remove('hidden');
                ollamaDefaultModel.textContent = data.default_model;
                ollamaModelsList.textContent = data.available_models.length > 0 ? data.available_models.join(', ') : 'None installed';
            } else { throw new Error('Ollama not connected'); }
        } catch (error) {
            ollamaIndicator.classList.add('disconnected');
            ollamaStatusText.textContent = 'Disconnected';
            ollamaDetails.classList.add('hidden');
        }
    }
    fetchOllamaStatus();

    // ==========================================
    // 2. DOM ELEMENTS & STATE
    // ==========================================
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const fileInfo = document.getElementById('file-info');
    const fileNameDisplay = document.getElementById('file-name');
    const fileMetaDisplay = document.getElementById('file-meta');
    const resetBtn = document.getElementById('reset-btn');
    const actionButtons = document.getElementById('action-buttons');
    const analyzeBtn = document.getElementById('analyze-btn');
    const uploadStatus = document.getElementById('upload-status');

    const reviewProgress = document.getElementById('review-progress');
    const stagesList = document.getElementById('stages-list');
    const progressBar = document.getElementById('progress-bar');
    const progressTimer = document.getElementById('progress-timer');
    const stageCurrent = document.getElementById('stage-current');
    const stageTotal = document.getElementById('stage-total');

    const aiSuccessState = document.getElementById('ai-success-state');
    const aiErrorState = document.getElementById('ai-error-state');
    const retryBtn = document.getElementById('retry-btn');
    const errorMessage = document.getElementById('error-message');

    const reviewResults = document.getElementById('review-results');
    const reportFilename = document.getElementById('report-filename');
    const reportLanguage = document.getElementById('report-language');
    const reportDuration = document.getElementById('report-duration');
    const reportScore = document.getElementById('report-score');
    const scoreRating = document.getElementById('score-rating');
    const scoreCard = document.getElementById('score-card');
    const reportSummaryText = document.getElementById('report-summary-text');
    const statsGrid = document.getElementById('stats-grid');
    const downloadJsonBtn = document.getElementById('download-json-btn');
    const reportRecommendation = document.getElementById('report-recommendation');
    const reportConclusionText = document.getElementById('report-conclusion-text');

    let selectedFile = null;
    let currentReviewData = null;
    let timerInterval = null;
    let pollInterval = null;
    let elapsedSeconds = 0;
    let lastReportedStage = -1;

    const ALLOWED_EXTENSIONS = new Set(['.py', '.java', '.js', '.ts', '.cpp', '.c', '.cs', '.go', '.rs', '.php', '.kt', '.swift', '.txt']);
    const MAX_FILE_SIZE = 10 * 1024 * 1024;

    const REVIEW_STAGES = [
        { name: 'Upload Source Code', message: 'Reading uploaded file...' },
        { name: 'Detect Programming Language', message: 'Detecting language...' },
        { name: 'Build Review Prompt', message: 'Preparing AI prompt...' },
        { name: 'Stage 1 – Code Understanding', message: 'Understanding project structure...' },
        { name: 'Stage 2 – Bug & Logic Analysis', message: 'Analyzing bugs...' },
        { name: 'Stage 3 – Security Analysis', message: 'Searching for security vulnerabilities...' },
        { name: 'Stage 4 – Performance Analysis', message: 'Reviewing performance...' },
        { name: 'Stage 5 – Architecture Analysis', message: 'Reviewing architecture...' },
        { name: 'Merge Results', message: 'Merging AI responses...' },
        { name: 'Generate Final Report', message: 'Generating final report...' }
    ];

    // ==========================================
    // 3. EVENT LISTENERS
    // ==========================================
    browseBtn.addEventListener('click', (e) => { e.preventDefault(); fileInput.click(); });
    fileInput.addEventListener('change', (e) => { if (e.target.files && e.target.files.length) handleFile(e.target.files[0]); });
    resetBtn.addEventListener('click', resetUI);
    analyzeBtn.addEventListener('click', startAnalysis);
    retryBtn.addEventListener('click', startAnalysis);
    if (downloadJsonBtn) downloadJsonBtn.addEventListener('click', handleDownloadReview);

    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); if (dropZone.style.pointerEvents !== 'none') dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault(); dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files && e.dataTransfer.files.length) { handleFile(e.dataTransfer.files[0]); fileInput.files = e.dataTransfer.files; }
    });

    document.querySelectorAll('.accordion-header').forEach(header => {
        header.addEventListener('click', () => {
            const targetId = header.getAttribute('data-target');
            const content = document.getElementById(targetId);
            const item = header.closest('.accordion-item');
            if (content && item) {
                const isOpen = item.classList.contains('open');
                document.querySelectorAll('.accordion-item').forEach(i => {
                    i.classList.remove('open');
                    const c = i.querySelector('.accordion-content');
                    if (c) c.classList.add('hidden');
                });
                if (!isOpen) {
                    item.classList.add('open');
                    content.classList.remove('hidden');
                }
            }
        });
    });

    // ==========================================
    // 4. CORE LOGIC FUNCTIONS
    // ==========================================
    function handleFile(file) {
        resetStatus();
        selectedFile = file;
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXTENSIONS.has(extension)) { showStatus('Unsupported file type: ' + extension, 'error'); return; }
        if (file.size > MAX_FILE_SIZE) { showStatus('File exceeds the 10 MB size limit.', 'error'); return; }

        aiSuccessState.classList.add('hidden');
        aiErrorState.classList.add('hidden');
        reviewResults.classList.add('hidden');
        reviewProgress.classList.add('hidden');

        fileNameDisplay.textContent = file.name;
        fileMetaDisplay.textContent = formatBytes(file.size) + ' • ' + extension;
        fileInfo.classList.remove('hidden');
        actionButtons.classList.remove('hidden');
        dropZone.classList.add('hidden');
    }

    function startAnalysis() {
        if (!selectedFile) return;
        setAnalyzingState();
        startProgressTimer();

        const formData = new FormData();
        formData.append('file', selectedFile);

        // 1. Start the review and get the review_id immediately
        fetch('/review', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            if (data.review_id) {
                // 2. Navigate to Progress Screen and start polling
                startPolling(data.review_id);
            } else {
                failCurrentStage('Review failed: No review ID received.');
            }
        })
        .catch(error => { 
            console.error('Review error:', error); 
            failCurrentStage('Network error. Ensure server and Ollama are running.');
        });
    }

    function setAnalyzingState() {
        analyzeBtn.disabled = true; browseBtn.disabled = true; resetBtn.disabled = true;
        dropZone.style.pointerEvents = 'none'; dropZone.style.opacity = '0.6';
        actionButtons.classList.add('hidden');
        aiSuccessState.classList.add('hidden'); aiErrorState.classList.add('hidden');
        reviewResults.classList.add('hidden');
        reviewProgress.classList.remove('hidden');
        initializeStages();
    }

    function initializeStages() {
        stagesList.innerHTML = '';
        stageTotal.textContent = REVIEW_STAGES.length;
        stageCurrent.textContent = '0';
        progressBar.style.width = '0%';
        lastReportedStage = -1;

        REVIEW_STAGES.forEach((stage, index) => {
            const stageEl = document.createElement('div');
            stageEl.className = 'stage-item pending';
            stageEl.id = 'stage-' + index;
            stageEl.innerHTML = '<div class="stage-icon pending"></div><div class="stage-content"><div class="stage-name">' + stage.name + '</div><div class="stage-message">' + stage.message + '</div></div>';
            stagesList.appendChild(stageEl);
        });
        markStageCompleted(0); markStageCompleted(1); markStageCompleted(2);
        lastReportedStage = 2;
    }

    function markStageCompleted(index) {
        const stage = document.getElementById('stage-' + index);
        if (stage) {
            stage.classList.remove('running', 'pending');
            stage.classList.add('completed');
            const icon = stage.querySelector('.stage-icon');
            icon.className = 'stage-icon completed';
            icon.textContent = '✓';
        }
    }

    function markStageRunning(index) {
        const stage = document.getElementById('stage-' + index);
        if (stage) {
            stage.classList.remove('pending', 'completed');
            stage.classList.add('running');
            const icon = stage.querySelector('.stage-icon');
            icon.className = 'stage-icon running';
            icon.textContent = '';
            stageCurrent.textContent = index + 1;
            progressBar.style.width = ((index + 1) / REVIEW_STAGES.length * 100) + '%';
        }
    }

    function failCurrentStage(reason) {
        stopTimer(); stopPolling();
        const runningStage = document.querySelector('.stage-item.running');
        if (runningStage) {
            runningStage.classList.remove('running');
            runningStage.classList.add('failed');
            const icon = runningStage.querySelector('.stage-icon');
            icon.className = 'stage-icon failed';
            icon.textContent = '✕';
            runningStage.querySelector('.stage-message').textContent = 'Failed: ' + reason;
        }
        showError(reason);
    }

    function startProgressTimer() {
        elapsedSeconds = 0;
        progressTimer.textContent = '00:00';
        timerInterval = setInterval(() => {
            elapsedSeconds++;
            const mins = String(Math.floor(elapsedSeconds / 60)).padStart(2, '0');
            const secs = String(elapsedSeconds % 60).padStart(2, '0');
            progressTimer.textContent = mins + ':' + secs;
        }, 1000);
    }

    function stopTimer() { if (timerInterval) clearInterval(timerInterval); timerInterval = null; }

    // ==========================================
    // 5. POLLING LOGIC
    // ==========================================
    function startPolling(reviewId) {
        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/review/progress/${reviewId}`);
                
                if (!response.ok) {
                    if (response.status === 404) {
                        stopPolling();
                        failCurrentStage('Review not found on server.');
                    }
                    return;
                }
                
                const progress = await response.json();
                const backendStage = progress.stage;
                const status = progress.status;

                if (backendStage !== lastReportedStage && backendStage > lastReportedStage) {
                    for (let i = lastReportedStage + 1; i < backendStage; i++) markStageCompleted(i);
                    if (backendStage < REVIEW_STAGES.length) markStageRunning(backendStage);
                    lastReportedStage = backendStage;
                }

                if (status === 'completed') {
                    stopPolling();
                    for (let i = lastReportedStage + 1; i < REVIEW_STAGES.length; i++) markStageCompleted(i);
                    stageCurrent.textContent = REVIEW_STAGES.length;
                    progressBar.style.width = '100%';
                    
                    if (progress.result && progress.result.success) {
                        currentReviewData = progress.result;
                        showSuccess(progress.result);
                    } else {
                        failCurrentStage('Review failed: Invalid result received.');
                    }
                } else if (status === 'failed') {
                    stopPolling();
                    failCurrentStage('Review failed: ' + (progress.error || 'Unknown error'));
                }
            } catch (error) {
                console.debug('Polling error:', error);
            }
        }, 1500);
    }

    function stopPolling() { if (pollInterval) { clearInterval(pollInterval); pollInterval = null; } }

    function showSuccess(data) {
        stopTimer(); stopPolling();
        reviewProgress.classList.add('hidden');
        aiSuccessState.classList.remove('hidden');
        resetBtn.disabled = false;
        displayProfessionalReport(data);
        reviewResults.classList.remove('hidden');
        setTimeout(() => { reviewResults.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 100);
    }

    function showError(reason) {
        stopTimer(); stopPolling();
        reviewProgress.classList.add('hidden');
        aiErrorState.classList.remove('hidden');
        if (reason && errorMessage) errorMessage.textContent = reason;
        resetBtn.disabled = false; browseBtn.disabled = false;
        dropZone.style.pointerEvents = 'auto'; dropZone.style.opacity = '1';
    }

    function resetUI() {
        stopTimer(); stopPolling();
        selectedFile = null; currentReviewData = null;
        fileInput.value = ''; fileInput.files = null;
        fileInfo.classList.add('hidden'); actionButtons.classList.add('hidden');
        dropZone.classList.remove('hidden'); dropZone.style.pointerEvents = 'auto'; dropZone.style.opacity = '1';
        analyzeBtn.disabled = false; browseBtn.disabled = false; resetBtn.disabled = false;
        reviewProgress.classList.add('hidden');
        aiSuccessState.classList.add('hidden'); aiErrorState.classList.add('hidden');
        reviewResults.classList.add('hidden');
        resetStatus();
    }

    function showStatus(message, type) { uploadStatus.textContent = message; uploadStatus.className = 'upload-status ' + type; uploadStatus.classList.remove('hidden'); }
    function resetStatus() { uploadStatus.textContent = ''; uploadStatus.className = 'upload-status hidden'; }
    function formatBytes(bytes) { if (bytes === 0) return '0 Bytes'; const k = 1024; const sizes = ['Bytes', 'KB', 'MB', 'GB']; const i = Math.floor(Math.log(bytes) / Math.log(k)); return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]; }

    function handleDownloadReview() {
        if (!currentReviewData) return;
        const dataStr = JSON.stringify(currentReviewData, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'review_' + currentReviewData.filename + '_' + Date.now() + '.json';
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // ==========================================
    // 6. ACCORDION PROFESSIONAL REPORT LOGIC
    // ==========================================
    function displayProfessionalReport(data) {
        const review = data.review;
        const score = review.overall_score || 0;

        if (reportFilename) reportFilename.textContent = data.filename;
        if (reportLanguage) reportLanguage.textContent = data.language;
        if (reportDuration) {
            const mins = Math.floor(elapsedSeconds / 60);
            const secs = elapsedSeconds % 60;
            reportDuration.textContent = mins + 'm ' + secs + 's';
        }

        if (reportScore) reportScore.textContent = score;
        if (scoreCard) {
            scoreCard.className = 'score-card';
            if (score >= 90) scoreCard.classList.add('score-high');
            else if (score >= 70) scoreCard.classList.add('score-medium');
            else scoreCard.classList.add('score-low');
        }
        if (scoreRating) {
            if (score >= 90) scoreRating.textContent = 'Excellent';
            else if (score >= 70) scoreRating.textContent = 'Good';
            else if (score >= 50) scoreRating.textContent = 'Needs Improvement';
            else scoreRating.textContent = 'Poor';
        }

        if (reportSummaryText) reportSummaryText.textContent = review.summary || 'No summary provided.';

        if (reportRecommendation) {
            if (score >= 90) reportRecommendation.textContent = 'Ready for Production';
            else if (score >= 70) reportRecommendation.textContent = 'Needs Minor Improvements';
            else if (score >= 50) reportRecommendation.textContent = 'Requires Refactoring';
            else reportRecommendation.textContent = 'Not Recommended';
        }
        if (reportConclusionText) reportConclusionText.textContent = review.conclusion || 'No conclusion provided.';

        const categoryMap = {
            bugs: review.bugs || [], security: review.security || [], performance: review.performance || [],
            architecture: review.architecture || [], readability: review.readability || [], best_practices: review.best_practices || [],
            refactoring: review.refactoring || [], documentation: review.documentation || []
        };
        const totalIssues = Object.values(categoryMap).reduce((sum, arr) => sum + arr.length, 0);

        if (statsGrid) {
            statsGrid.innerHTML =
                '<div class="stat-card stat-critical"><div class="stat-value">' + categoryMap.bugs.length + '</div><div class="stat-label">\uD83D\uDC1B Bugs</div></div>' +
                '<div class="stat-card stat-high"><div class="stat-value">' + categoryMap.security.length + '</div><div class="stat-label">\uD83D\uDD12 Security</div></div>' +
                '<div class="stat-card stat-medium"><div class="stat-value">' + categoryMap.performance.length + '</div><div class="stat-label">\u26A1 Performance</div></div>' +
                '<div class="stat-card stat-low"><div class="stat-value">' + categoryMap.architecture.length + '</div><div class="stat-label">\uD83C\uDFD7\uFE0F Architecture</div></div>' +
                '<div class="stat-card"><div class="stat-value">' + categoryMap.readability.length + '</div><div class="stat-label">\uD83D\uDCD6 Readability</div></div>' +
                '<div class="stat-card"><div class="stat-value">' + categoryMap.best_practices.length + '</div><div class="stat-label">\u2705 Best Practices</div></div>' +
                '<div class="stat-card"><div class="stat-value">' + categoryMap.refactoring.length + '</div><div class="stat-label">\uD83D\uDD27 Refactoring</div></div>' +
                '<div class="stat-card"><div class="stat-value">' + totalIssues + '</div><div class="stat-label">\uD83D\uDCCA Total</div></div>';
        }

        populateAccordion('bugs', categoryMap.bugs, 'Bug');
        populateAccordion('security', categoryMap.security, 'Security Vulnerability');
        populateAccordion('performance', categoryMap.performance, 'Performance Issue');
        populateAccordion('architecture', categoryMap.architecture, 'Architecture Concern');
        populateAccordion('readability', categoryMap.readability, 'Readability Issue');
        populateAccordion('best-practices', categoryMap.best_practices, 'Best Practice');
        populateAccordion('refactoring', categoryMap.refactoring, 'Refactoring Suggestion');
        populateAccordion('documentation', categoryMap.documentation, 'Documentation Issue');
        populateAccordion('positive', review.positive_points || [], 'Positive Point', true);

        updateAccordionCount('bugs', categoryMap.bugs.length);
        updateAccordionCount('security', categoryMap.security.length);
        updateAccordionCount('performance', categoryMap.performance.length);
        updateAccordionCount('architecture', categoryMap.architecture.length);
        updateAccordionCount('readability', categoryMap.readability.length);
        updateAccordionCount('best-practices', categoryMap.best_practices.length);
        updateAccordionCount('refactoring', categoryMap.refactoring.length);
        updateAccordionCount('documentation', categoryMap.documentation.length);
        updateAccordionCount('positive', (review.positive_points || []).length);

        document.querySelectorAll('.accordion-item').forEach(item => {
            item.classList.remove('open');
            const content = item.querySelector('.accordion-content');
            if (content) content.classList.add('hidden');
        });
    }

    function updateAccordionCount(categoryId, count) {
        const countEl = document.getElementById('count-' + categoryId);
        if (countEl) countEl.textContent = count;
    }

    function populateAccordion(categoryId, items, categoryLabel, isPositive) {
        const container = document.getElementById('report-' + categoryId);
        if (!container) return;
        container.innerHTML = '';

        if (!items || items.length === 0) {
            container.innerHTML = '<div class="finding-card"><div class="finding-body" style="color: var(--text-muted); font-style: italic;">No findings in this category.</div></div>';
            return;
        }

        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'finding-card';
            let severity = 'medium';
            let severityText = 'Medium';
            const lowerText = item.toLowerCase();

            if (isPositive) { severity = 'low'; severityText = 'Strength'; } 
            else if (lowerText.indexOf('critical') !== -1 || lowerText.indexOf('crash') !== -1 || lowerText.indexOf('severe') !== -1) { severity = 'critical'; severityText = 'Critical'; } 
            else if (lowerText.indexOf('high') !== -1 || lowerText.indexOf('major') !== -1 || lowerText.indexOf('vulnerability') !== -1) { severity = 'high'; severityText = 'High'; } 
            else if (lowerText.indexOf('low') !== -1 || lowerText.indexOf('minor') !== -1 || lowerText.indexOf('suggestion') !== -1) { severity = 'low'; severityText = 'Low'; }

            card.innerHTML =
                '<div class="finding-header">' +
                    '<h4 class="finding-title">' + categoryLabel + '</h4>' +
                    '<span class="severity-badge severity-' + severity + '">' + severityText + '</span>' +
                '</div>' +
                '<div class="finding-body">' + escapeHtml(item) + '</div>';
            container.appendChild(card);
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
});