/**
 * AI Code Reviewer - Client-Side Application Logic
 * Handles Ollama status, file upload, AI thinking animation, review rendering, and export functionality.
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
                ollamaModelsList.textContent = data.available_models.length > 0 
                    ? data.available_models.join(', ') 
                    : 'None installed';
            } else {
                throw new Error('Ollama not connected');
            }
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

    // Upload & Review Elements
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
    
    const aiThinkingState = document.getElementById('ai-thinking-state');
    const thinkingTitle = document.getElementById('thinking-title');
    const thinkingSubtitle = document.getElementById('thinking-subtitle');
    const thinkingTimerValue = document.getElementById('thinking-timer-value');
    
    const aiSuccessState = document.getElementById('ai-success-state');
    const aiErrorState = document.getElementById('ai-error-state');
    const retryBtn = document.getElementById('retry-btn');
    
    const reviewResults = document.getElementById('review-results');
    const reviewFilename = document.getElementById('review-filename');
    const reviewLanguage = document.getElementById('review-language');
    const reviewScore = document.getElementById('review-score');
    const reviewSummaryText = document.getElementById('review-summary-text');
    const reviewConclusionText = document.getElementById('review-conclusion-text');
    
    // Export Elements
    const reviewActions = document.getElementById('review-actions');
    const downloadReviewBtn = document.getElementById('download-review-btn');

    // Local State
    let selectedFile = null;
    let currentReviewData = null;
    let timerInterval = null;
    let thinkingInterval = null;
    let progressInterval = null;
    let elapsedSeconds = 0;

    const ALLOWED_EXTENSIONS = new Set([
        '.py', '.java', '.js', '.ts', '.cpp', '.c', 
        '.cs', '.go', '.rs', '.php', '.kt', '.swift', '.txt'
    ]);
    const MAX_FILE_SIZE = 10 * 1024 * 1024;

    const THINKING_MESSAGES = [
        "Initializing AI Review...", "Reading uploaded source code...", "Detecting programming language...",
        "Parsing file structure...", "Understanding code organization...", "Building review context...",
        "Identifying important components...", "Understanding application flow...", "Analyzing business logic...",
        "Looking for potential bugs...", "Checking null safety...", "Checking edge cases...",
        "Inspecting security vulnerabilities...", "Reviewing authentication patterns...", "Checking input validation...",
        "Evaluating performance...", "Reviewing architecture...", "Inspecting maintainability...",
        "Reviewing naming conventions...", "Checking coding standards...", "Finding code smells...",
        "Looking for duplicate logic...", "Evaluating best practices...", "Searching for refactoring opportunities...",
        "Comparing implementation patterns...", "Preparing recommendations...", "Generating structured review...",
        "Finalizing AI response..."
    ];

    const PROGRESS_MESSAGES = [
        "Preparing prompt...", "Sending request to Ollama...", "Waiting for AI response...",
        "Receiving response...", "Parsing AI output...", "Building report...", "Finalizing review..."
    ];

    // ==========================================
    // 3. EVENT LISTENERS
    // ==========================================

    // Upload Events
    browseBtn.addEventListener('click', (e) => { e.preventDefault(); fileInput.click(); });
    fileInput.addEventListener('change', (e) => { if (e.target.files?.length) handleFile(e.target.files[0]); });
    resetBtn.addEventListener('click', resetUI);
    analyzeBtn.addEventListener('click', startAnalysis);
    retryBtn.addEventListener('click', startAnalysis);
    downloadReviewBtn.addEventListener('click', handleDownloadReview);

    // Drag & Drop
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); if (dropZone.style.pointerEvents !== 'none') dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault(); dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files?.length) { handleFile(e.dataTransfer.files[0]); fileInput.files = e.dataTransfer.files; }
    });

    // ==========================================
    // 4. CORE LOGIC FUNCTIONS
    // ==========================================

    function handleFile(file) {
        resetStatus();
        selectedFile = file;
        const extension = '.' + file.name.split('.').pop().toLowerCase();

        if (!ALLOWED_EXTENSIONS.has(extension)) { showStatus(`Unsupported file type: ${extension}`, 'error'); return; }
        if (file.size > MAX_FILE_SIZE) { showStatus('File exceeds the 10 MB size limit.', 'error'); return; }

        aiSuccessState.classList.add('hidden');
        aiErrorState.classList.add('hidden');
        reviewResults.classList.add('hidden');
        reviewActions.classList.add('hidden');

        fileNameDisplay.textContent = file.name;
        fileMetaDisplay.textContent = `${formatBytes(file.size)} • ${extension}`;

        fileInfo.classList.remove('hidden');
        actionButtons.classList.remove('hidden');
        dropZone.classList.add('hidden');
    }

    function startAnalysis() {
        if (!selectedFile) return;
        setAnalyzingState();
        startTimer();
        startMessageRotation();

        const formData = new FormData();
        formData.append('file', selectedFile);

        fetch('/review', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentReviewData = data;
                showSuccess(data);
            } else {
                showError();
            }
        })
        .catch(error => { console.error('Review error:', error); showError(); });
    }

    function setAnalyzingState() {
        analyzeBtn.disabled = true; browseBtn.disabled = true; resetBtn.disabled = true;
        dropZone.style.pointerEvents = 'none'; dropZone.style.opacity = '0.6';
        actionButtons.classList.add('hidden');
        aiThinkingState.classList.remove('hidden');
        aiSuccessState.classList.add('hidden'); aiErrorState.classList.add('hidden');
        reviewResults.classList.add('hidden'); reviewActions.classList.add('hidden');
    }

    function startTimer() {
        elapsedSeconds = 0; thinkingTimerValue.textContent = '00:00';
        timerInterval = setInterval(() => {
            elapsedSeconds++;
            const mins = String(Math.floor(elapsedSeconds / 60)).padStart(2, '0');
            const secs = String(elapsedSeconds % 60).padStart(2, '0');
            thinkingTimerValue.textContent = `${mins}:${secs}`;
        }, 1000);
    }

    function stopTimer() { if (timerInterval) clearInterval(timerInterval); timerInterval = null; }

    function startMessageRotation() {
        let msgIndex = 0; let progressIndex = 0;
        thinkingTitle.textContent = THINKING_MESSAGES[0];
        thinkingSubtitle.textContent = PROGRESS_MESSAGES[0];

        thinkingInterval = setInterval(() => { msgIndex = (msgIndex + 1) % THINKING_MESSAGES.length; thinkingTitle.textContent = THINKING_MESSAGES[msgIndex]; }, 2500);
        progressInterval = setInterval(() => { progressIndex = (progressIndex + 1) % PROGRESS_MESSAGES.length; thinkingSubtitle.textContent = PROGRESS_MESSAGES[progressIndex]; }, 4000);
    }

    function stopMessageRotation() {
        if (thinkingInterval) clearInterval(thinkingInterval);
        if (progressInterval) clearInterval(progressInterval);
        thinkingInterval = null; progressInterval = null;
    }

    function showSuccess(data) {
        stopTimer(); stopMessageRotation();
        aiThinkingState.classList.add('hidden');
        aiSuccessState.classList.remove('hidden');
        resetBtn.disabled = false;
        
        displayReviewResults(data);
        reviewResults.classList.remove('hidden');
        reviewActions.classList.remove('hidden');
        
        setTimeout(() => reviewResults.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }

    function showError() {
        stopTimer(); stopMessageRotation();
        aiThinkingState.classList.add('hidden');
        aiErrorState.classList.remove('hidden');
        resetBtn.disabled = false; browseBtn.disabled = false;
        dropZone.style.pointerEvents = 'auto'; dropZone.style.opacity = '1';
    }

    function resetUI() {
        stopTimer(); stopMessageRotation();
        selectedFile = null; currentReviewData = null;
        fileInput.value = ''; fileInput.files = null;
        
        fileInfo.classList.add('hidden'); actionButtons.classList.add('hidden');
        dropZone.classList.remove('hidden'); dropZone.style.pointerEvents = 'auto'; dropZone.style.opacity = '1';
        
        analyzeBtn.disabled = false; browseBtn.disabled = false; resetBtn.disabled = false;
        
        aiThinkingState.classList.add('hidden'); aiSuccessState.classList.add('hidden'); aiErrorState.classList.add('hidden');
        reviewResults.classList.add('hidden'); reviewActions.classList.add('hidden');
        
        resetStatus();
    }

    function displayReviewResults(data) {
        reviewFilename.textContent = data.filename;
        reviewLanguage.textContent = data.language;
        reviewScore.textContent = data.review.overall_score;
        reviewSummaryText.textContent = data.review.summary;
        reviewConclusionText.textContent = data.review.conclusion;

        populateList('review-bugs', data.review.bugs);
        populateList('review-security', data.review.security);
        populateList('review-performance', data.review.performance);
        populateList('review-readability', data.review.readability);
        populateList('review-architecture', data.review.architecture);
        populateList('review-best-practices', data.review.best_practices);
        populateList('review-refactoring', data.review.refactoring);
        populateList('review-documentation', data.review.documentation);
        populateList('review-positive', data.review.positive_points);
    }

    function populateList(elementId, items) {
        const list = document.getElementById(elementId);
        list.innerHTML = '';
        if (!items || items.length === 0) {
            const li = document.createElement('li');
            li.textContent = "No issues found in this category.";
            li.style.color = "var(--text-muted)"; li.style.fontStyle = "italic";
            list.appendChild(li); return;
        }
        items.forEach(item => { const li = document.createElement('li'); li.textContent = item; list.appendChild(li); });
    }

    function showStatus(message, type) {
        uploadStatus.textContent = message;
        uploadStatus.className = `upload-status ${type}`;
        uploadStatus.classList.remove('hidden');
    }

    function resetStatus() { uploadStatus.textContent = ''; uploadStatus.className = 'upload-status hidden'; }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024; const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // ==========================================
    // 5. EXPORT LOGIC
    // ==========================================

    function handleDownloadReview() {
        if (!currentReviewData) return;
        
        const dataStr = JSON.stringify(currentReviewData, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `review_${currentReviewData.filename}_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
});