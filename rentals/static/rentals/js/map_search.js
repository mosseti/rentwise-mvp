let rentMap;
let markers = [];
let activePlace = null;
let activePlaceMarker = null;
let userMarker = null;
let suggestionTimer = null;

function shillings(value){ return 'KSh ' + Number(value).toLocaleString(); }

function setStatus(text, tone){
  const el = document.getElementById('search-status');
  el.textContent = text;
  el.className = 'search-status ' + (tone || 'muted');
}

function clearMarkers(){
  markers.forEach(marker => rentMap.removeLayer(marker));
  markers = [];
}

function buildParams(){
  const params = new URLSearchParams();
  const area = document.getElementById('area-filter').value;
  const unit = document.getElementById('unit-filter').value;
  const rent = document.getElementById('rent-filter').value;
  const q = document.getElementById('query-filter').value.trim();
  const radius = document.getElementById('radius-filter').value;
  if(area) params.append('area', area);
  if(unit) params.append('unit_type', unit);
  if(rent) params.append('max_rent', rent);
  if(q) params.append('q', q);
  if(activePlace){
    params.append('lat', activePlace.lat);
    params.append('lng', activePlace.lng);
    params.append('radius_km', radius || '5');
  }
  return params;
}

function renderEmpty(resultBox, data){
  resultBox.innerHTML = `
    <div class="empty-search-card">
      <h3>No Verified Available Units Found Here</h3>
      <p>${data.message || 'No matching buildings were found. Try a nearby estate, increase the search radius, or walk around the area and ask caretakers directly.'}</p>
      <div class="actions">
        <button class="btn small" type="button" id="widen-search">Increase Radius</button>
        <button class="btn small" type="button" id="try-again">Search Another Area</button>
      </div>
    </div>`;
  const widen = document.getElementById('widen-search');
  const radiusSelect = document.getElementById('radius-filter');
  if(widen){
    widen.addEventListener('click', () => {
      const options = Array.from(radiusSelect.options).map(o => Number(o.value));
      const current = Number(radiusSelect.value);
      const next = options.find(v => v > current);
      if(next){ radiusSelect.value = String(next); loadMarkers(); }
    });
  }
  const again = document.getElementById('try-again');
  if(again){ again.addEventListener('click', () => document.getElementById('place-search').focus()); }
}

async function loadMarkers(){
  const res = await fetch('/api/buildings/?' + buildParams().toString());
  const data = await res.json();
  clearMarkers();
  const resultBox = document.getElementById('map-results');
  resultBox.innerHTML = '';
  setStatus(data.message || 'Showing available verified listings.', data.buildings.length ? 'success' : 'warning');

  const bounds = [];
  if(activePlace){ bounds.push([activePlace.lat, activePlace.lng]); }

  data.buildings.forEach(b => {
    const position = [b.lat, b.lng];
    bounds.push(position);
    const distanceText = b.distance_km !== null && b.distance_km !== undefined ? `<br>${b.distance_km} km from searched point` : '';
    const marker = L.marker(position).addTo(rentMap);
    marker.bindPopup(`
      <div class="map-popup">
        <strong>${b.name}</strong><br>
        ${b.area} ${b.landmark ? '· ' + b.landmark : ''}<br>
        From ${shillings(b.price_from)}<br>
        ${b.available_count} units available${distanceText}<br>
        <a href="${b.url}">View units</a>
      </div>`);
    markers.push(marker);

    const item = document.createElement('div');
    item.className = 'map-result-card ' + (b.match_group === 'nearby' ? 'surrounding' : 'exact');
    const distance = b.distance_km !== null && b.distance_km !== undefined ? `<p class="muted">${b.distance_km} km Away · ${b.match_group === 'nearby' ? 'Surrounding Area' : 'Close Match'}</p>` : '';
    item.innerHTML = `<h3>${b.name}</h3><p>${b.area} · ${b.landmark || ''}</p>${distance}<p><strong>From ${shillings(b.price_from)}</strong> · ${b.available_count} Available</p><a href="${b.url}">View Units</a>`;
    item.addEventListener('click', () => {
      rentMap.setView(position, 17);
      marker.openPopup();
    });
    resultBox.appendChild(item);
  });

  if(data.buildings.length){
    rentMap.fitBounds(bounds, {padding: [35, 35], maxZoom: 17});
  } else {
    renderEmpty(resultBox, data);
    if(activePlace){ rentMap.setView([activePlace.lat, activePlace.lng], 15); }
  }
}

function setActivePlace(name, lat, lng){
  activePlace = { name, lat, lng };
  if(activePlaceMarker){ rentMap.removeLayer(activePlaceMarker); }
  activePlaceMarker = L.marker([lat, lng]).addTo(rentMap).bindPopup(name);
  rentMap.setView([lat, lng], 15);
  setStatus('Searching verified listings near ' + name + '...', 'muted');
  loadMarkers();
}

async function searchTypedPlace(){
  const q = document.getElementById('place-search').value.trim();
  if(!q) return;
  setStatus('Finding ' + q + '...', 'muted');
  try{
    const res = await fetch('/api/geocode/?q=' + encodeURIComponent(q));
    const data = await res.json();
    if(!res.ok || !data.result){
      setStatus(data.error || 'Place not found. Try another Nairobi landmark or estate.', 'warning');
      return;
    }
    document.getElementById('place-search').value = data.result.label;
    setActivePlace(data.result.label, data.result.lat, data.result.lng);
  } catch(error){
    setStatus('Could not search the place right now. Check your internet connection and try again.', 'warning');
  }
}

async function updateSuggestions(){
  const input = document.getElementById('place-search');
  const list = document.getElementById('place-suggestions');
  const q = input.value.trim();
  if(q.length < 2){ list.innerHTML = ''; return; }
  try{
    const res = await fetch('/api/place-suggestions/?q=' + encodeURIComponent(q));
    const data = await res.json();
    list.innerHTML = '';
    (data.results || []).forEach(item => {
      const option = document.createElement('option');
      option.value = item.label;
      option.dataset.lat = item.lat;
      option.dataset.lng = item.lng;
      list.appendChild(option);
    });
  } catch(error){
    // Suggestions are helpful but not required. Keep typing/search working if this fails.
  }
}

function createMap(){
  rentMap = L.map('rent-map', {scrollWheelZoom: true}).setView([-1.286389, 36.817223], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(rentMap);
}

document.addEventListener('DOMContentLoaded', () => {
  createMap();
  const placeInput = document.getElementById('place-search');
  document.getElementById('apply-filters').addEventListener('click', loadMarkers);
  ['area-filter','unit-filter','radius-filter'].forEach(id => document.getElementById(id).addEventListener('change', loadMarkers));
  document.getElementById('rent-filter').addEventListener('keydown', event => { if(event.key === 'Enter') loadMarkers(); });
  document.getElementById('query-filter').addEventListener('keydown', event => { if(event.key === 'Enter') loadMarkers(); });
  document.getElementById('go-place').addEventListener('click', searchTypedPlace);
  placeInput.addEventListener('keydown', event => { if(event.key === 'Enter'){ event.preventDefault(); searchTypedPlace(); } });
  placeInput.addEventListener('input', () => {
    clearTimeout(suggestionTimer);
    suggestionTimer = setTimeout(updateSuggestions, 650);
  });

  document.getElementById('clear-place').addEventListener('click', () => {
    activePlace = null;
    placeInput.value = '';
    if(activePlaceMarker){ rentMap.removeLayer(activePlaceMarker); activePlaceMarker = null; }
    rentMap.setView([-1.286389, 36.817223], 12);
    loadMarkers();
  });

  document.getElementById('use-location').addEventListener('click', () => {
    if(!navigator.geolocation){ alert('Location is not available on this browser.'); return; }
    navigator.geolocation.getCurrentPosition(pos => {
      const position = [pos.coords.latitude, pos.coords.longitude];
      if(userMarker){ userMarker.setLatLng(position); }
      else { userMarker = L.marker(position).addTo(rentMap).bindPopup('You are here'); }
      document.getElementById('place-search').value = 'My Current Location';
      activePlace = {name: 'My Current Location', lat: position[0], lng: position[1]};
      rentMap.setView(position, 15);
      userMarker.openPopup();
      loadMarkers();
    }, () => alert('Allow location access to use this feature.'));
  });

  const initialPlace = new URLSearchParams(window.location.search).get('place');
  if(initialPlace){
    placeInput.value = initialPlace;
    searchTypedPlace();
  } else {
    loadMarkers();
  }
});
