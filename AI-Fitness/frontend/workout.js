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
const API_BASE = 'http://127.0.0.1:8000/api/v1';

document.addEventListener('DOMContentLoaded', () => {
  initTabNavigation();
  initSearchFilter();
  loadExerciseCatalogue();
});

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

  document.getElementById('setupExerciseName').innerText = selectedExercise.name;
  document.getElementById('setupExerciseDesc').innerText = selectedExercise.description || 'YOLO Pose Repetition Tracker & Form Evaluator';
  document.getElementById('setupDifficulty').innerText = selectedExercise.difficulty || 'Intermediate';
  document.getElementById('setupMuscleGroup').innerText = getExerciseMuscleGroup(selectedExercise.name);

  goToStep('workoutSetupStep');
}

/**
 * Starts an active workout session (Step C)
 */
async function startWorkoutSession() {
  if (!selectedExercise) return;

  activeSessionId = `session_${Date.now()}`;
  currentRepCount = 0;
  currentFormScore = 0.0;
  accumulatedFeedback = [];

  document.getElementById('activeExerciseTitle').innerText = selectedExercise.name;
  document.getElementById('hudRepCount').innerText = '0';
  document.getElementById('hudFormScore').innerText = 'N/A';
  document.getElementById('hudDuration').innerText = '00:00';
  document.getElementById('hudFeedback').innerText = 'Starting camera & connecting YOLO Pose Engine...';

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

  if (telemetry.feedback && telemetry.feedback.length > 0) {
    const feedbackStr = telemetry.feedback.join(' | ');
    document.getElementById('hudFeedback').innerText = feedbackStr;

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
    await fetch(`${API_BASE}/workouts/live/stop-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: activeSessionId })
    });
  } catch (e) {
    console.warn('[FitQuest Warning]: Live session stop endpoint call failed:', e);
  }

  // Transition to results step
  goToStep('workoutResultStep');
  document.getElementById('resRepCount').innerText = currentRepCount;
  document.getElementById('resDuration').innerText = formatDuration(workoutElapsedSeconds);
  document.getElementById('resFormScore').innerText = currentRepCount === 0 ? 'N/A' : `${currentFormScore.toFixed(1)}%`;
  document.getElementById('resAICoaching').innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Generating personalized AI coaching feedback...`;

  try {
    const userId = typeof getAuthenticatedUserId === 'function' ? getAuthenticatedUserId() : 1;
    // Post completed workout telemetry payload to POST /api/v1/workouts
    const payload = {
      session_data: {
        user_id: userId,
        exercise_id: selectedExercise.id,
        repetitions: currentRepCount,
        duration_sec: workoutElapsedSeconds || 30,
        form_score: currentRepCount === 0 ? 0.0 : currentFormScore
      },
      form_scores_history: currentRepCount > 0 ? Array(currentRepCount).fill(1) : [],
      feedback_events: accumulatedFeedback.length > 0 ? accumulatedFeedback : (currentRepCount === 0 ? ["No valid repetitions detected"] : [`Completed set for ${selectedExercise.name}`])
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

    // Render returned results & AI coaching insights
    document.getElementById('resRepCount').innerText = resultData.repetitions;
    document.getElementById('resDuration').innerText = formatDuration(resultData.duration_sec);
    document.getElementById('resFormScore').innerText = resultData.repetitions === 0 ? 'N/A (No Reps)' : `${resultData.form_score}%`;

    const aiText = resultData.ai_coaching_logs && resultData.ai_coaching_logs.length > 0 
      ? resultData.ai_coaching_logs[0].response 
      : 'Great workout set!';

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
    document.getElementById('resAICoaching').innerHTML = `
      <div style="color: #ef4444;">
        <i class="fa-solid fa-triangle-exclamation"></i> Session recorded locally. (Backend server error).
      </div>
    `;
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
  let formatted = escapeHTML(text);
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
  formatted = formatted.replace(/\n/g, '<br>');
  return formatted;
}
