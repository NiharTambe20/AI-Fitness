/**
 * FitQuest — Cinematic 3D Landing Page Controller
 * Manages 3D Extruded Wordmark Mouse Parallax, Typing Reveal Animation, 5-Layer 3D Scroll Reveal & Application Transition.
 */

(function () {
  let isLandingActive = true;
  let targetRotateX = 0;
  let targetRotateY = 0;
  let currentRotateX = 0;
  let currentRotateY = 0;
  let animFrameId = null;
  let isTouchDevice = false;
  let hasTypedWordmark = false;

  document.addEventListener('DOMContentLoaded', () => {
    initLandingPage();
  });

  function initLandingPage() {
    const landingView = document.getElementById('landingView');
    const wordmark = document.getElementById('hero3DWordmark');
    const enterBtns = document.querySelectorAll('.btn-landing-enter');
    const brandLinks = document.querySelectorAll('.nav-brand');

    if (!landingView) return;

    // Detect touch device
    isTouchDevice = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || window.matchMedia('(pointer: coarse)').matches;

    // 1. Typing Reveal Animation for FITQUEST
    initWordmarkTypingAnimation();

    // 2. Desktop Mouse Movement Listener for 3D Parallax Tilt on Hero Wordmark
    if (!isTouchDevice && wordmark) {
      window.addEventListener('mousemove', handleMouseMove, { passive: true });
      window.addEventListener('mouseleave', handleMouseLeave, { passive: true });
      startParallaxLoop();
    }

    // 3. Multi-Layer 3D Scroll Reveal Listener
    landingView.addEventListener('scroll', handleLandingScroll, { passive: true });
    handleLandingScroll();

    // 4. CTA Click Handlers — Enter FitQuest Main Application
    enterBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        enterApplication();
      });
    });

    // 5. Brand Click Handler (Shift + Click returns to Landing Page)
    brandLinks.forEach((brand) => {
      brand.addEventListener('click', (e) => {
        if (e.shiftKey) {
          e.preventDefault();
          showLandingPage();
        }
      });
    });

    // Handle initial entrance completion
    setTimeout(() => {
      landingView.classList.add('entrance-complete');
    }, 1200);
  }

  /**
   * Sequential Typing Reveal Animation for "FITQUEST" Wordmark
   */
  function initWordmarkTypingAnimation() {
    const textEl = document.getElementById('wordmarkText');
    const cursorEl = document.getElementById('wordmarkCursor');
    if (!textEl) return;

    const fullWord = 'FITQUEST';
    let charIndex = 0;

    // Reset initial state
    textEl.textContent = '';
    if (cursorEl) {
      cursorEl.style.opacity = '1';
      cursorEl.style.display = 'inline-block';
    }

    function typeNextChar() {
      if (charIndex <= fullWord.length) {
        textEl.textContent = fullWord.substring(0, charIndex);
        charIndex++;

        if (charIndex <= fullWord.length) {
          setTimeout(typeNextChar, 90);
        } else {
          // Finished typing FITQUEST — fade out blinking cursor
          setTimeout(() => {
            if (cursorEl) {
              cursorEl.style.opacity = '0';
              setTimeout(() => {
                cursorEl.style.display = 'none';
              }, 400);
            }
            hasTypedWordmark = true;
          }, 350);
        }
      }
    }

    // Start typing after brief initial delay (150ms)
    setTimeout(typeNextChar, 150);
  }

  /**
   * Manages 3D Layered Scroll Transformations across all 5 Cinematic Layers
   */
  function handleLandingScroll() {
    if (!isLandingActive) return;

    const landingView = document.getElementById('landingView');
    if (!landingView) return;

    const layers = landingView.querySelectorAll('.landing-layer');
    if (!layers || layers.length === 0) return;

    const viewHeight = landingView.clientHeight || window.innerHeight;
    const scrollTop = landingView.scrollTop;

    layers.forEach((layer, idx) => {
      const layerTop = idx * viewHeight;
      const progress = (scrollTop - layerTop) / viewHeight;

      if (progress > 1.2 || progress < -1.2) {
        layer.style.opacity = '0';
        layer.style.pointerEvents = 'none';
        return;
      }

      layer.style.pointerEvents = 'auto';

      if (progress >= 0 && progress <= 1) {
        // Layer scrolling OUT into background depth
        const scale = (1 - progress * 0.15).toFixed(3);
        const opacity = Math.max(0, 1 - progress * 1.1).toFixed(3);
        const translateY = (-progress * 50).toFixed(1);
        const translateZ = (-progress * 120).toFixed(1);

        layer.style.opacity = opacity;
        layer.style.transform = `translate3d(0, ${translateY}px, ${translateZ}px) scale(${scale})`;
      } else if (progress < 0 && progress >= -1) {
        // Layer scrolling IN from deeper space below
        const normIn = 1 + progress;
        const scale = (0.88 + normIn * 0.12).toFixed(3);
        const opacity = Math.min(1, Math.max(0, normIn * 1.25)).toFixed(3);
        const translateY = ((1 - normIn) * 70).toFixed(1);
        const translateZ = (-(1 - normIn) * 80).toFixed(1);

        layer.style.opacity = opacity;
        layer.style.transform = `translate3d(0, ${translateY}px, ${translateZ}px) scale(${scale})`;
      } else {
        // Layer centered
        layer.style.opacity = '1';
        layer.style.transform = 'translate3d(0, 0px, 0px) scale(1)';
      }
    });
  }

  /**
   * Calculates mouse distance relative to viewport center for 3D tilt
   */
  function handleMouseMove(e) {
    if (!isLandingActive) return;

    const centerX = window.innerWidth / 2;
    const centerY = window.innerHeight / 2;

    const normX = (e.clientX - centerX) / centerX;
    const normY = (e.clientY - centerY) / centerY;

    targetRotateY = normX * 8;
    targetRotateX = -normY * 8;
  }

  /**
   * Smoothly resets 3D tilt when mouse leaves browser window
   */
  function handleMouseLeave() {
    targetRotateX = 0;
    targetRotateY = 0;
  }

  /**
   * Animation Loop using RequestAnimationFrame for 60fps smooth 3D tilt
   */
  function startParallaxLoop() {
    function updateTilt() {
      if (isLandingActive && !isTouchDevice) {
        const wordmark = document.getElementById('hero3DWordmark');
        if (wordmark) {
          currentRotateX += (targetRotateX - currentRotateX) * 0.08;
          currentRotateY += (targetRotateY - currentRotateY) * 0.08;

          wordmark.style.transform = `perspective(1000px) rotateX(${currentRotateX.toFixed(2)}deg) rotateY(${currentRotateY.toFixed(2)}deg)`;
        }
      }
      animFrameId = requestAnimationFrame(updateTilt);
    }
    updateTilt();
  }

  /**
   * Transitions from Cinematic Landing Page into the main FitQuest application
   */
  function enterApplication() {
    const landingView = document.getElementById('landingView');
    if (!landingView) return;

    isLandingActive = false;
    landingView.classList.add('fade-out');

    setTimeout(() => {
      landingView.style.display = 'none';
      landingView.classList.remove('fade-out');
      landingView.scrollTop = 0;

      const token = localStorage.getItem('fitquest_token');
      const authView = document.getElementById('authView');
      const appMainWrapper = document.getElementById('appMainWrapper');

      if (token) {
        if (authView) authView.style.display = 'none';
        if (appMainWrapper) appMainWrapper.style.display = 'block';

        if (typeof switchTab === 'function') {
          switchTab('homeView');
        }
        if (typeof loadGamificationData === 'function') {
          loadGamificationData();
        }
      } else {
        if (appMainWrapper) appMainWrapper.style.display = 'none';
        if (authView) {
          authView.style.display = 'flex';
          authView.classList.add('active');
        }
      }
    }, 400);
  }

  /**
   * Re-displays the Landing Page
   */
  function showLandingPage() {
    const landingView = document.getElementById('landingView');
    const authView = document.getElementById('authView');
    const appMainWrapper = document.getElementById('appMainWrapper');

    if (landingView) {
      isLandingActive = true;
      landingView.scrollTop = 0;

      if (authView) authView.style.display = 'none';
      if (appMainWrapper) appMainWrapper.style.display = 'none';

      landingView.style.display = 'block';
      landingView.classList.remove('fade-out');
      landingView.classList.add('entrance-complete');

      // Re-trigger typing animation if returning
      initWordmarkTypingAnimation();
      handleLandingScroll();
    }
  }

  window.enterFitquestApp = enterApplication;
  window.showLandingPage = showLandingPage;
})();
