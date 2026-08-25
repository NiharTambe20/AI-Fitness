/**
 * FitQuest Authentication & User Profile Manager
 * Manages Registration, Login, Token Storage, Persistent Sessions, Profile Updates, and Protected Route Redirection.
 */

const AUTH_API_BASE = 'http://127.0.0.1:8000/api/v1/auth';

// State
let currentUser = null;
let authToken = localStorage.getItem('fitquest_token') || null;

document.addEventListener('DOMContentLoaded', () => {
  initAuthUI();
  checkPersistentSession();
});

/**
 * Initializes Event Listeners for Login, Register, Profile Edit, Logout, and User Dropdown
 */
function initAuthUI() {
  // Auth Form Tabs Switcher (Login <-> Signup)
  const authTabs = document.querySelectorAll('.auth-tab-btn');
  authTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      authTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const formType = tab.getAttribute('data-auth-form');
      if (formType === 'login') {
        document.getElementById('loginFormContainer').style.display = 'block';
        document.getElementById('registerFormContainer').style.display = 'none';
      } else {
        document.getElementById('loginFormContainer').style.display = 'none';
        document.getElementById('registerFormContainer').style.display = 'block';
      }
      clearAuthAlerts();
    });
  });

  // Login Form Submission
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearAuthAlerts();

      const email = document.getElementById('loginEmail').value.trim();
      const password = document.getElementById('loginPassword').value;

      if (!email || !password) {
        showAuthError('Please enter both email and password.');
        return;
      }

      setAuthBtnLoading('loginBtn', true);
      try {
        const response = await fetch(`${AUTH_API_BASE}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Login failed. Please check your credentials.');
        }

        handleAuthSuccess(data);
      } catch (err) {
        showAuthError(err.message);
      } finally {
        setAuthBtnLoading('loginBtn', false);
      }
    });
  }

  // Register Form Submission
  const registerForm = document.getElementById('registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearAuthAlerts();

      const name = document.getElementById('regName').value.trim();
      const email = document.getElementById('regEmail').value.trim();
      const password = document.getElementById('regPassword').value;
      const confirmPassword = document.getElementById('regConfirmPassword').value;
      const fitnessGoal = document.getElementById('regFitnessGoal').value;
      const experienceLevel = document.getElementById('regExperienceLevel').value;
      const age = document.getElementById('regAge').value ? parseInt(document.getElementById('regAge').value) : null;
      const height = document.getElementById('regHeight').value ? parseFloat(document.getElementById('regHeight').value) : null;
      const weight = document.getElementById('regWeight').value ? parseFloat(document.getElementById('regWeight').value) : null;
      const gender = document.getElementById('regGender').value || null;

      if (!name || !email || !password) {
        showAuthError('Please fill in all required fields (Name, Email, Password).');
        return;
      }

      if (password !== confirmPassword) {
        showAuthError('Passwords do not match. Please re-enter your password.');
        return;
      }

      const payload = {
        name,
        email,
        password,
        fitness_goal: fitnessGoal,
        experience_level: experienceLevel,
        age,
        height,
        weight,
        gender
      };

      setAuthBtnLoading('registerBtn', true);
      try {
        const response = await fetch(`${AUTH_API_BASE}/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Registration failed. Duplicate email or invalid input.');
        }

        handleAuthSuccess(data);
      } catch (err) {
        showAuthError(err.message);
      } finally {
        setAuthBtnLoading('registerBtn', false);
      }
    });
  }

  // Profile Edit Form Submission
  const profileEditForm = document.getElementById('profileEditForm');
  if (profileEditForm) {
    profileEditForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const updatePayload = {
        name: document.getElementById('editName').value.trim(),
        fitness_goal: document.getElementById('editFitnessGoal').value,
        experience_level: document.getElementById('editExperienceLevel').value,
        age: document.getElementById('editAge').value ? parseInt(document.getElementById('editAge').value) : null,
        height: document.getElementById('editHeight').value ? parseFloat(document.getElementById('editHeight').value) : null,
        weight: document.getElementById('editWeight').value ? parseFloat(document.getElementById('editWeight').value) : null,
        gender: document.getElementById('editGender').value || null
      };

      try {
        const response = await fetch(`${AUTH_API_BASE}/profile`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify(updatePayload)
        });

        const updatedUser = await response.json();
        if (!response.ok) {
          throw new Error(updatedUser.detail || 'Failed to update profile.');
        }

        currentUser = updatedUser;
        renderProfilePage();
        updateUserNavBadge();
        toggleEditProfileModal(false);
        alert('Profile updated successfully!');
      } catch (err) {
        alert(`Error updating profile: ${err.message}`);
      }
    });
  }
}

/**
 * Checks for stored authentication token on page refresh
 */
async function checkPersistentSession() {
  if (!authToken) {
    showUnauthenticatedState();
    return;
  }

  try {
    const response = await fetch(`${AUTH_API_BASE}/me`, {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    if (!response.ok) {
      throw new Error('Token expired or invalid');
    }

    currentUser = await response.json();
    showAuthenticatedState();
  } catch (err) {
    console.warn('[FitQuest Auth]: Persistent session check failed:', err);
    logoutUser();
  }
}

/**
 * Handles successful login or registration
 */
function handleAuthSuccess(authData) {
  authToken = authData.access_token;
  currentUser = authData.user;
  localStorage.setItem('fitquest_token', authToken);

  showAuthenticatedState();
  switchTab('homeView');
}

/**
 * Logs out user and resets UI state
 */
async function logoutUser() {
  if (authToken) {
    try {
      await fetch(`${AUTH_API_BASE}/logout`, { method: 'POST' });
    } catch (e) {
      // Ignore
    }
  }

  authToken = null;
  currentUser = null;
  localStorage.removeItem('fitquest_token');

  showUnauthenticatedState();
}

/**
 * Switches UI to Authenticated state
 */
function showAuthenticatedState() {
  document.getElementById('authView').style.display = 'none';
  document.getElementById('appMainWrapper').style.display = 'block';

  updateUserNavBadge();
  renderProfilePage();

  if (typeof loadGamificationData === 'function') {
    loadGamificationData();
  }

  // If coming from login, default to home view if active view is authView
  const currentActivePanel = document.querySelector('.view-panel.active');
  if (!currentActivePanel || currentActivePanel.id === 'authView') {
    switchTab('homeView');
  } else {
    // Reload user-specific history if currently on historyView
    if (currentActivePanel.id === 'historyView' && typeof loadWorkoutHistory === 'function') {
      loadWorkoutHistory();
    }
  }
}


/**
 * Switches UI to Unauthenticated state
 */
function showUnauthenticatedState() {
  document.getElementById('appMainWrapper').style.display = 'none';
  document.getElementById('authView').style.display = 'block';

  const viewPanels = document.querySelectorAll('.view-panel');
  viewPanels.forEach(panel => panel.classList.remove('active'));
  document.getElementById('authView').classList.add('active');
}

/**
 * Updates Top Navigation user badge with active user's name & dropdown menu
 */
function updateUserNavBadge() {
  const userBadge = document.getElementById('userNavBadge');
  if (!userBadge || !currentUser) return;

  userBadge.innerHTML = `
    <div class="user-dropdown-container">
      <button class="user-dropdown-trigger" onclick="toggleUserDropdown(event)">
        <i class="fa-solid fa-circle-user"></i> ${escapeHTML(currentUser.name)} <i class="fa-solid fa-caret-down"></i>
      </button>
      <div id="userDropdownMenu" class="user-dropdown-menu">
        <div class="dropdown-header">
          <strong>${escapeHTML(currentUser.name)}</strong>
          <span class="dropdown-email">${escapeHTML(currentUser.email)}</span>
        </div>
        <div class="dropdown-divider"></div>
        <button class="dropdown-item" onclick="openProfileTab()">
          <i class="fa-solid fa-address-card"></i> My Profile
        </button>
        <button class="dropdown-item danger" onclick="logoutUser()">
          <i class="fa-solid fa-right-from-bracket"></i> Logout
        </button>
      </div>
    </div>
  `;
}

/**
 * Toggles header user profile dropdown menu
 */
function toggleUserDropdown(event) {
  event.stopPropagation();
  const menu = document.getElementById('userDropdownMenu');
  if (menu) {
    menu.classList.toggle('show');
  }
}

// Close dropdown on outside click
document.addEventListener('click', (e) => {
  const menu = document.getElementById('userDropdownMenu');
  if (menu && menu.classList.contains('show')) {
    menu.classList.remove('show');
  }
});

/**
 * Renders Profile Page view with authenticated user info
 */
function renderProfilePage() {
  if (!currentUser) return;

  document.getElementById('profAvatarInitial').innerText = currentUser.name.charAt(0).toUpperCase();
  document.getElementById('profName').innerText = currentUser.name;
  document.getElementById('profEmail').innerText = currentUser.email;

  document.getElementById('profGoal').innerText = currentUser.fitness_goal || 'General Fitness';
  document.getElementById('profExperience').innerText = currentUser.experience_level || 'Beginner';

  document.getElementById('profAge').innerText = currentUser.age ? `${currentUser.age} yrs` : 'Not specified';
  document.getElementById('profHeight').innerText = currentUser.height ? `${currentUser.height} cm` : 'Not specified';
  document.getElementById('profWeight').innerText = currentUser.weight ? `${currentUser.weight} kg` : 'Not specified';
  document.getElementById('profGender').innerText = currentUser.gender || 'Not specified';
}

/**
 * Opens My Profile tab directly from header dropdown
 */
function openProfileTab() {
  switchTab('profileView');
}

/**
 * Toggles Edit Profile Modal visibility
 */
function toggleEditProfileModal(show) {
  const modal = document.getElementById('editProfileModal');
  if (!modal) return;

  if (show) {
    document.getElementById('editName').value = currentUser.name;
    document.getElementById('editFitnessGoal').value = currentUser.fitness_goal || 'General Fitness';
    document.getElementById('editExperienceLevel').value = currentUser.experience_level || 'Beginner';
    document.getElementById('editAge').value = currentUser.age || '';
    document.getElementById('editHeight').value = currentUser.height || '';
    document.getElementById('editWeight').value = currentUser.weight || '';
    document.getElementById('editGender').value = currentUser.gender || '';
    modal.style.display = 'flex';
  } else {
    modal.style.display = 'none';
  }
}

/**
 * Returns active user ID or fallback
 */
function getAuthenticatedUserId() {
  return currentUser ? currentUser.id : 1;
}

/**
 * Returns active user profile object for AI Coach
 */
function getAuthenticatedUserProfile() {
  if (!currentUser) {
    return { fitness_goal: 'General Fitness', experience_level: 'Beginner' };
  }
  return {
    user_id: String(currentUser.id),
    fitness_goal: currentUser.fitness_goal || 'General Fitness',
    experience_level: currentUser.experience_level || 'Beginner'
  };
}

/* Helpers */
function showAuthError(msg) {
  const alertBox = document.getElementById('authAlertBox');
  if (alertBox) {
    alertBox.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${escapeHTML(msg)}`;
    alertBox.style.display = 'block';
  }
}

function clearAuthAlerts() {
  const alertBox = document.getElementById('authAlertBox');
  if (alertBox) {
    alertBox.style.display = 'none';
    alertBox.innerHTML = '';
  }
}

function setAuthBtnLoading(btnId, isLoading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = isLoading;
  if (isLoading) {
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Please wait...`;
  } else {
    btn.innerHTML = btnId === 'loginBtn' ? 'Login' : 'Create Account';
  }
}

function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
}
