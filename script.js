function toggleMenu() {
  const header = document.querySelector('.header');
  const toggleBtn = header.querySelector('.toggle');
  // Expand or collapse
  header.classList.toggle('expanded');
  toggleBtn.classList.toggle('rotated');
}

function showSection(sectionId) {
  const allSections = document.querySelectorAll('section[id]');
  const header = document.querySelector('.header');
  const toggleBtn = header.querySelector('.toggle');
  const landingIframe = document.querySelector('.landing-iframe');

  // Hide all sections
  allSections.forEach(sec => sec.classList.add('hidden'));

  if (sectionId === 'pricing') {
    document.getElementById('pricing').classList.remove('hidden');
  } else if (sectionId === 'about') {
    document.getElementById('about').classList.remove('hidden');
    document.getElementById('about-mission').classList.remove('hidden');
    document.getElementById('about-innovation').classList.remove('hidden');
  } else if (sectionId === 'create') {
    document.getElementById('create').classList.remove('hidden');
    document.getElementById('create-steps').classList.remove('hidden');
  } else {
    // Default: show landing sections
    document.getElementById('landing').classList.remove('hidden');
    document.getElementById('landing-carousel').classList.remove('hidden');
    document.getElementById('landing-additional').classList.remove('hidden');
    document.getElementById('landing-stats').classList.remove('hidden');
    document.getElementById('landing-stats2').classList.remove('hidden');
    document.getElementById('landing-more').classList.remove('hidden');
    document.getElementById('landing-more2').classList.remove('hidden');
  }

  // If the landing page is not active, remove the iframe src (to unload it)
  if (sectionId !== 'landing') {
    landingIframe.src = "";
  } else {
    landingIframe.src = "https://hansenhomeai.github.io/WebbyDeerKnoll/";
  }

  // Scroll to the top of the page when switching sections
  window.scrollTo(0, 0);

  // If the header is expanded, close it
  if (header.classList.contains('expanded')) {
    header.classList.remove('expanded');
    toggleBtn.classList.remove('rotated');
  }
}

function sendFeedback(e) {
  e.preventDefault();
  const feedbackInput = document.querySelector('input[name="feedback"]');
  const feedback = feedbackInput.value.trim();
  if (!feedback) {
    alert('Please enter your feedback before sending.');
    return;
  }

  const button = document.querySelector('.feedback-button');
  const originalText = button.textContent;
  button.textContent = ''; // Clear text

  // Create a check icon
  const checkSpan = document.createElement('span');
  checkSpan.textContent = '✓';
  checkSpan.style.fontSize = '1.2rem';
  checkSpan.style.display = 'inline-block';
  checkSpan.style.textAlign = 'center';
  button.appendChild(checkSpan);

  // Open user's email client
  window.location.href = `mailto:hello@hansenhome.ai?subject=Feedback&body=${encodeURIComponent(feedback)}`;

  // Clear input
  feedbackInput.value = '';

  // After 2 seconds, revert the button
  setTimeout(() => {
    button.removeChild(checkSpan);
    button.textContent = originalText;
  }, 2000);
}

function updateIframeOverlay() {
  const textBox = document.querySelector('.landing-content');
  const overlay = document.getElementById('iframe-overlay');

  if (textBox && overlay) {
    const textBoxHeight = textBox.offsetHeight;
    const textBoxTop = textBox.offsetTop;
    overlay.style.height = `calc(100vh - ${textBoxTop + textBoxHeight}px)`;
    overlay.style.top = `${textBoxTop + textBoxHeight}px`;
  }
}

document.addEventListener("DOMContentLoaded", function () {
  let hoverElements = document.querySelectorAll(".logo, .toggle, .nav-links a, .nav-links-desktop a, .cta-button, .cta-button2, .cta-button2-fixed");

  hoverElements.forEach(element => {
    element.addEventListener("touchstart", function () {
      element.classList.add("disable-hover");
      setTimeout(() => {
        element.classList.remove("disable-hover");
      }, 500); // Adjust timeout as needed
    });
  });
});

// Update overlay on load and resize
window.addEventListener('load', updateIframeOverlay);
window.addEventListener('resize', updateIframeOverlay);

document.addEventListener('DOMContentLoaded', () => {
  showSection('landing');

  // Close the header if clicked outside while expanded
  document.addEventListener('click', (e) => {
    const header = document.querySelector('.header');
    const toggleBtn = header.querySelector('.toggle');
    if (header.classList.contains('expanded') && !header.contains(e.target)) {
      header.classList.remove('expanded');
      toggleBtn.classList.remove('rotated');
    }
  });
});
