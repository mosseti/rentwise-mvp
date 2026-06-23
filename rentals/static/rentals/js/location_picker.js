let pickerMap;
let pickerMarker;

function readStart(){
  const latInput = document.getElementById('id_latitude');
  const lngInput = document.getElementById('id_longitude');
  return [parseFloat(latInput.value || '-1.286389'), parseFloat(lngInput.value || '36.817223')];
}

function setCoords(position){
  document.getElementById('id_latitude').value = position[0].toFixed(6);
  document.getElementById('id_longitude').value = position[1].toFixed(6);
  pickerMarker.setLatLng(position);
}

document.addEventListener('DOMContentLoaded', () => {
  const mapEl = document.getElementById('pick-map');
  if(!mapEl) return;
  const start = readStart();
  pickerMap = L.map(mapEl).setView(start, 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(pickerMap);
  pickerMarker = L.marker(start, {draggable: true}).addTo(pickerMap).bindPopup('Building location');

  pickerMap.on('click', e => setCoords([e.latlng.lat, e.latlng.lng]));
  pickerMarker.on('dragend', e => {
    const ll = e.target.getLatLng();
    setCoords([ll.lat, ll.lng]);
  });

  document.getElementById('pick-current').addEventListener('click', () => {
    if(!navigator.geolocation){ alert('Location is not supported.'); return; }
    navigator.geolocation.getCurrentPosition(pos => {
      const position = [pos.coords.latitude, pos.coords.longitude];
      pickerMap.setView(position, 17);
      setCoords(position);
    }, () => alert('Allow location access, then try again.'));
  });
});
