/**
 * FitQuest Workout Flow Engine & Multi-View Router
 * Manages Exercise Selection, Setup, Live Webcam + YOLO Pose Telemetry HUD, Results & History.
 */

// Global State
let allExercises = [];
let selectedExercise = null;
let workoutTimerInterval = null;
let workoutStartTime = null;
let workoutElapsedSeconds = 0;

// Live CV & Camera State
let webcamStream = null;
let frameCaptureInterval = null;
let workoutSocket = null;
let activeSessionId = null;
let currentRepCount = 0;
let currentFormScore = 100.0;
let accumulatedFeedback = [];

// API Endpoints
var API_BASE = window.API_BASE || 'http://127.0.0.1:8000/api/v1';

document.addEventListener('DOMContentLoaded', () => {
  initTabNavigation();
  initSearchFilter();
  initWorkoutModeTabs();
  loadExerciseCatalogue();
});

/**
 * Initializes Workout Mode Tab Buttons (Quick vs Structured)
 */
function initWorkoutModeTabs() {
  const quickBtn = document.getElementById('modeQuickBtn');
  const structBtn = document.getElementById('modeStructuredBtn');

  if (quickBtn) {
    quickBtn.addEventListener('click', () => switchWorkoutMode('quick'));
  }
  if (structBtn) {
    structBtn.addEventListener('click', () => switchWorkoutMode('structured'));
  }
}

/**
 * Initializes Top Navigation Bar tab switching
 */
function initTabNavigation() {
  const navTabs = document.querySelectorAll('.nav-tab');
  navTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const viewId = tab.getAttribute('data-view');
      switchTab(viewId);
    });
  });
}

/**
 * Switches active view panel
 */
function switchTab(viewId) {
  const navTabs = document.querySelectorAll('.nav-tab');
  const viewPanels = document.querySelectorAll('.view-panel');

  navTabs.forEach((tab) => {
    if (tab.getAttribute('data-view') === viewId) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  viewPanels.forEach((panel) => {
    if (panel.id === viewId) {
      panel.classList.add('active');
    } else {
      panel.classList.remove('active');
    }
  });

  if (viewId === 'workoutView' && allExercises.length === 0) {
    loadExerciseCatalogue();
  } else if (viewId === 'historyView') {
    loadWorkoutHistory();
  }
}

/**
 * Switches sub-step views inside Workout Experience
 */
function goToStep(stepId) {
  const workoutSteps = document.querySelectorAll('.workout-step');
  workoutSteps.forEach((step) => {
    if (step.id === stepId) {
      step.classList.add('active');
    } else {
      step.classList.remove('active');
    }
  });
}

/**
 * Fetches all 20 seeded exercises from backend API GET /api/v1/exercises
 */
async function loadExerciseCatalogue() {
  const grid = document.getElementById('exerciseGrid');
  if (!grid) return;

  try {
    const response = await fetch(`${API_BASE}/exercises`);
    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }

    allExercises = await response.json();
    renderExerciseGrid(allExercises);
  } catch (error) {
    console.error('[FitQuest Error]: Failed to fetch exercises from backend:', error);
    grid.innerHTML = `
      <div class="loading-spinner" style="color: #ef4444;">
        <i class="fa-solid fa-triangle-exclamation"></i> Could not connect to backend server. Make sure FastAPI server is running on http://127.0.0.1:8000.
      </div>
    `;
  }
}

/**
 * Renders exercise cards into selection grid
 */
function renderExerciseGrid(exercises) {
  const grid = document.getElementById('exerciseGrid');
  if (!grid) return;

  if (exercises.length === 0) {
    grid.innerHTML = `<div class="loading-spinner">No matching exercises found.</div>`;
    return;
  }

  grid.innerHTML = exercises.map((ex) => `
    <div class="exercise-card">
      <div>
        <div class="ex-card-header">
          <div class="ex-icon-badge">
            <i class="fa-solid ${getExerciseIcon(ex.name)}"></i>
          </div>
          <span class="ex-difficulty-badge">${ex.difficulty || 'Intermediate'}</span>
        </div>
        <h3 class="ex-title">${escapeHTML(ex.name)}</h3>
        <p class="ex-desc">${escapeHTML(ex.description || 'YOLO Pose Tracker')}</p>
      </div>
      <button class="btn btn-primary" onclick="selectExercise(${ex.id})">
        <i class="fa-solid fa-play"></i> Select Exercise
      </button>
    </div>
  `).join('');
}

/**
 * Exercise search filter
 */
function initSearchFilter() {
  const input = document.getElementById('exerciseSearch');
  if (!input) return;

  input.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    const filtered = allExercises.filter((ex) => 
      ex.name.toLowerCase().includes(query) || 
      (ex.description && ex.description.toLowerCase().includes(query))
    );
    renderExerciseGrid(filtered);
  });
}

/**
 * Selects an exercise and transitions to Setup Screen
 */
function selectExercise(exerciseId) {
  selectedExercise = allExercises.find((ex) => ex.id === exerciseId);
  if (!selectedExercise) return;

  // Reset all state for new exercise selection
  activeSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  currentRepCount = 0;
  currentFormScore = 0.0;
  accumulatedFeedback = [];
  workoutElapsedSeconds = 0;

  document.getElementById('setupExerciseName').innerText = selectedExercise.name;
  document.getElementById('setupExerciseDesc').innerText = selectedExercise.description || 'YOLO Pose Repetition Tracker & Form Evaluator';
  document.getElementById('setupDifficulty').innerText = selectedExercise.difficulty || 'Intermediate';
  document.getElementById('setupMuscleGroup').innerText = getExerciseMuscleGroup(selectedExercise.name);

  // Clear previous AI coaching DOM text
  const aiCoachEl = document.getElementById('resAICoaching');
  if (aiCoachEl) {
    aiCoachEl.innerHTML = 'Loading personalized AI coaching analysis...';
  }

  goToStep('workoutSetupStep');
}

/**
 * Starts an active workout session (Step C)
 */
async function startWorkoutSession() {
  if (!selectedExercise) return;

  activeSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  currentRepCount = 0;
  currentFormScore = 0.0;
  accumulatedFeedback = [];

  document.getElementById('activeExerciseTitle').innerText = selectedExercise.name;
  document.getElementById('hudRepCount').innerText = '0';
  document.getElementById('hudFormScore').innerText = 'N/A';
  document.getElementById('hudDuration').innerText = '00:00';
  document.getElementById('hudFeedback').innerText = 'Starting camera & connecting YOLO Pose Engine...';

  // Clear result screen DOM elements
  document.getElementById('resRepCount').innerText = '--';
  document.getElementById('resDuration').innerText = '00:00';
  document.getElementById('resFormScore').innerText = 'N/A';
  document.getElementById('resAICoaching').innerHTML = 'Loading personalized AI coaching analysis...';

  // Call start-session backend API to guarantee clean controller initialization
  try {
    await fetch(`${API_BASE}/workouts/live/start-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: activeSessionId,
        exercise_choice: String(selectedExercise.id)
      })
    });
  } catch (e) {
    console.warn('[FitQuest Warning]: Live session start endpoint call failed:', e);
  }

  // Reset duration timer
  workoutElapsedSeconds = 0;
  workoutStartTime = Date.now();
  if (workoutTimerInterval) clearInterval(workoutTimerInterval);

  workoutTimerInterval = setInterval(() => {
    workoutElapsedSeconds = Math.floor((Date.now() - workoutStartTime) / 1000);
    document.getElementById('hudDuration').innerText = formatDuration(workoutElapsedSeconds);
  }, 1000);

  goToStep('workoutActiveStep');

  // Start webcam and CV live telemetry stream
  await startCameraStream();
}

/**
 * Initializes browser webcam feed and live CV telemetry stream
 */
async function startCameraStream() {
  const video = document.getElementById('webcamFeed');
  const overlay = document.getElementById('overlayImage');
  const placeholder = document.getElementById('cameraPlaceholder');
  const notice = document.getElementById('cameraNoticeText');

  try {
    // Request webcam permission
    webcamStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
      audio: false
    });

    video.srcObject = webcamStream;
    video.style.display = 'block';
    if (overlay) overlay.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';

    document.getElementById('hudFeedback').innerText = 'Webcam active. Position yourself in view.';

    // Start frame streaming to backend
    startFrameTransmission();

  } catch (err) {
    console.warn('[FitQuest Camera Warning]: Webcam access denied or unavailable:', err);
    if (placeholder) placeholder.style.display = 'block';
    if (video) video.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
    if (notice) {
      notice.innerHTML = `
        <span style="color: #ef4444;">
          <i class="fa-solid fa-triangle-exclamation"></i> Camera Access Denied / Unavailable.
        </span><br>
        Please allow webcam permissions in your browser. (Telemetry simulation mode active).
      `;
    }
  }
}

/**
 * Transmits video frames to backend CV Engine via HTTP / WebSocket
 */
function startFrameTransmission() {
  const video = document.getElementById('webcamFeed');
  const canvas = document.getElementById('frameCanvas');
  const overlay = document.getElementById('overlayImage');
  const ctx = canvas ? canvas.getContext('2d') : null;

  if (frameCaptureInterval) clearInterval(frameCaptureInterval);

  // Send frame every 120ms (~8-10 FPS)
  frameCaptureInterval = setInterval(async () => {
    if (!video || video.paused || video.ended || !video.videoWidth) return;

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const base64Frame = canvas.toDataURL('image/jpeg', 0.6);

    try {
      const payload = {
        session_id: activeSessionId,
        exercise_choice: String(selectedExercise.id),
        frame_data: base64Frame,
        include_annotated_image: true
      };

      const res = await fetch(`${API_BASE}/workouts/live/process-frame`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) return;

      const telemetry = await res.json();
      updateHUDTelemetry(telemetry, overlay);

    } catch (err) {
      console.error('[FitQuest Frame Processing Error]:', err);
    }
  }, 120);
}

/**
 * Updates Live Workout HUD with authoritative CV Engine telemetry
 */
// Feedback Stabilization State (prevents rapid per-frame UI flicker)
let activeFeedbackCode = 'GOOD_FORM';
let activeFeedbackDetail = 'Get ready... Position yourself in front of camera.';
let activeFeedbackPriority = 7;
let lastFeedbackUpdateTime = 0;
const FEEDBACK_HOLD_MS = 450; // Hold active feedback for 450ms unless higher priority error arrives

function updateHUDTelemetry(telemetry, overlayElement) {
  if (!telemetry || telemetry.status === 'error') return;

  if (telemetry.rep_count !== undefined) {
    currentRepCount = telemetry.rep_count;
    document.getElementById('hudRepCount').innerText = currentRepCount;
  }

  if (telemetry.form_score !== undefined) {
    currentFormScore = telemetry.form_score;
    if (currentRepCount === 0 || currentFormScore === 0.0) {
      document.getElementById('hudFormScore').innerText = 'N/A';
    } else {
      document.getElementById('hudFormScore').innerText = `${currentFormScore.toFixed(1)}%`;
    }
  }

  // Stabilize feedback cues across frames
  const now = Date.now();
  const newCode = telemetry.feedback_code || 'GOOD_FORM';
  const newDetail = telemetry.feedback_detail || (telemetry.feedback && telemetry.feedback.length > 0 ? telemetry.feedback[0] : 'Good Form');
  const newPriority = telemetry.feedback_priority !== undefined ? telemetry.feedback_priority : 7;

  // Immediate override if higher priority (lower numeric priority) OR hold window elapsed
  if (newPriority < activeFeedbackPriority || (now - lastFeedbackUpdateTime) >= FEEDBACK_HOLD_MS) {
    activeFeedbackCode = newCode;
    activeFeedbackDetail = newDetail;
    activeFeedbackPriority = newPriority;
    lastFeedbackUpdateTime = now;
  }

  const feedbackContainer = document.getElementById('hudFeedback');
  if (feedbackContainer) {
    if (!telemetry.valid || activeFeedbackCode === 'LANDMARKS_MISSING') {
      feedbackContainer.innerHTML = `
        <div class="feedback-badge badge-error">
          <i class="fa-solid fa-eye-slash"></i> <span>BODY NOT DETECTED</span>
        </div>
        <div class="feedback-text-detail">${escapeHTML(activeFeedbackDetail)}</div>
      `;
    } else if (activeFeedbackCode === 'GOOD_FORM') {
      feedbackContainer.innerHTML = `
        <div class="feedback-badge badge-good">
          <i class="fa-solid fa-circle-check"></i> <span>✓ GOOD FORM</span>
        </div>
        <div class="feedback-text-detail">${escapeHTML(activeFeedbackDetail)}</div>
      `;
    } else {
      feedbackContainer.innerHTML = `
        <div class="feedback-badge badge-warning">
          <i class="fa-solid fa-triangle-exclamation"></i> <span>⚠ FORM ISSUE: ${escapeHTML(activeFeedbackCode.replace(/_/g, ' '))}</span>
        </div>
        <div class="feedback-text-detail">${escapeHTML(activeFeedbackDetail)}</div>
      `;
    }
  }

  if (telemetry.feedback && telemetry.feedback.length > 0) {
    const feedbackStr = telemetry.feedback.join(' | ');
    if (!accumulatedFeedback.includes(feedbackStr)) {
      accumulatedFeedback.push(feedbackStr);
    }
  }

  if (telemetry.annotated_frame && overlayElement) {
    overlayElement.src = telemetry.annotated_frame;
  }
}


/**
 * Stops camera stream cleanly
 */
function stopCameraStream() {
  if (frameCaptureInterval) {
    clearInterval(frameCaptureInterval);
    frameCaptureInterval = null;
  }

  if (webcamStream) {
    webcamStream.getTracks().forEach((track) => track.stop());
    webcamStream = null;
  }

  const video = document.getElementById('webcamFeed');
  const overlay = document.getElementById('overlayImage');
  const placeholder = document.getElementById('cameraPlaceholder');

  if (video) video.style.display = 'none';
  if (overlay) overlay.style.display = 'none';
  if (placeholder) placeholder.style.display = 'block';
}

/**
 * Ends active workout session, stops camera, and posts session to backend
 */
async function endWorkoutSession() {
  if (workoutTimerInterval) clearInterval(workoutTimerInterval);

  // Stop camera & frame capture
  stopCameraStream();

  // Call stop-session backend API to retrieve final CV summary
  try {
    const stopRes = await fetch(`${API_BASE}/workouts/live/stop-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: activeSessionId })
    });
    if (stopRes.ok) {
      const stopSummary = await stopRes.json();
      if (stopSummary && stopSummary.status === 'success') {
        currentRepCount = stopSummary.total_reps;
        currentFormScore = stopSummary.total_reps === 0 ? 0.0 : stopSummary.form_score;
        if (stopSummary.duration_sec !== undefined) {
          workoutElapsedSeconds = stopSummary.duration_sec;
        }
      }
    }
  } catch (e) {
    console.warn('[FitQuest Warning]: Live session stop endpoint call failed:', e);
  }

  // Transition to results step
  goToStep('workoutResultStep');
  const isInitialZero = (currentRepCount === 0);
  document.getElementById('resRepCount').innerText = currentRepCount;
  document.getElementById('resDuration').innerText = formatDuration(workoutElapsedSeconds);
  document.getElementById('resFormScore').innerText = isInitialZero ? 'N/A (No Reps)' : `${currentFormScore.toFixed(1)}%`;
  
  const zeroRepMessage = "No valid repetitions were detected in this session, so there isn't enough workout data to generate performance insights. Complete an exercise and try again.";

  if (isInitialZero) {
    document.getElementById('resAICoaching').innerHTML = formatMarkdownText(zeroRepMessage);
  } else {
    document.getElementById('resAICoaching').innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Generating personalized AI coaching feedback...`;
  }

  try {
    const userId = typeof getAuthenticatedUserId === 'function' ? getAuthenticatedUserId() : 1;
    const exerciseId = (selectedExercise && selectedExercise.id) ? selectedExercise.id : 1;
    const exerciseName = (selectedExercise && selectedExercise.name) ? selectedExercise.name : 'Exercise';

    // Post completed workout telemetry payload to POST /api/v1/workouts
    const payload = {
      session_data: {
        user_id: userId,
        exercise_id: exerciseId,
        repetitions: currentRepCount,
        duration_sec: workoutElapsedSeconds,
        form_score: currentRepCount === 0 ? 0.0 : currentFormScore
      },
      form_scores_history: currentRepCount > 0 ? Array(currentRepCount).fill(1) : [],
      feedback_events: accumulatedFeedback.length > 0 ? accumulatedFeedback : (currentRepCount === 0 ? ["No valid repetitions detected"] : [`Completed set for ${exerciseName}`])
    };

    const response = await fetch(`${API_BASE}/workouts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Server status ${response.status}`);
    }

    const resultData = await response.json();

    const isFinalZero = (resultData.repetitions === 0 || currentRepCount === 0);

    // Render returned results & AI coaching insights
    document.getElementById('resRepCount').innerText = resultData.repetitions;
    document.getElementById('resDuration').innerText = formatDuration(resultData.duration_sec);
    document.getElementById('resFormScore').innerText = isFinalZero ? 'N/A (No Reps)' : `${resultData.form_score}%`;

    const aiText = isFinalZero
      ? zeroRepMessage
      : (resultData.ai_coaching_logs && resultData.ai_coaching_logs.length > 0 
          ? resultData.ai_coaching_logs[0].response 
          : "Great workout set!");

    document.getElementById('resAICoaching').innerHTML = formatMarkdownText(aiText);

    // Refresh gamification streaks & achievements for valid workouts (reps >= 1)
    if (currentRepCount >= 1 && typeof loadGamificationData === 'function') {
      loadGamificationData();
      if (typeof showGamificationNotification === 'function') {
        showGamificationNotification('🔥 Workout Saved!', 'Your workout set was recorded towards your streak!', 'fa-fire');
      }
    }

  } catch (error) {
    console.error('[FitQuest Error]: Failed to record session to backend:', error);
    if (currentRepCount === 0) {
      document.getElementById('resAICoaching').innerHTML = formatMarkdownText(zeroRepMessage);
    } else {
      document.getElementById('resAICoaching').innerHTML = `
        <div style="color: #ef4444;">
          <i class="fa-solid fa-triangle-exclamation"></i> Session recorded locally. (Backend server error).
        </div>
      `;
    }
  }
}

/**
 * Fetches and renders historical workouts from GET /api/v1/workouts/user/{userId}
 */
async function loadWorkoutHistory() {
  const container = document.getElementById('historyList');
  if (!container) return;

  try {
    const userId = typeof getAuthenticatedUserId === 'function' ? getAuthenticatedUserId() : 1;
    const response = await fetch(`${API_BASE}/workouts/user/${userId}`);

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }

    const historyData = await response.json();

    if (historyData.length === 0) {
      container.innerHTML = `<div class="loading-spinner">No workout history recorded yet. Complete a workout session to see your stats here!</div>`;
      return;
    }

    container.innerHTML = historyData.map((item) => `
      <div class="history-card">
        <div class="history-info">
          <h3>${escapeHTML(item.exercise ? item.exercise.name : 'Exercise Session')}</h3>
          <div class="history-meta">
            <i class="fa-solid fa-calendar"></i> ${new Date(item.started_at).toLocaleString()}
          </div>
        </div>
        <div class="history-metrics">
          <span class="metric-pill">${item.repetitions} Reps</span>
          <span class="metric-pill">${formatDuration(item.duration_sec)}</span>
          <span class="metric-pill score">${item.repetitions === 0 ? 'N/A Form' : item.form_score + '% Form'}</span>
        </div>
      </div>
    `).join('');

  } catch (error) {
    console.error('[FitQuest Error]: Failed to fetch history:', error);
    container.innerHTML = `

      <div class="loading-spinner" style="color: #ef4444;">
        <i class="fa-solid fa-triangle-exclamation"></i> Could not fetch history from backend. Ensure FastAPI server is running.
      </div>
    `;
  }
}

/* --- Helpers --- */
function formatDuration(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function getExerciseIcon(name) {
  const n = name.toLowerCase();
  if (n.includes('curl') || n.includes('raise')) return 'fa-dumbbell';
  if (n.includes('squat') || n.includes('lunge')) return 'fa-person-running';
  if (n.includes('push') || n.includes('press') || n.includes('plank')) return 'fa-child-reaching';
  return 'fa-person';
}

function getExerciseMuscleGroup(name) {
  const n = name.toLowerCase();
  if (n.includes('curl') || n.includes('tricep') || n.includes('raise') || n.includes('press')) return 'Upper Body (Arms & Shoulders)';
  if (n.includes('squat') || n.includes('lunge') || n.includes('calf')) return 'Lower Body (Legs & Glutes)';
  if (n.includes('crunch') || n.includes('situp') || n.includes('twist') || n.includes('plank')) return 'Core & Abs';
  return 'Full Body & Cardiovascular';
}

function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
}

function formatMarkdownText(text) {
  if (!text) return '';

  const lines = text.split(/\r?\n/);
  let htmlResult = [];
  let inList = null;

  function closeList() {
    if (inList) {
      htmlResult.push(`</${inList}>`);
      inList = null;
    }
  }

  for (let line of lines) {
    let trimmed = line.trim();

    const h3Match = trimmed.match(/^###\s+(.*)/);
    if (h3Match) {
      closeList();
      let content = processInlineMarkdown(escapeHTML(h3Match[1]));
      htmlResult.push(`<h3>${content}</h3>`);
      continue;
    }

    const h2Match = trimmed.match(/^##\s+(.*)/);
    if (h2Match) {
      closeList();
      let content = processInlineMarkdown(escapeHTML(h2Match[1]));
      htmlResult.push(`<h2>${content}</h2>`);
      continue;
    }

    const h1Match = trimmed.match(/^#\s+(.*)/);
    if (h1Match) {
      closeList();
      let content = processInlineMarkdown(escapeHTML(h1Match[1]));
      htmlResult.push(`<h1>${content}</h1>`);
      continue;
    }

    const bqMatch = trimmed.match(/^>\s+(.*)/);
    if (bqMatch) {
      closeList();
      let content = processInlineMarkdown(escapeHTML(bqMatch[1]));
      htmlResult.push(`<blockquote>${content}</blockquote>`);
      continue;
    }

    const unorderedMatch = trimmed.match(/^[-*]\s+(.*)/);
    if (unorderedMatch) {
      if (inList !== 'ul') {
        closeList();
        htmlResult.push('<ul class="markdown-list">');
        inList = 'ul';
      }
      let content = processInlineMarkdown(escapeHTML(unorderedMatch[1]));
      htmlResult.push(`<li>${content}</li>`);
      continue;
    }

    const orderedMatch = trimmed.match(/^\d+\.\s+(.*)/);
    if (orderedMatch) {
      if (inList !== 'ol') {
        closeList();
        htmlResult.push('<ol class="markdown-list">');
        inList = 'ol';
      }
      let content = processInlineMarkdown(escapeHTML(orderedMatch[1]));
      htmlResult.push(`<li>${content}</li>`);
      continue;
    }

    if (trimmed === '') {
      closeList();
      continue;
    }

    closeList();
    let content = processInlineMarkdown(escapeHTML(trimmed));
    htmlResult.push(`<p>${content}</p>`);
  }

  closeList();
  return htmlResult.join('');
}

function processInlineMarkdown(escapedStr) {
  let res = escapedStr.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  res = res.replace(/\*(.*?)\*/g, '<em>$1</em>');
  return res;
}


/* ==========================================================================
   STRUCTURED WORKOUT SESSIONS — ORCHESTRATION ENGINE
   ========================================================================== */

let activeWorkoutMode = 'quick'; // 'quick' or 'structured'
let structuredPlans = [];
let activeStructuredSession = null;
let restTimerInterval = null;
let restTimeRemaining = 0;

/**
 * Toggles workout selection view mode ('quick' vs 'structured')
 */
function switchWorkoutMode(mode) {
  activeWorkoutMode = mode;
  const quickBtn = document.getElementById('modeQuickBtn');
  const structBtn = document.getElementById('modeStructuredBtn');
  const exGrid = document.getElementById('exerciseGrid');
  const structGrid = document.getElementById('structuredPlanGrid');

  if (!quickBtn || !structBtn || !exGrid || !structGrid) return;

  if (mode === 'quick') {
    quickBtn.classList.add('active-mode');
    structBtn.classList.remove('active-mode');
    quickBtn.style.background = '';
    quickBtn.style.borderColor = '';
    structBtn.style.background = '';
    structBtn.style.borderColor = '';

    exGrid.style.display = 'grid';
    structGrid.style.display = 'none';
  } else {
    structBtn.classList.add('active-mode');
    quickBtn.classList.remove('active-mode');
    structBtn.style.background = '';
    structBtn.style.borderColor = '';
    quickBtn.style.background = '';
    quickBtn.style.borderColor = '';

    exGrid.style.display = 'none';
    structGrid.style.display = 'grid';

    if (structuredPlans.length === 0) {
      loadStructuredPlans();
    }
  }
}

/**
 * Fetches structured workout preset templates from GET /api/v1/structured-workouts/templates
 */
async function loadStructuredPlans() {
  const container = document.getElementById('structuredPlanGrid');
  if (!container) return;

  container.innerHTML = `<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading workout routines...</div>`;

  try {
    const response = await fetch(`${API_BASE}/structured-workouts/templates`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    structuredPlans = await response.json();

    if (!structuredPlans || structuredPlans.length === 0) {
      container.innerHTML = `<div class="loading-spinner">No structured workout plans available.</div>`;
      return;
    }

    container.innerHTML = structuredPlans.map((plan) => `
      <div class="exercise-card" onclick="openStructuredPlanModal(${plan.id})" style="border-top: 2px solid var(--accent-lime); cursor: pointer;">
        <div>
          <div class="ex-card-header">
            <div class="ex-icon-badge">
              <i class="fa-solid fa-layer-group"></i>
            </div>
            <span class="ex-difficulty-badge">${escapeHTML(plan.category)}</span>
          </div>
          <h3 class="ex-title">${escapeHTML(plan.title)}</h3>
          <p class="ex-desc">${escapeHTML(plan.description)}</p>
          <div style="display: flex; gap: 12px; font-size: 0.82rem; color: var(--text-secondary); margin-top: 12px;">
            <span><i class="fa-solid fa-dumbbell"></i> ${plan.exercises ? plan.exercises.length : 0} Exercises</span>
            <span><i class="fa-solid fa-clock"></i> ~${plan.estimated_duration_min} min</span>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="openStructuredPlanModal(${plan.id})" style="margin-top: 14px; width: 100%; text-align: center;">
          Preview Routine <i class="fa-solid fa-arrow-right"></i>
        </button>
      </div>
    `).join('');

  } catch (error) {
    console.error('[FitQuest Error]: Failed to fetch structured plans:', error);
    container.innerHTML = `<div class="loading-spinner" style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> Could not load workout routines.</div>`;
  }
}

/**
 * Opens Structured Routine Preview Modal
 */
function openStructuredPlanModal(planId) {
  const plan = structuredPlans.find(p => p.id === planId);
  if (!plan) return;

  document.getElementById('planModalCategory').innerText = plan.category;
  document.getElementById('planModalTitle').innerText = plan.title;
  document.getElementById('planModalDesc').innerText = plan.description;

  const exList = document.getElementById('planModalExerciseList');
  exList.innerHTML = plan.exercises.map((item, idx) => `
    <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-secondary); border: 1px solid var(--border-color); padding: 12px 16px; border-radius: var(--radius-sm);">
      <div>
        <span style="font-weight: 700; color: var(--text-primary); font-size: 0.92rem;">${idx + 1}. ${escapeHTML(item.exercise_name)}</span>
        <span style="font-size: 0.78rem; color: var(--text-muted); display: block;">Target: ${item.target_sets} sets × ${item.target_reps} reps</span>
      </div>
      <span class="setup-badge">${item.target_sets * item.target_reps} reps</span>
    </div>
  `).join('');

  const startBtn = document.getElementById('startStructuredPlanBtn');
  startBtn.onclick = () => {
    closeStructuredPlanModal();
    startStructuredWorkoutSession(plan);
  };

  document.getElementById('structuredPlanModal').style.display = 'flex';
}

function closeStructuredPlanModal() {
  document.getElementById('structuredPlanModal').style.display = 'none';
}

/**
 * Starts a structured workout routine session
 */
async function startStructuredWorkoutSession(plan) {
  try {
    const userId = typeof getAuthenticatedUserId === 'function' ? getAuthenticatedUserId() : 1;
    const response = await fetch(`${API_BASE}/structured-workouts/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, plan_id: plan.id })
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const sessionData = await response.json();

    activeStructuredSession = {
      id: sessionData.id,
      plan: plan,
      currentExIndex: 0,
      currentSetNumber: 1,
      loggedSets: []
    };

    // Show Structured HUD Banner
    document.getElementById('structuredHudBanner').style.display = 'flex';
    document.getElementById('structuredRoutineTitle').innerText = plan.title;

    // Launch first exercise
    launchStructuredExercise();

  } catch (error) {
    console.error('[FitQuest Error]: Failed to start structured workout session:', error);
    alert('Failed to start structured workout. Ensure backend server is running.');
  }
}

/**
 * Prepares and launches the currently active exercise in the structured sequence
 */
async function launchStructuredExercise() {
  if (!activeStructuredSession) return;

  const currentEx = activeStructuredSession.plan.exercises[activeStructuredSession.currentExIndex];
  if (!currentEx) {
    finishStructuredWorkout();
    return;
  }

  selectedExercise = {
    id: currentEx.exercise_id,
    name: currentEx.exercise_name
  };

  // Update HUD progress text
  document.getElementById('structuredExProgress').innerText = `Exercise ${activeStructuredSession.currentExIndex + 1} of ${activeStructuredSession.plan.exercises.length}: ${currentEx.exercise_name}`;
  document.getElementById('structuredSetProgress').innerText = `Set ${activeStructuredSession.currentSetNumber} of ${currentEx.target_sets} (Target: ${currentEx.target_reps} Reps)`;

  // Reset CV telemetry state & timer
  resetCVExerciseState();

  // Call start-session backend API to guarantee clean controller initialization
  try {
    await fetch(`${API_BASE}/workouts/live/start-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: activeSessionId,
        exercise_choice: String(selectedExercise.id)
      })
    });
  } catch (e) {
    console.warn('[FitQuest Warning]: Live session start endpoint call failed:', e);
  }

  // Update title & transition directly to active step
  document.getElementById('activeExerciseTitle').innerText = `${currentEx.exercise_name} (Set ${activeStructuredSession.currentSetNumber})`;
  goToStep('workoutActiveStep');

  // Connect webcam feed & start live CV stream
  await startCameraStream();
}

/**
 * Resets CV exercise tracker telemetry state cleanly before starting next set/exercise
 */
function resetCVExerciseState() {
  activeSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  currentRepCount = 0;
  currentFormScore = 0.0;
  accumulatedFeedback = [];
  workoutElapsedSeconds = 0;

  document.getElementById('hudRepCount').innerText = '0';
  document.getElementById('hudFormScore').innerText = 'N/A';
  document.getElementById('hudDuration').innerText = '00:00';
  document.getElementById('hudFeedback').innerText = 'Get ready... Position yourself in front of camera.';

  if (workoutTimerInterval) clearInterval(workoutTimerInterval);
  workoutStartTime = Date.now();
  workoutTimerInterval = setInterval(() => {
    workoutElapsedSeconds = Math.floor((Date.now() - workoutStartTime) / 1000);
    document.getElementById('hudDuration').innerText = formatDuration(workoutElapsedSeconds);
  }, 1000);
}

/**
 * Handles completion of the current set in a structured workout
 */
async function completeCurrentSet() {
  if (!activeStructuredSession) {
    endWorkoutSession();
    return;
  }

  stopCameraStream();

  const currentEx = activeStructuredSession.plan.exercises[activeStructuredSession.currentExIndex];
  const setNum = activeStructuredSession.currentSetNumber;

  const setPayload = {
    structured_session_id: activeStructuredSession.id,
    exercise_id: currentEx.exercise_id,
    set_number: setNum,
    target_reps: currentEx.target_reps,
    actual_reps: currentRepCount,
    duration_sec: workoutElapsedSeconds,
    form_score: currentRepCount === 0 ? 0.0 : currentFormScore,
    feedback_events: accumulatedFeedback
  };

  try {
    const res = await fetch(`${API_BASE}/structured-workouts/log-set`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(setPayload)
    });

    if (res.ok) {
      const setLog = await res.json();
      activeStructuredSession.loggedSets.push(setLog);
    }
  } catch (err) {
    console.error('[FitQuest Error]: Failed to log set result:', err);
  }

  // Advance set or exercise
  if (setNum < currentEx.target_sets) {
    activeStructuredSession.currentSetNumber += 1;
    startRestTimer(45, `${currentEx.exercise_name} — Set ${activeStructuredSession.currentSetNumber} (${currentEx.target_reps} Reps)`);
  } else if (activeStructuredSession.currentExIndex < activeStructuredSession.plan.exercises.length - 1) {
    activeStructuredSession.currentExIndex += 1;
    activeStructuredSession.currentSetNumber = 1;
    const nextEx = activeStructuredSession.plan.exercises[activeStructuredSession.currentExIndex];
    startRestTimer(45, `${nextEx.exercise_name} — Set 1 (${nextEx.target_reps} Reps)`);
  } else {
    finishStructuredWorkout();
  }
}

/**
 * Starts the rest countdown timer between sets
 */
function startRestTimer(seconds, nextLabel) {
  // Pause frame transmission during rest
  if (frameCaptureInterval) {
    clearInterval(frameCaptureInterval);
    frameCaptureInterval = null;
  }

  restTimeRemaining = seconds;
  document.getElementById('restNextExerciseLabel').innerText = nextLabel;
  document.getElementById('restTimerDisplay').innerText = formatDuration(restTimeRemaining);
  document.getElementById('restTimerModal').style.display = 'flex';

  if (restTimerInterval) clearInterval(restTimerInterval);

  restTimerInterval = setInterval(() => {
    restTimeRemaining -= 1;
    document.getElementById('restTimerDisplay').innerText = formatDuration(restTimeRemaining);

    if (restTimeRemaining <= 0) {
      skipRestTimer();
    }
  }, 1000);
}

function addRestTime(sec) {
  restTimeRemaining += sec;
  document.getElementById('restTimerDisplay').innerText = formatDuration(restTimeRemaining);
}

function skipRestTimer() {
  if (restTimerInterval) {
    clearInterval(restTimerInterval);
    restTimerInterval = null;
  }
  document.getElementById('restTimerModal').style.display = 'none';

  // Resume next set/exercise
  launchStructuredExercise();
}

/**
 * Completes the entire structured workout routine and renders combined summary
 */
async function finishStructuredWorkout() {
  if (!activeStructuredSession) return;

  // Stop camera stream & background timer
  stopCameraStream();
  if (workoutTimerInterval) clearInterval(workoutTimerInterval);
  document.getElementById('structuredHudBanner').style.display = 'none';

  try {
    const res = await fetch(`${API_BASE}/structured-workouts/complete/${activeStructuredSession.id}`, {
      method: 'POST'
    });

    let summaryData = null;
    if (res.ok) {
      summaryData = await res.json();
    }

    renderStructuredSummaryView(summaryData);

  } catch (err) {
    console.error('[FitQuest Error]: Failed to complete structured workout:', err);
    goToStep('workoutSelectionStep');
  } finally {
    activeStructuredSession = null;
  }
}

/**
 * Renders the combined workout summary breakdown in workoutResultStep
 */
function renderStructuredSummaryView(summary) {
  goToStep('workoutResultStep');

  if (summary) {
    const totalDurationSec = summary.sets ? summary.sets.reduce((acc, s) => acc + (s.duration_sec || 0), 0) : 0;
    document.getElementById('resRepCount').innerText = `${summary.total_actual_reps} / ${summary.total_target_reps}`;
    document.getElementById('resDuration').innerText = formatDuration(totalDurationSec);
    document.getElementById('resFormScore').innerText = summary.completed_sets > 0 ? `${summary.average_form_score}%` : 'N/A';

    const aiMessage = `
      <strong>🏆 Structured Routine Completed!</strong><br>
      You completed <strong>${summary.completed_sets} sets</strong> across <strong>${summary.total_exercises} exercises</strong> with an average form accuracy of <strong>${summary.average_form_score}%</strong>.
    `;
    document.getElementById('resAICoaching').innerHTML = formatMarkdownText(aiMessage);
  }

  // Refresh gamification streaks
  if (typeof loadGamificationData === 'function') {
    loadGamificationData();
  }
}

// Export UI functions to window object
window.switchWorkoutMode = switchWorkoutMode;
window.openStructuredPlanModal = openStructuredPlanModal;
window.closeStructuredPlanModal = closeStructuredPlanModal;
window.completeCurrentSet = completeCurrentSet;
window.skipRestTimer = skipRestTimer;
window.addRestTime = addRestTime;


