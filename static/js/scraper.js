/**
 * scraper.js - PRODUCTION VERSION with CANCEL functionality
 */

let pollTimer = null;
let debugLines = [];
let currentJobId = null;

// ── Debug log ─────────────────────────────────────────────────────────────────

function log(msg) {
  const ts = new Date().toLocaleTimeString();
  debugLines.push(`[${ts}] ${msg}`);
  if (debugLines.length > 300) debugLines.shift();
  const el = document.getElementById('debugLog');
  el.textContent = debugLines.join('\n');
  el.scrollTop = el.scrollHeight;
}

function toggleDebug() {
  const el = document.getElementById('debugLog');
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

// ── Topbar status dot ─────────────────────────────────────────────────────────

function setStatus(state, text) {
  const dot = document.getElementById('statusDot');
  const span = document.getElementById('statusText');
  dot.className = 'status-dot' + (state ? ' ' + state : '');
  span.textContent = text;
}

// ── Submit ────────────────────────────────────────────────────────────────────

document.getElementById('submitBtn').addEventListener('click', async function () {
  const city = document.getElementById('city').value;
  const areas = collectAreas();
  const filterSets = collectFilterSets();
  const maxProps = parseInt(document.getElementById('max_properties').value) || 10;

  if (!city) {
    showError('Please select a city.');
    return;
  }
  if (!areas.length) {
    showError('Please select at least one area.');
    return;
  }
  if (!filterSets.length) {
    showError('Please add at least one filter set.');
    return;
  }

  log(`Submit: city=${city} areas=${areas.length} filters=${filterSets.length} max=${maxProps}`);

  document.getElementById('submitBtn').disabled = true;
  setStatus('active', 'running');

  // Reset and show progress overlay
  document.getElementById('progressOverlay').classList.add('active');
  document.getElementById('cancelBtn').style.display = 'block'; // Show cancel button in popup
  document.getElementById('progFill').style.width = '0%';
  document.getElementById('progPct').textContent = '0%';
  document.getElementById('pmTitle').textContent = 'Starting scraper…';
  document.getElementById('pmSub').textContent = '';
  document.getElementById('pmFilter').textContent = '—';
  document.getElementById('pmArea').textContent = '—';

  try {
    const resp = await fetch('/start_scraping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        city,
        areas,
        filter_sets: filterSets,
        max_properties: maxProps,
      }),
    });
    const data = await resp.json();

    if (data.success) {
      currentJobId = data.job_id;
      log(`Job started: ${currentJobId}`);
      log('Polling every 1.5s');
      pollTimer = setInterval(pollStatus, 1500);
    } else {
      endError(data.error || 'Failed to start scraping');
    }
  } catch (e) {
    endError('Network error: ' + e.message);
  }
});

// ── Cancel ────────────────────────────────────────────────────────────────────

document.getElementById('cancelBtn').addEventListener('click', async function () {
  if (!currentJobId) return;
  
  if (!confirm('Are you sure you want to cancel this scrape?')) return;
  
  log(`Cancelling job: ${currentJobId}`);
  
  try {
    const resp = await fetch('/cancel_job', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: currentJobId }),
    });
    const data = await resp.json();
    
    if (data.success) {
      log('Job cancelled successfully');
      clearInterval(pollTimer);
      document.getElementById('progressOverlay').classList.remove('active');
      document.getElementById('cancelBtn').style.display = 'none';
      document.getElementById('submitBtn').disabled = false;
      setStatus('', 'idle');
      showError('Scrape cancelled by user');
    } else {
      showError('Failed to cancel: ' + (data.error || 'Unknown error'));
    }
  } catch (e) {
    showError('Cancel error: ' + e.message);
  }
});

// ── Polling ───────────────────────────────────────────────────────────────────

async function pollStatus() {
  if (!currentJobId) return;

  try {
    const resp = await fetch(`/status?job_id=${currentJobId}`);
    const d = await resp.json();

    if (d.state === 'PENDING') {
      document.getElementById('pmTitle').textContent = 'Waiting in queue...';
      document.getElementById('pmSub').textContent = d.status || '';

    } else if (d.state === 'PROGRESS' || d.running) {
      const pct = d.total > 0
        ? Math.min(99, (d.progress / d.total * 100)).toFixed(1)
        : 0;

      document.getElementById('progFill').style.width = pct + '%';
      document.getElementById('progPct').textContent = pct + '%';
      document.getElementById('pmTitle').textContent = d.status || `${d.progress} properties scraped`;
      document.getElementById('pmSub').textContent = '';
      document.getElementById('pmFilter').textContent = d.current_filter || '—';
      document.getElementById('pmArea').textContent = d.current_area || '—';

    } else if (d.state === 'SUCCESS' || (!d.running && d.results)) {
      clearInterval(pollTimer);
      document.getElementById('progressOverlay').classList.remove('active');
      document.getElementById('cancelBtn').style.display = 'none';
      document.getElementById('submitBtn').disabled = false;

      if (d.results && d.results.length > 0) {
        showResults(d);
        setStatus('', 'idle');
        log(`Done — ${d.results.length} properties`);
      } else {
        endError(d.error || 'No properties found. Try broader filters.');
        setStatus('error', 'no results');
      }

    } else if (d.state === 'FAILURE' || d.error) {
      clearInterval(pollTimer);
      endError(d.error || 'Scraping failed');
      log('ERROR: ' + (d.error || 'Unknown error'));
    }
  } catch (e) {
    log('Poll error: ' + e.message);
  }
}

// ── Results overlay ───────────────────────────────────────────────────────────

function showResults(d) {
  const total = d.results.length;
  const withPrice = d.results.filter(r => r.price).length;
  const areas = new Set(d.results.map(r => r.search_area).filter(Boolean)).size;

  document.getElementById('rmSub').textContent =
    `${total} properties across ${areas} area${areas !== 1 ? 's' : ''}`;

  document.getElementById('resStats').innerHTML = `
    <div class="stat-box">
      <div class="stat-num">${total}</div>
      <div class="stat-lbl">Properties</div>
    </div>
    <div class="stat-box">
      <div class="stat-num">${withPrice}</div>
      <div class="stat-lbl">With price</div>
    </div>
    <div class="stat-box">
      <div class="stat-num">${areas}</div>
      <div class="stat-lbl">Areas</div>
    </div>`;

  document.querySelector('a[href="/download/excel"]').href = `/download/excel?job_id=${currentJobId}`;
  document.querySelector('a[href="/download/json"]').href = `/download/json?job_id=${currentJobId}`;

  document.getElementById('progFill').style.width = '100%';
  document.getElementById('resultsOverlay').classList.add('active');
  setStatus('', 'idle');
}

function closeResults() {
  document.getElementById('resultsOverlay').classList.remove('active');
}

// ── Error handling ────────────────────────────────────────────────────────────

function endError(msg) {
  document.getElementById('progressOverlay').classList.remove('active');
  document.getElementById('cancelBtn').style.display = 'none';
  document.getElementById('submitBtn').disabled = false;
  setStatus('error', 'error');
  showError(msg);
  if (pollTimer) clearInterval(pollTimer);
}

function showError(msg) {
  const toast = document.getElementById('errorToast');
  toast.textContent = msg;
  toast.classList.add('active');
  setTimeout(() => toast.classList.remove('active'), 5000);
}