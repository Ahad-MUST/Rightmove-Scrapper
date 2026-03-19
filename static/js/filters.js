/**
 * filters.js
 * Manages filter set cards: creation, removal, pill helpers,
 * data collection, and the status-bar counters.
 */

let filterCount = 0;

// ── Status bar ────────────────────────────────────────────────────────────────

function updateStatusBar() {
  const allCb   = document.getElementById('area-all');
  const checked = document.querySelectorAll('.area-cb:checked').length;
  const areas   = allCb && allCb.checked ? '∞' : checked;

  document.getElementById('sbAreas').textContent   = areas;
  document.getElementById('sbFilters').textContent =
    document.querySelectorAll('.filter-card').length;
  document.getElementById('sbMax').textContent =
    document.getElementById('max_properties').value;
}

document.getElementById('max_properties').addEventListener('change', updateStatusBar);

// ── Pill helper ───────────────────────────────────────────────────────────────

/**
 * Build the HTML string for a single pill checkbox.
 * Visual state is driven by CSS :has(input:checked) — no JS toggling needed.
 *
 * @param {string} cls       - CSS class for the hidden input (used by collectFilterSets)
 * @param {string} value     - checkbox value sent to the backend
 * @param {string} label     - visible text
 * @param {string} [extraCls] - optional extra class on the <label> (e.g. 'dont-pill')
 */
function makePill(cls, value, label, extraCls, checked) {
  return `<label class="pill ${extraCls || ''}">
    <input type="checkbox" class="${cls}" value="${value}"${checked ? ' checked' : ''}>${label}
  </label>`;
}

// ── Filter set lifecycle ──────────────────────────────────────────────────────

function addFilterSet() {
  filterCount++;
  const idx = filterCount;

  // Hide the empty-state placeholder
  const emptyState = document.getElementById('emptyState');
  if (emptyState) emptyState.style.display = 'none';

  const card = document.createElement('div');
  card.className = 'filter-card';
  card.id = `fs-${idx}`;

  card.innerHTML = `
    <div class="filter-card-head">
      <div class="fc-left">
        <span class="fc-num">#${idx}</span>
        <span class="fc-title">Filter set ${idx}</span>
      </div>
      <button class="btn-remove" onclick="removeFilterSet(${idx})">Remove</button>
    </div>

    <div class="filter-card-body">

      <div class="fc-field">
        <label>Min price (£/mo)</label>
        <input type="number" class="fs-min-price" placeholder="e.g. 800" step="50" min="0">
      </div>
      <div class="fc-field">
        <label>Max price (£/mo)</label>
        <input type="number" class="fs-max-price" placeholder="e.g. 2000" step="50" min="0">
      </div>

      <div class="fc-field">
        <label>Min bedrooms</label>
        <select class="fs-min-beds">
          <option value="any">Any</option>
          <option value="0">Studio</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
          <option value="5+">5+</option>
        </select>
      </div>
      <div class="fc-field">
        <label>Max bedrooms</label>
        <select class="fs-max-beds">
          <option value="any">Any</option>
          <option value="0">Studio</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
          <option value="5+">5+</option>
        </select>
      </div>

      <div class="fc-field full">
        <label>Furnished</label>
        <div class="pill-group">
          ${makePill('fs-furn', 'furnished',     'Furnished')}
          ${makePill('fs-furn', 'partFurnished', 'Part-furnished')}
          ${makePill('fs-furn', 'unfurnished',   'Unfurnished')}
        </div>
      </div>

      <div class="fc-field full">
        <label>
          Property type
          <span style="color:var(--text3);font-size:.65rem;">(blank = all)</span>
        </label>
        <div class="pill-group">
          ${makePill('fs-pt', 'detached',      'Detached',      '', true)}
          ${makePill('fs-pt', 'semi-detached', 'Semi-detached', '', true)}
          ${makePill('fs-pt', 'terraced',      'Terraced',      '', true)}
          ${makePill('fs-pt', 'flat',          'Flat',          '', true)}
          ${makePill('fs-pt', 'bungalow',      'Bungalow',      '', true)}
          ${makePill('fs-pt', 'land',          'Land')}
          ${makePill('fs-pt', 'park-home',     'Park home')}
          ${makePill('fs-pt', 'student-halls', 'Student halls')}
        </div>
      </div>

      <div class="fc-field full">
        <label>Don't show</label>
        <div class="pill-group">
          ${makePill('fs-dont-show', 'houseShare',  'House share',           'dont-pill', true)}
          ${makePill('fs-dont-show', 'retirement',  'Retirement home',       'dont-pill', true)}
          ${makePill('fs-dont-show', 'student',     'Student accommodation', 'dont-pill', true)}
        </div>
      </div>

    </div>`;

  document.getElementById('filterSets').appendChild(card);
  updateStatusBar();
}

function removeFilterSet(idx) {
  const el = document.getElementById(`fs-${idx}`);
  if (el) el.remove();

  // Show empty state again if no filter cards remain
  if (!document.querySelectorAll('.filter-card').length) {
    document.getElementById('emptyState').style.display = 'flex';
  }
  updateStatusBar();
}

document.getElementById('addFilterBtn').addEventListener('click', addFilterSet);

// Render one filter set on page load so the user has something to start with
addFilterSet();

// ── Data collection ───────────────────────────────────────────────────────────

/** Collect all filter-set payloads to send to /start_scraping. */
function collectFilterSets() {
  return Array.from(document.querySelectorAll('.filter-card')).map(div => ({
    min_price:      div.querySelector('.fs-min-price').value || null,
    max_price:      div.querySelector('.fs-max-price').value || null,
    bedrooms:       div.querySelector('.fs-min-beds').value,
    max_bedrooms:   div.querySelector('.fs-max-beds').value,
    furnished:      Array.from(div.querySelectorAll('.fs-furn:checked')).map(c => c.value),
    property_types: Array.from(div.querySelectorAll('.fs-pt:checked')).map(c => c.value),
    dont_show:      Array.from(div.querySelectorAll('.fs-dont-show:checked')).map(c => c.value),
  }));
}