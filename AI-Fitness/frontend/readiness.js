/**
 * FitQuest Training Readiness & Daily Recommendation Module
 * Fetches deterministic readiness scores, recommendations, and status metrics from GET /api/v1/readiness/me.
 */

let recommendedExerciseId = null;

document.addEventListener('DOMContentLoaded', () => {
  initReadinessObserver();
});

/**
 * Observes navigation switches to load readiness metrics whenever homeView is displayed.
 */
function initReadinessObserver() {
  loadTrainingReadiness();

  const navTabs = document.querySelectorAll('.nav-tab');
  navTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      if (tab.getAttribute('data-view') === 'homeView') {
        loadTrainingReadiness();
      }
    });
  });
}

/**
 * Fetches training readiness metrics from GET /api/v1/readiness/me
 */
async function loadTrainingReadiness() {
  const token = localStorage.getItem('fitquest_token');
  const headers = { 'Accept': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE}/readiness/me`, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    renderReadinessCard(data);

  } catch (error) {
    console.error('[FitQuest Readiness Error]: Failed to fetch training readiness:', error);
  }
}

/**
 * Renders Training Readiness Widget Card UI
 */
function renderReadinessCard(data) {
  const scoreVal = document.getElementById('readinessScoreVal');
  const statusText = document.getElementById('readinessStatusText');
  const intensityEl = document.getElementById('readinessIntensity');
  const focusEl = document.getElementById('readinessFocus');
  const formTrendEl = document.getElementById('readinessFormTrend');
  const explanationEl = document.getElementById('readinessExplanation');
  const startBtn = document.getElementById('startRecommendedBtn');
  const exBtnName = document.getElementById('recommendedExNameBtn');
  const iconGauge = document.getElementById('readinessGaugeIcon');

  if (!statusText) return;

  // 1. Insufficient Data State (0 valid workouts)
  if (data.status === 'INSUFFICIENT_DATA' || data.readiness_score === null) {
    if (scoreVal) scoreVal.innerText = 'N/A';
    statusText.innerText = 'INSUFFICIENT WORKOUT DATA';
    statusText.style.color = 'var(--text-muted)';
    if (intensityEl) intensityEl.innerText = 'N/A (Complete 1st Workout)';
    if (focusEl) focusEl.innerText = 'General Fitness';
    if (formTrendEl) formTrendEl.innerText = 'N/A';
    if (explanationEl) {
      explanationEl.innerText = data.explanation || 'Complete your first valid workout session to unlock your personalized FitQuest Training Readiness.';
    }
    if (startBtn) startBtn.style.display = 'none';
    return;
  }

  // 2. Valid Readiness State (Score 0 - 100)
  const score = data.readiness_score;
  if (scoreVal) scoreVal.innerText = `${score} / 100`;

  let statusColor = 'var(--accent-cyan)';
  let readableStatus = 'READY TO TRAIN';

  if (data.status === 'READY_TO_TRAIN') {
    statusColor = 'var(--accent-cyan)';
    readableStatus = 'READY TO TRAIN';
  } else if (data.status === 'GOOD_TO_TRAIN') {
    statusColor = 'var(--accent-green)';
    readableStatus = 'GOOD TO TRAIN';
  } else if (data.status === 'LIGHT_TRAINING') {
    statusColor = '#f59e0b';
    readableStatus = 'LIGHT TRAINING RECOMMENDED';
  } else if (data.status === 'RECOVERY_RECOMMENDED') {
    statusColor = '#ef4444';
    readableStatus = 'RECOVERY RECOMMENDED';
  }

  statusText.innerText = readableStatus;
  statusText.style.color = statusColor;

  if (scoreVal) scoreVal.style.color = statusColor;
  if (iconGauge) iconGauge.style.color = statusColor;

  // Recommended Intensity
  if (intensityEl) {
    const rawIntensity = data.recommended_intensity || 'MODERATE';
    intensityEl.innerText = rawIntensity.replace(/_/g, ' ').toUpperCase();
  }

  // Recommended Focus
  if (focusEl) {
    const rawFocus = data.recommended_focus || 'FULL_BODY';
    focusEl.innerText = rawFocus.replace(/_/g, ' ').toUpperCase();
  }

  // Recent Form Trend
  if (formTrendEl) {
    const trend = data.supporting_metrics?.form_trend || 'STABLE';
    if (trend === 'IMPROVING') {
      formTrendEl.innerHTML = '<span style="color: var(--accent-green);"><i class="fa-solid fa-arrow-trend-up"></i> Improving</span>';
    } else if (trend === 'DECLINING') {
      formTrendEl.innerHTML = '<span style="color: #ef4444;"><i class="fa-solid fa-arrow-trend-down"></i> Declining</span>';
    } else {
      formTrendEl.innerHTML = '<span style="color: var(--accent-cyan);"><i class="fa-solid fa-minus"></i> Stable</span>';
    }
  }

  // Explanation
  if (explanationEl) {
    explanationEl.innerText = data.explanation || '';
  }

  // Recommended Exercise Button
  if (data.recommended_exercise_id && data.recommended_exercise_name) {
    recommendedExerciseId = data.recommended_exercise_id;
    if (exBtnName) exBtnName.innerText = data.recommended_exercise_name;
    if (startBtn) startBtn.style.display = 'inline-flex';
  } else if (startBtn) {
    startBtn.style.display = 'none';
  }
}

/**
 * Handles clicking "Start Recommended Workout" button safely
 */
function startRecommendedWorkout() {
  if (typeof switchTab === 'function') {
    switchTab('workoutView');
  }

  if (recommendedExerciseId && typeof selectExercise === 'function') {
    setTimeout(() => {
      selectExercise(recommendedExerciseId);
    }, 150);
  }
}
