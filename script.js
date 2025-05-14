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

  // Hide ALL sections first
  allSections.forEach(sec => sec.classList.add('hidden'));

  // Then show only the relevant sections
  if (sectionId === 'pricing') {
    document.getElementById('pricing-header').classList.remove('hidden');
    document.getElementById('pricing').classList.remove('hidden');
  } else if (sectionId === 'about') {
    document.getElementById('about').classList.remove('hidden');
    document.getElementById('about-mission').classList.remove('hidden');
    document.getElementById('about-innovation').classList.remove('hidden');
  } else if (sectionId === 'create') {
    document.getElementById('create').classList.remove('hidden');
    document.getElementById('create-steps1').classList.remove('hidden');
    document.getElementById('create-steps2').classList.remove('hidden');
    document.getElementById('create-steps3').classList.remove('hidden');
  } else if (sectionId === 'landing') {  // Make this explicit
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

  // Initialize popup functionality
  const popup = document.getElementById('addPathPopup');
  const uploadArea = document.getElementById('csvUploadArea');
  const fileInput = document.getElementById('csvFileInput');
  
  if (popup) {
    popup.classList.add('hidden');
  }

  if (uploadArea && fileInput) {
    // Click to upload
    uploadArea.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.click();
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.stopPropagation();
      uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.4)';
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
      e.preventDefault();
      e.stopPropagation();
      uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.2)';
    });
    
    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.2)';
      if (e.dataTransfer.files.length) {
        handleFileUpload(e.dataTransfer.files[0]);
      }
    });
    
    // File input change
    fileInput.addEventListener('change', (e) => {
      e.stopPropagation();
      if (e.target.files.length) {
        handleFileUpload(e.target.files[0]);
      }
    });
  }
});

// FILE: dronePathGenerator.js
(function() {
  let poiCount = 0;
  let hoverTimer = null;

  const modeToggle = document.getElementById('modeToggle');
  const standardModeUI = document.getElementById('standardModeUI');
  const advancedModeUI = document.getElementById('advancedModeUI');
  const ranchModeUI = document.getElementById('ranchModeUI');
  const poiSection = document.getElementById('poiSection');
  const addPoiButton = document.getElementById('addPoiButton');

  // 1) Setup the text-field hover logic (0.45s delay).
  document.querySelectorAll('#dfpg-container .input-wrapper').forEach((wrapper) => {
    const inputElem = wrapper.querySelector('input');
    const overlay = wrapper.querySelector('.hover-overlay');
    const labelText = wrapper.getAttribute('data-label') || '';
    overlay.innerHTML = labelText;

    inputElem.addEventListener('mouseenter', () => {
      if (inputElem.value.trim() !== '') {
        hoverTimer = setTimeout(() => {
          wrapper.classList.add('hover-active');
        }, 450);
      }
    });
    inputElem.addEventListener('mouseleave', () => {
      clearTimeout(hoverTimer);
      wrapper.classList.remove('hover-active');
    });
    // If user clicks/focuses, hide the overlay:
    inputElem.addEventListener('focus', () => {
      clearTimeout(hoverTimer);
      wrapper.classList.remove('hover-active');
    });
  });

  // 2) Slider fraction => default Advanced values
  function getAdvancedValuesFromSliderFraction(fraction) {
    const loops = Math.round(3 + (17 - 3) * fraction);
    const initRadius = Math.round(100 + (300 - 100) * fraction);

    // For radiusIncrement and aglIncrement, do an exponential approach:
    const radIncExpMin = 20;
    const radIncExpMax = 80;
    const radInc = Math.round(radIncExpMin * Math.pow(radIncExpMax / radIncExpMin, fraction));

    const incAGLExpMin = 10;
    const incAGLExpMax = 50;
    const incAGL = Math.round(incAGLExpMin * Math.pow(incAGLExpMax / incAGLExpMin, fraction));

    const startAGL = Math.round(100 + (300 - 100) * fraction);
    const startAlt = Math.round(50 + (150 - 50) * fraction);

    return {
      loops,
      initRadius,
      radInc,
      incAGL,
      startAGL,
      startAlt
    };
  }

  function getSliderFraction() {
    const sliderVal = parseFloat(document.getElementById("pathSizeSlider").value);
    return sliderVal / 100.0;
  }

  // 3) Handle mode switching
  window.setGeneratorMode = function(mode) {
    if (mode === 'standard') {
      modeToggle.setAttribute('data-mode', 'standard');
      standardModeUI.style.display = 'block';
      ranchModeUI.style.display = 'none';
      advancedModeUI.style.display = 'none';
      poiSection.style.display = 'none';
      addPoiButton.style.display = 'none';
    } else if (mode === 'ranch') {
      modeToggle.setAttribute('data-mode', 'ranch');
      standardModeUI.style.display = 'none';
      ranchModeUI.style.display = 'block';
      advancedModeUI.style.display = 'none';
      poiSection.style.display = 'none';
      addPoiButton.style.display = 'none';
    } else {
      // advanced
      modeToggle.setAttribute('data-mode', 'advanced');
      standardModeUI.style.display = 'none';
      ranchModeUI.style.display = 'none';
      advancedModeUI.style.display = 'block';
      poiSection.style.display = 'block';
      addPoiButton.style.display = 'inline-block';

      // If switching to advanced, dynamically set fields based on slider fraction
      const fraction = getSliderFraction();
      const advVals = getAdvancedValuesFromSliderFraction(fraction);
      document.getElementById("numLoops").value = advVals.loops;
      document.getElementById("initialRadius").value = advVals.initRadius;
      document.getElementById("radiusIncrement").value = advVals.radInc;
      document.getElementById("aglIncrement").value = advVals.incAGL;
      document.getElementById("initialAGL").value = advVals.startAGL;
      document.getElementById("startPointAltitude").value = advVals.startAlt;
    }
  };

  addPoiButton.addEventListener("click", addPoiRow);
  function addPoiRow() {
    poiCount++;
    const row = document.createElement('div');
    row.classList.add('poi-row');

    const poiLabel = document.createElement('span');
    poiLabel.classList.add('poi-row-title');
    poiLabel.textContent = `POI ${poiCount}`;
    row.appendChild(poiLabel);

    // POI gimbal tilt
    const poiAltitudeWrap = document.createElement('div');
    poiAltitudeWrap.classList.add('input-wrapper');
    poiAltitudeWrap.setAttribute('data-label', 'POI Gimbal Tilt (degrees)');
    const poiAltitudeInput = document.createElement('input');
    poiAltitudeInput.type = 'number';
    poiAltitudeInput.name = `poiAltitude${poiCount}`;
    poiAltitudeInput.placeholder = 'POI Gimbal Tilt (°)';
    poiAltitudeInput.step = 'any';
    const overlayAlt = document.createElement('div');
    overlayAlt.classList.add('hover-overlay');
    poiAltitudeWrap.appendChild(poiAltitudeInput);
    poiAltitudeWrap.appendChild(overlayAlt);
    row.appendChild(poiAltitudeWrap);

    // "From" and "To" fields in one row
    const loopRangeContainer = document.createElement('div');
    loopRangeContainer.classList.add('input-row');

    const loopFromWrap = document.createElement('div');
    loopFromWrap.classList.add('input-wrapper');
    loopFromWrap.setAttribute('data-label', 'From Loop');
    const loopFromInput = document.createElement('input');
    loopFromInput.type = 'number';
    loopFromInput.name = `poiLoopFrom${poiCount}`;
    loopFromInput.placeholder = 'From Loop';
    loopFromInput.min = '1';
    loopFromInput.step = '1';
    const overlayFrom = document.createElement('div');
    overlayFrom.classList.add('hover-overlay');
    loopFromWrap.appendChild(loopFromInput);
    loopFromWrap.appendChild(overlayFrom);

    const toLabel = document.createElement('span');
    toLabel.style.display = 'flex';
    toLabel.style.alignItems = 'center';
    toLabel.style.color = '#fff';
    toLabel.textContent = 'to';

    const loopToWrap = document.createElement('div');
    loopToWrap.classList.add('input-wrapper');
    loopToWrap.setAttribute('data-label', 'To Loop');
    const loopToInput = document.createElement('input');
    loopToInput.type = 'number';
    loopToInput.name = `poiLoopTo${poiCount}`;
    loopToInput.placeholder = 'To Loop';
    loopToInput.min = '1';
    loopToInput.step = '1';
    const overlayTo = document.createElement('div');
    overlayTo.classList.add('hover-overlay');
    loopToWrap.appendChild(loopToInput);
    loopToWrap.appendChild(overlayTo);

    loopRangeContainer.appendChild(loopFromWrap);
    loopRangeContainer.appendChild(toLabel);
    loopRangeContainer.appendChild(loopToWrap);
    row.appendChild(loopRangeContainer);

    const actions = document.createElement('div');
    actions.classList.add('poi-row-actions');
    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = 'Delete POI';
    deleteBtn.classList.add('delete-poi-button');
    deleteBtn.addEventListener('click', () => {
      row.remove();
    });
    actions.appendChild(deleteBtn);
    row.appendChild(actions);

    document.getElementById("poiSection").appendChild(row);

    // Re-bind the hover logic for these new inputs
    const newInputs = row.querySelectorAll('.input-wrapper');
    newInputs.forEach((wrapper) => {
      const inputElem = wrapper.querySelector('input');
      const overlay = wrapper.querySelector('.hover-overlay');
      const labelText = wrapper.getAttribute('data-label') || '';
      overlay.innerHTML = labelText;

      inputElem.addEventListener('mouseenter', () => {
        if (inputElem.value.trim() !== '') {
          hoverTimer = setTimeout(() => {
            wrapper.classList.add('hover-active');
          }, 450);
        }
      });
      inputElem.addEventListener('mouseleave', () => {
        clearTimeout(hoverTimer);
        wrapper.classList.remove('hover-active');
      });
      inputElem.addEventListener('focus', () => {
        clearTimeout(hoverTimer);
        wrapper.classList.remove('hover-active');
      });
    });
  }

  document.getElementById("coordinateForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    const generateBtn = document.getElementById("generateButton");
    const originalBtnText = generateBtn.textContent;

    // Show spinner
    generateBtn.disabled = true;
    generateBtn.innerHTML = `<div class="spinner"></div>`;

    const resultDiv = document.getElementById("result");
    const downloadMasterBtn = document.getElementById("downloadMasterBtn");
    const flightTimeDiv = document.getElementById("flightTime");
    const segmentDownloadsDiv = document.getElementById("segmentDownloads");
    const logDiv = document.getElementById("log");
    logDiv.innerHTML = '';
    resultDiv.innerHTML = '';

    // Decide which battery field to read from for standard/ranch/advanced:
    let batteryVal = document.getElementById("batteryCapacity").value.trim();
    if (modeToggle.getAttribute('data-mode') === 'advanced') {
      batteryVal = document.getElementById("batteryCapacityAdvanced").value.trim();
    }

    // Build the payload
    const payload = {
      title: document.getElementById("title").value.trim() || 'untitled',
      coordinates: document.getElementById("coordinates").value.trim(),
      takeoffCoordinates: document.getElementById("takeoffCoordinates").value.trim(),
      mode: modeToggle.getAttribute('data-mode'),
      sliderFraction: getSliderFraction(),
      minHeight: document.getElementById("minHeight").value.trim(),
      maxHeight: document.getElementById("maxHeight").value.trim(),
      batteryCapacity: batteryVal,
      numLoops: document.getElementById("numLoops").value.trim(),
      initialRadius: document.getElementById("initialRadius").value.trim(),
      radiusIncrement: document.getElementById("radiusIncrement").value.trim(),
      exponentialRadius: document.getElementById("exponentialRadius").checked,
      aglIncrement: document.getElementById("aglIncrement").value.trim(),
      exponentialAGL: document.getElementById("exponentialAGL").checked,
      initialAGL: document.getElementById("initialAGL").value.trim(),
      startPointAltitude: document.getElementById("startPointAltitude").value.trim(),

      // POI
      useGimbalTiltMode: !document.getElementById("poiModeToggle").checked,
      poiRows: []
    };

    // Ranch-specific
    if (modeToggle.getAttribute('data-mode') === 'ranch') {
      payload.minHeightRanch = document.getElementById("minHeightRanch").value.trim();
      payload.maxHeightRanch = document.getElementById("maxHeightRanch").value.trim();
      payload.batteryCapacityRanch = document.getElementById("batteryCapacityRanch").value.trim();
      payload.numBatteriesRanch = document.getElementById("numBatteriesRanch").value.trim();
      payload.initialRadiusRanch = document.getElementById("initialRadiusRanch").value.trim();
    }

    // Gather POI data
    const rows = document.getElementsByClassName('poi-row');
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      const altVal = row.querySelector(`input[name="poiAltitude${i+1}"]`).value.trim();
      const loopFrom = row.querySelector(`input[name="poiLoopFrom${i+1}"]`).value.trim();
      const loopTo = row.querySelector(`input[name="poiLoopTo${i+1}"]`).value.trim();
      payload.poiRows.push({
        altitude: altVal,
        loopFrom: loopFrom,
        loopTo: loopTo
      });
    }

    try {
      // *** CALL YOUR AWS LAMBDA ENDPOINT HERE ***
      const lambdaUrl = "https://7bidiow2t9.execute-api.us-west-2.amazonaws.com/prod/DronePathREST";
      const response = await fetch(lambdaUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Lambda request failed: ${response.status}`);
      }

      const rawData = await response.json();
      const data = typeof rawData.body === "string" ? JSON.parse(rawData.body) : rawData.body;

      if (data && data.logs) {
        data.logs.forEach(entry => {
          log(entry.title, entry.msg);
        });
      }
      if (data && data.error) {
        throw new Error(data.error);
      }
      if (data && data.elevationMsg) {
        resultDiv.innerHTML = data.elevationMsg;
      }
      if (typeof data.totalFlightTimeMinutes !== "undefined") {
        flightTimeDiv.style.display = "block";
        flightTimeDiv.innerHTML = `Estimated Total Flight Time: ${data.totalFlightTimeMinutes.toFixed(2)} minutes`;
      }
      if (data.masterWaypoints && data.masterWaypoints.length) {
        downloadMasterBtn.style.display = "inline-block";
        const titleSafe = sanitizeTitle(data.title || 'untitled');
        downloadMasterBtn.onclick = function() {
          downloadCSV(data.masterWaypoints, `${titleSafe}-master.csv`);
          log('Download:', `${titleSafe}-master.csv has been downloaded.`);
        };
      } else {
        downloadMasterBtn.style.display = "none";
      }
      if (data.segments && data.segments.length) {
        segmentDownloadsDiv.style.display = "block";
        segmentDownloadsDiv.innerHTML = `<p>Flight Segments (${data.segments.length}):</p>`;
        data.segments.forEach((segment, idx) => {
          const btn = document.createElement('button');
          btn.textContent = `Download Segment ${idx + 1}`;
          btn.style.marginRight = "5px";
          const titleSafe = sanitizeTitle(data.title || 'untitled');
          btn.onclick = () => {
            downloadCSV(segment, `${titleSafe}-segment-${idx + 1}.csv`);
            log('Download:', `${titleSafe}-segment-${idx + 1}.csv has been downloaded.`);
          };
          segmentDownloadsDiv.appendChild(btn);
        });
      } else {
        segmentDownloadsDiv.style.display = "none";
      }

    } catch (error) {
      resultDiv.innerHTML = `Error: ${error.message}`;
      log('Error:', error.message);
      downloadMasterBtn.style.display = "none";
      flightTimeDiv.style.display = "none";
      segmentDownloadsDiv.style.display = "none";
    } finally {
      generateBtn.innerHTML = originalBtnText;
      generateBtn.disabled = false;
    }
  });

  function log(title, msg) {
    const logDiv = document.getElementById("log");
    logDiv.innerHTML += `<strong>${title}</strong> ${msg}\n`;
  }

  function downloadCSV(waypoints, filename) {
    let csv = "latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval\n";
    waypoints.forEach((wp) => {
      csv += [
        wp.latitude,
        wp.longitude,
        parseFloat(wp.altitude || 0).toFixed(2),
        wp.heading,
        wp.curvesize,
        wp.rotationdir,
        wp.gimbalmode,
        wp.gimbalpitchangle,
        wp.altitudemode,
        wp.speed,
        wp.poi_latitude,
        wp.poi_longitude,
        wp.poi_altitude,
        wp.poi_altitudemode,
        wp.photo_timeinterval,
        wp.photo_distinterval
      ].join(",") + "\n";
    });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function sanitizeTitle(t) {
    return t.replace(/[^a-z0-9_\-]/gi, '_');
  }

  // ===== JS FOR TOOLTIP POSITIONING =====
  document.addEventListener('click', function(e) {
    const isIcon = e.target.matches('.info-pill-icon[data-tooltip-target]');  // Only match icons with tooltip targets
    const isTooltip = e.target.closest('.info-tooltip');
    const openTooltips = document.querySelectorAll('#dfpg-container .info-tooltip.active');

    // Close all tooltips if clicking outside
    if (!isIcon && !isTooltip) {
      openTooltips.forEach(tip => {
        if (tip && tip.classList) {
          tip.classList.remove('active');
          tip.style.display = 'none';
        }
      });
    }

    // Handle tooltip click
    if (isIcon) {
      e.preventDefault();
      e.stopPropagation(); // Prevent event from bubbling up
      const icon = e.target;
      const tooltipId = icon.getAttribute('data-tooltip-target');
      const tooltip = document.getElementById(tooltipId);

      if (tooltip && tooltip.classList) { // Only proceed if tooltip exists and has classList
        if (tooltip.classList.contains('active')) {
          tooltip.classList.remove('active');
          tooltip.style.display = 'none';
        } else {
          openTooltips.forEach(tip => {
            if (tip && tip.classList) {
              tip.classList.remove('active');
              tip.style.display = 'none';
            }
          });
          tooltip.classList.add('active');
          tooltip.style.display = 'block';

          // Positioning logic
          const container = document.querySelector('#dfpg-container .dfpg-container-inner');
          if (container) {
            const containerRect = container.getBoundingClientRect();
            const iconRect = icon.getBoundingClientRect();
            const top = (iconRect.bottom - containerRect.top) + 10;
            tooltip.style.top = top + 'px';

            tooltip.style.left = '50%';
            tooltip.style.transform = 'translateX(-50%)';

            // Adjust arrow positioning
            const tooltipRect = tooltip.getBoundingClientRect();
            const iconCenterX = iconRect.left + (iconRect.width / 2);
            const arrowX = iconCenterX - tooltipRect.left;
            tooltip.style.setProperty('--arrowOffset', arrowX + 'px');
          }
        }
      }
    }
  });
})();

// CHUNK #3: dronePhotoUploader.js
(function() {
  const propertyTitle   = document.getElementById('propertyTitle');
  const addressOfProp   = document.getElementById('addressOfProperty');
  const listingDesc     = document.getElementById('listingDescription');
  const uploadArea      = document.getElementById('uploadArea');
  const uploadPrompt    = document.getElementById('uploadPrompt');
  const fileInput       = document.getElementById('fileInput');
  const selectedFileDisplay = document.getElementById('selectedFileDisplay');
  const selectedFileName = document.getElementById('selectedFileName');
  const removeFileBtn   = document.getElementById('removeFileBtn');
  const emailField      = document.getElementById('emailField');
  const optionalNotes   = document.getElementById('optionalNotes');
  const uploadBtn       = document.getElementById('uploadBtn');
  const progressBar     = document.getElementById('progressBar');
  const progressBarFill = document.getElementById('progressBarFill');

  let selectedFile = null;  
  const MAX_FILE_SIZE = 7 * 1024 * 1024 * 1024; // 7GB
  const CHUNK_SIZE    = 24 * 1024 * 1024;       // 24MB

  // Required text fields
  const requiredFields = [propertyTitle, addressOfProp, listingDesc, emailField];
  requiredFields.forEach(field => {
    field.addEventListener('input', () => {
      if (field.value.trim()) {
        field.classList.remove('missing-field');
      }
    });
  });

  // Close icon => remove selected file
  removeFileBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = "";
    selectedFileDisplay.style.display = "none";
    uploadPrompt.style.display = "block";
    uploadArea.classList.remove('missing-field');
  });

  // Drag & drop
  uploadArea.addEventListener('click', () => fileInput.click());
  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
  });
  uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
  });
  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  });
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  });

  function validateAndSetFile(file) {
    if (
      file.type !== "application/x-zip-compressed" && 
      !file.name.toLowerCase().endsWith(".zip")
    ) {
      alert("Please upload a .zip file only.");
      fileInput.value = "";
      selectedFile = null;
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      alert("File size exceeds 5GB. Please upload a smaller .zip file.");
      fileInput.value = "";
      selectedFile = null;
      return;
    }
    selectedFile = file;

    // Hide the prompt
    uploadPrompt.style.display = "none";
    // Show file name + close icon
    selectedFileDisplay.style.display = "block";
    selectedFileName.textContent = file.name;
    // Remove highlight
    uploadArea.classList.remove('missing-field');
  }

  /************************************************
   * Endpoints for multipart in your backend
   ************************************************/
  const START_MULTIPART_ENDPOINT   = "https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/start-multipart-upload";
  const GET_PRESIGNED_PART_ENDPOINT= "https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/get-presigned-url";
  const COMPLETE_MULTIPART_ENDPOINT= "https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/complete-multipart-upload";
  const SAVE_SUBMISSION_ENDPOINT   = "https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/save-submission";

  async function saveSubmissionMetadata(objectKey) {
    const payload = {
      email: emailField.value.trim(),
      propertyTitle: propertyTitle.value.trim(),
      listingDescription: listingDesc.value.trim(),
      addressOfProperty: addressOfProp.value.trim(),
      optionalNotes: optionalNotes.value.trim(),
      objectKey: objectKey
    };

    const res = await fetch(SAVE_SUBMISSION_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error("Failed to save submission metadata");
    }
    return await res.json();
  }

  async function startMultipartUpload(fileName, fileType) {
    const payload = {
      propertyTitle: propertyTitle.value.trim(),
      addressOfProperty: addressOfProp.value.trim(),
      listingDescription: listingDesc.value.trim(),
      email: emailField.value.trim(),
      optionalNotes: optionalNotes.value.trim(),
      fileName: fileName,
      fileType: fileType
    };

    const res = await fetch(START_MULTIPART_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error("Failed to start multipart upload");
    }
    return await res.json();
  }

  async function getPresignedUrlForPart(uploadId, bucketName, objectKey, partNumber) {
    const payload = { uploadId, bucketName, objectKey, partNumber };
    const res = await fetch(GET_PRESIGNED_PART_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error("Failed to get presigned URL for part " + partNumber);
    }
    return await res.json();
  }

  async function completeMultipartUpload(uploadId, bucketName, objectKey, parts) {
    const payload = { uploadId, bucketName, objectKey, parts };
    const res = await fetch(COMPLETE_MULTIPART_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error("Failed to complete multipart upload");
    }
    return await res.json();
  }

  async function uploadFileInChunks(file) {
    const { uploadId, bucketName, objectKey } = await startMultipartUpload(file.name, file.type);
    console.log("Multipart upload started:", { uploadId, bucketName, objectKey });

    const totalSize   = file.size;
    let uploadedBytes = 0;
    let partNumber    = 1;
    const partsETags  = [];

    let offset = 0;
    while (offset < totalSize) {
      const chunk = file.slice(offset, offset + CHUNK_SIZE);
      const chunkSize = chunk.size;

      const { url } = await getPresignedUrlForPart(uploadId, bucketName, objectKey, partNumber);
      const eTag = await uploadPart(url, chunk, partNumber);

      partsETags.push({ ETag: eTag, PartNumber: partNumber });

      uploadedBytes += chunkSize;
      const percent = (uploadedBytes / totalSize) * 100;
      progressBarFill.style.width = percent + "%";
      console.log(`Uploaded part #${partNumber}: ${percent.toFixed(2)}% done`);

      offset += CHUNK_SIZE;
      partNumber++;
    }

    await completeMultipartUpload(uploadId, bucketName, objectKey, partsETags);
    console.log("Multipart upload completed!");
    return { objectKey };
  }

  function uploadPart(url, chunk, partNumber) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("PUT", url);

      xhr.upload.addEventListener("error", () => {
        reject(new Error("Network error uploading part #" + partNumber));
      });
      xhr.onload = () => {
        if (xhr.status === 200) {
          const eTag = xhr.getResponseHeader("ETag");
          if (!eTag) {
            return reject(new Error("No ETag found in upload response for part #" + partNumber));
          }
          resolve(eTag);
        } else {
          reject(new Error("Failed to upload part #" + partNumber + "; status: " + xhr.status));
        }
      };

      xhr.send(chunk);
    });
  }

  // Handle upload
  uploadBtn.addEventListener('click', async () => {
    let missing = false;
    requiredFields.forEach(field => {
      if (!field.value.trim()) {
        field.classList.add('missing-field');
        missing = true;
      }
    });
    if (!selectedFile) {
      uploadArea.classList.add('missing-field');
      missing = true;
    }
    if (missing) {
      return;
    }

    const originalBtnHTML = uploadBtn.innerHTML;
    uploadBtn.innerHTML = '<div class="spinner"></div>';
    uploadBtn.disabled = true;

    try {
      progressBar.style.display = 'block';
      progressBarFill.style.width = '0%';

      // Start chunked upload
      const result = await uploadFileInChunks(selectedFile);

      // Save to DynamoDB
      await saveSubmissionMetadata(result.objectKey);
      console.log("Submission metadata saved!");

      uploadBtn.innerHTML = 'Upload Complete!';
      alert("Upload completed!");
    } catch (err) {
      console.error("Multipart Upload error:", err.message);
      alert("Error uploading file (multipart): " + err.message);
    } finally {
      setTimeout(() => {
        uploadBtn.innerHTML = originalBtnHTML;
        uploadBtn.disabled = false;
        progressBar.style.display = 'none';
        progressBarFill.style.width = '0%';
      }, 1500);
    }
  });
})();

// Define the functions in the global scope first
function showAddPathPopup(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  console.log('showAddPathPopup called');
  const popup = document.getElementById('addPathPopup');
  console.log('popup element:', popup);
  if (popup) {
    popup.classList.remove('hidden');
    // Add event listener for clicking outside the popup
    setTimeout(() => {
      document.addEventListener('click', handleOutsideClick);
    }, 0);
    console.log('popup shown and click handler added');
  } else {
    console.error('Popup element not found');
  }
}

function hideAddPathPopup(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  const popup = document.getElementById('addPathPopup');
  if (popup) {
    popup.classList.add('hidden');
    const parsingResults = document.getElementById('parsingResults');
    const csvFileInput = document.getElementById('csvFileInput');
    if (parsingResults) parsingResults.classList.add('hidden');
    if (csvFileInput) csvFileInput.value = '';
    // Remove the outside click listener
    document.removeEventListener('click', handleOutsideClick);
  }
}

function handleOutsideClick(event) {
  const popup = document.getElementById('addPathPopup');
  const popupContent = document.querySelector('.popup-content');
  const closeIcon = document.querySelector('.close-icon');
  
  // Check if click is outside the popup content and not on the close icon
  if (popup && popupContent && !popupContent.contains(event.target) && event.target !== closeIcon) {
    hideAddPathPopup(event);
  }
}

function handleFileUpload(file) {
  console.log('handleFileUpload called with file:', file);
  
  // Add null check for file
  if (!file) {
    console.error('No file provided to handleFileUpload');
    return;
  }

  // Check file extension
  if (!file.name.toLowerCase().endsWith('.csv')) {
    console.error('Invalid file type:', file.name);
    alert('Please upload a CSV file');
    return;
  }
  
  const reader = new FileReader();
  
  reader.onload = function(e) {
    console.log('FileReader onload triggered');
    try {
      const csvData = e.target.result;
      console.log('CSV data first 100 chars:', csvData.substring(0, 100));
      analyzeFlightPath(csvData);
    } catch (error) {
      console.error('Error processing CSV data:', error);
      alert('Error processing CSV file: ' + error.message);
    }
  };
  
  reader.onerror = function(e) {
    console.error('FileReader error:', e.target.error);
    alert('Error reading file: ' + e.target.error);
  };
  
  console.log('Starting to read file as text');
  try {
    reader.readAsText(file);
  } catch (error) {
    console.error('Error starting file read:', error);
    alert('Error starting file read: ' + error.message);
  }
}

function analyzeFlightPath(csvData) {
  console.log('analyzeFlightPath called');
  
  if (!csvData) {
    console.error('No CSV data provided to analyzeFlightPath');
    return;
  }
  
  const lines = csvData.split('\n');
  console.log('Number of CSV lines:', lines.length);
  
  if (lines.length < 2) {
    console.error('Invalid CSV file format - not enough lines');
    alert('Invalid CSV file format');
    return;
  }
  
  // Parse CSV headers
  const headers = lines[0].split(',').map(h => h.trim());
  console.log('CSV headers:', headers);
  
  const waypoints = [];
  let validWaypoints = 0;
  
  // Parse waypoints
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;
    
    const values = lines[i].split(',').map(v => v.trim());
    if (values.length !== headers.length) {
      console.warn(`Skipping line ${i + 1}: incorrect number of values`);
      continue;
    }
    
    const waypoint = {};
    headers.forEach((header, index) => {
      waypoint[header] = values[index];
    });
    waypoints.push(waypoint);
    validWaypoints++;
  }
  
  console.log('Valid waypoints parsed:', validWaypoints);
  
  if (waypoints.length === 0) {
    console.error('No valid waypoints found in CSV');
    alert('No waypoints found in CSV file');
    return;
  }

  try {
    console.log('Detecting parameters from waypoints');
    const params = {
      mode: detectMode(waypoints),
      radiusIncrement: detectRadiusIncrement(waypoints),
      aglIncrement: detectAGLIncrement(waypoints),
      centerCoordinates: detectCenterCoordinates(waypoints)
    };
    
    console.log('Detected parameters:', params);
    displayDetectedParams(params);
  } catch (error) {
    console.error('Error detecting parameters:', error);
    alert('Error analyzing flight path: ' + error.message);
  }
}

function detectMode(waypoints) {
  // Check for patterns that indicate ranch mode
  const hasConsistentPOI = waypoints.every(wp => 
    wp.poi_longitude === waypoints[0].poi_longitude
  );
  
  const hasVaryingGimbal = waypoints.some(wp => 
    parseFloat(wp.gimbalpitchangle) !== parseFloat(waypoints[0].gimbalpitchangle)
  );
  
  if (hasConsistentPOI && hasVaryingGimbal) {
    return 'ranch';
  }
  
  // Check for standard vs advanced
  const hasPOIRows = waypoints.some(wp => wp.poi_altitude !== '0');
  return hasPOIRows ? 'advanced' : 'standard';
}

function detectRadiusIncrement(waypoints) {
  // Calculate distances from center to each waypoint
  const center = detectCenterCoordinates(waypoints);
  if (!center) return null;

  const radii = waypoints.map(wp => {
    const dx = parseFloat(wp.longitude) - parseFloat(center.longitude);
    const dy = parseFloat(wp.latitude) - parseFloat(center.latitude);
    return Math.sqrt(dx * dx + dy * dy);
  }).sort((a, b) => a - b);

  if (radii.length < 2) return null;
  
  const increments = [];
  for (let i = 1; i < radii.length; i++) {
    increments.push(radii[i] - radii[i-1]);
  }
  
  // Return the most common increment
  const incrementCounts = {};
  increments.forEach(inc => {
    incrementCounts[inc] = (incrementCounts[inc] || 0) + 1;
  });
  
  return Object.entries(incrementCounts)
    .sort((a, b) => b[1] - a[1])[0][0];
}

function detectCenterCoordinates(waypoints) {
  // Find the point that appears most frequently as POI
  const poiCounts = {};
  waypoints.forEach(wp => {
    if (wp.poi_latitude && wp.poi_longitude) {
      const key = `${wp.poi_latitude},${wp.poi_longitude}`;
      poiCounts[key] = (poiCounts[key] || 0) + 1;
    }
  });
  
  if (Object.keys(poiCounts).length === 0) {
    // If no POI coordinates, use the average of all waypoints
    const sum = waypoints.reduce((acc, wp) => ({
      latitude: acc.latitude + parseFloat(wp.latitude),
      longitude: acc.longitude + parseFloat(wp.longitude)
    }), { latitude: 0, longitude: 0 });
    
    return {
      latitude: sum.latitude / waypoints.length,
      longitude: sum.longitude / waypoints.length
    };
  }
  
  // Return the most frequent POI coordinates
  const mostFrequent = Object.entries(poiCounts)
    .sort((a, b) => b[1] - a[1])[0][0]
    .split(',');
    
  return {
    latitude: parseFloat(mostFrequent[0]),
    longitude: parseFloat(mostFrequent[1])
  };
}

function detectAGLIncrement(waypoints) {
  // Find unique altitudes and sort them
  const altitudes = Array.from(new Set(waypoints.map(wp => parseFloat(wp.altitude))))
    .sort((a, b) => a - b);
  
  if (altitudes.length < 2) return null;
  
  const increments = [];
  for (let i = 1; i < altitudes.length; i++) {
    increments.push(altitudes[i] - altitudes[i-1]);
  }
  
  // Return the most common increment
  const incrementCounts = {};
  increments.forEach(inc => {
    incrementCounts[inc] = (incrementCounts[inc] || 0) + 1;
  });
  
  return Object.entries(incrementCounts)
    .sort((a, b) => b[1] - a[1])[0][0];
}

function displayDetectedParams(params) {
  console.log('Displaying detected parameters');
  const parsingResults = document.getElementById('parsingResults');
  const detectedParams = document.getElementById('detectedParams');
  
  if (!parsingResults || !detectedParams) {
    console.error('Could not find parsingResults or detectedParams elements');
    return;
  }
  
  // Clear previous results
  detectedParams.innerHTML = '';
  
  // Display each detected parameter
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null) {
      const paramDiv = document.createElement('div');
      paramDiv.innerHTML = `<strong>${key}:</strong> <span>${value}</span>`;
      detectedParams.appendChild(paramDiv);
    }
  });
  
  parsingResults.classList.remove('hidden');
}

// Initialize everything when the DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM Content Loaded - Initializing popup functionality');
  
  // Initialize popup
  const popup = document.getElementById('addPathPopup');
  console.log('Found popup element:', popup);
  
  if (popup) {
    popup.classList.add('hidden');
    
    // Add event listener for the add path button
    const addPathButton = document.querySelector('[data-action="show-add-path-popup"]');
    if (addPathButton) {
      console.log('Found add path button');
      addPathButton.addEventListener('click', function(event) {
        event.preventDefault();
        event.stopPropagation();
        showAddPathPopup(event);
      });
    } else {
      console.error('Add path button not found');
    }
    
    // Initialize upload area
    const uploadArea = document.getElementById('csvUploadArea');
    const fileInput = document.getElementById('csvFileInput');
    
    if (uploadArea && fileInput) {
      console.log('Setting up file upload handlers');
      // Click to upload
      uploadArea.addEventListener('click', (e) => {
        console.log('Upload area clicked');
        e.stopPropagation();
        fileInput.click();
      });
      
      // Drag and drop
      uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.4)';
      });
      
      uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.2)';
      });
      
      uploadArea.addEventListener('drop', (e) => {
        console.log('File dropped');
        e.preventDefault();
        e.stopPropagation();
        uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.2)';
        if (e.dataTransfer.files.length) {
          handleFileUpload(e.dataTransfer.files[0]);
        }
      });
      
      // File input change
      fileInput.addEventListener('change', (e) => {
        console.log('File input changed');
        e.stopPropagation();
        if (e.target.files.length) {
          handleFileUpload(e.target.files[0]);
        }
      });
    } else {
      console.error('Upload area or file input not found');
    }
  } else {
    console.error('Popup element not found');
  }
});

// Make functions globally available
window.showAddPathPopup = showAddPathPopup;
window.hideAddPathPopup = hideAddPathPopup;
window.handleFileUpload = handleFileUpload;
window.analyzeFlightPath = analyzeFlightPath;
window.detectMode = detectMode;
window.detectRadiusIncrement = detectRadiusIncrement;
window.detectAGLIncrement = detectAGLIncrement;
window.detectCenterCoordinates = detectCenterCoordinates;
window.displayDetectedParams = displayDetectedParams;

// API Endpoints
const API_ENDPOINTS = {
    DRONE_PATH: "https://7bidiow2t9.execute-api.us-west-2.amazonaws.com/prod/DronePathREST",
    START_UPLOAD: "https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/start-multipart-upload",
    GET_PRESIGNED_URL: "https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/get-presigned-url",
    COMPLETE_UPLOAD: "https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/complete-multipart-upload",
    SAVE_SUBMISSION: "https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/save-submission"
};

async function saveSubmissionMetadata(objectKey) {
    const email = document.getElementById('email').value;
    const propertyTitle = document.getElementById('propertyTitle').value;
    const listingDescription = document.getElementById('listingDescription').value;
    const addressOfProperty = document.getElementById('addressOfProperty').value;
    const optionalNotes = document.getElementById('optionalNotes').value;

    const response = await fetch(API_ENDPOINTS.SAVE_SUBMISSION, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email,
            propertyTitle,
            listingDescription,
            addressOfProperty,
            optionalNotes,
            objectKey
        })
    });

    if (!response.ok) {
        throw new Error(`Failed to save submission metadata: ${response.status}`);
    }

    return response.json();
}

async function startMultipartUpload(fileName, fileType) {
    const response = await fetch(API_ENDPOINTS.START_UPLOAD, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileName, fileType })
    });

    if (!response.ok) {
        throw new Error(`Failed to start multipart upload: ${response.status}`);
    }

    return response.json();
}

async function getPresignedUrlForPart(uploadId, bucketName, objectKey, partNumber) {
    const response = await fetch(API_ENDPOINTS.GET_PRESIGNED_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uploadId, bucketName, objectKey, partNumber })
    });

    if (!response.ok) {
        throw new Error(`Failed to get presigned URL: ${response.status}`);
    }

    return response.json();
}

async function completeMultipartUpload(uploadId, bucketName, objectKey, parts) {
    const response = await fetch(API_ENDPOINTS.COMPLETE_UPLOAD, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uploadId, bucketName, objectKey, parts })
    });

    if (!response.ok) {
        throw new Error(`Failed to complete multipart upload: ${response.status}`);
    }

    return response.json();
}

// Update the drone path generation API call
async function generateDronePath(payload) {
    try {
        const response = await fetch(API_ENDPOINTS.DRONE_PATH, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Lambda request failed: ${response.status}`);
        }

        const rawData = await response.json();
        const data = typeof rawData.body === "string" ? JSON.parse(rawData.body) : rawData.body;

        if (data && data.logs) {
            data.logs.forEach(entry => {
                log(entry.title, entry.msg);
            });
        }
        if (data && data.error) {
            throw new Error(data.error);
        }
        if (data && data.elevationMsg) {
            resultDiv.innerHTML = data.elevationMsg;
        }
        if (typeof data.totalFlightTimeMinutes !== "undefined") {
            flightTimeDiv.style.display = "block";
            flightTimeDiv.innerHTML = `Estimated Total Flight Time: ${data.totalFlightTimeMinutes.toFixed(2)} minutes`;
        }

        return data;
    } catch (error) {
        console.error('Error generating drone path:', error);
        throw error;
    }
}