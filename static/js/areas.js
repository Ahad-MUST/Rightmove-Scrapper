/**
 * areas.js
 * Handles city selection, area list rendering, select-all / clear,
 * and the selected-count badge.
 */

/* CITY_AREAS is injected by the Jinja template before this script runs. */

document.getElementById('city').addEventListener('change', function () {
  loadAreas(this.value);
});

function loadAreas(city) {
  const container = document.getElementById('areaContainer');
  container.innerHTML = '';

  if (!city) {
    updateBadge();
    updateStatusBar();
    return;
  }

  const cityData = CITY_AREAS[city];
  if (!cityData) {
    container.innerHTML =
      '<div style="padding:20px 8px;color:var(--text3);font-size:.8rem;">No areas found.</div>';
    return;
  }

  // "Entire city" option
  const allLbl = document.createElement('label');
  allLbl.className = 'area-item all-item';
  allLbl.innerHTML = `
    <input type="checkbox" id="area-all" value="all">
    <span class="check-box"></span>
    <span>Entire city</span>`;
  container.appendChild(allLbl);

  let areaCount = 0;
  const zones = cityData.zones || {};

  Object.entries(zones).forEach(([zoneName, zoneValue]) => {
    const areas = Array.isArray(zoneValue) ? zoneValue : (zoneValue.areas || []);
    if (!areas.length) return;

    const hdr = document.createElement('div');
    hdr.className   = 'zone-label';
    hdr.textContent = zoneName;
    container.appendChild(hdr);

    areas.forEach(area => {
      if (!area || typeof area !== 'object') return;
      const slug = area.url_slug || area.id || '';
      const name = area.name || slug;
      if (!slug) return;

      const lbl = document.createElement('label');
      lbl.className = 'area-item';
      lbl.innerHTML = `
        <input type="checkbox" class="area-cb" value="${slug}">
        <span class="check-box"></span>
        <span>${name}</span>`;
      container.appendChild(lbl);
      areaCount++;
    });
  });

  log(`Loaded ${areaCount} areas for ${city}`);

  // Wire up mutual-exclusion logic between "all" and individual areas
  const allCb = document.getElementById('area-all');

  allCb.addEventListener('change', function () {
    if (this.checked) {
      document.querySelectorAll('.area-cb').forEach(c => (c.checked = false));
    }
    updateBadge();
    updateStatusBar();
  });

  document.querySelectorAll('.area-cb').forEach(cb => {
    cb.addEventListener('change', function () {
      if (this.checked && allCb) allCb.checked = false;
      updateBadge();
      updateStatusBar();
    });
  });

  updateBadge();
  updateStatusBar();
}

document.getElementById('selectAllBtn').addEventListener('click', function () {
  const allCb = document.getElementById('area-all');
  if (allCb) allCb.checked = false;
  document.querySelectorAll('.area-cb').forEach(cb => (cb.checked = true));
  updateBadge();
  updateStatusBar();
});

document.getElementById('clearAllBtn').addEventListener('click', function () {
  const allCb = document.getElementById('area-all');
  if (allCb) allCb.checked = false;
  document.querySelectorAll('.area-cb').forEach(cb => (cb.checked = false));
  updateBadge();
  updateStatusBar();
});

function updateBadge() {
  const allCb   = document.getElementById('area-all');
  const checked = document.querySelectorAll('.area-cb:checked').length;
  const badge   = document.getElementById('selBadge');

  if (allCb && allCb.checked) {
    badge.innerHTML = 'Selected: <span>entire city</span>';
  } else if (checked > 0) {
    badge.innerHTML = `Selected: <span>${checked} area${checked > 1 ? 's' : ''}</span>`;
  } else {
    badge.textContent = 'No areas selected';
  }
}

/** Collect currently selected area slugs for the submit payload. */
function collectAreas() {
  const allCb = document.getElementById('area-all');
  if (allCb && allCb.checked) return ['all'];
  return Array.from(document.querySelectorAll('.area-cb:checked')).map(c => c.value);
}
