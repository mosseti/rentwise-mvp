document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('detail-map');
  if(!el) return;
  const position = [parseFloat(el.dataset.lat), parseFloat(el.dataset.lng)];
  const map = L.map(el).setView(position, 17);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  L.marker(position).addTo(map).bindPopup(el.dataset.name).openPopup();
});
