import argparse
import csv
import json
from pathlib import Path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mapa de Reclamos Hidricos</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * { box-sizing: border-box; }
    html, body { height: 100%; margin: 0; }
    body {
      font-family: Arial, Helvetica, sans-serif;
      color: #1f2933;
      background: #f4f7f9;
      overflow: hidden;
    }
    .app {
      height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }
    .topbar {
      background: #184e77;
      color: #fff;
      padding: 10px 14px;
      display: grid;
      grid-template-columns: minmax(220px, 1fr) auto;
      gap: 12px;
      align-items: center;
    }
    .title {
      min-width: 0;
    }
    .title h1 {
      margin: 0;
      font-size: 17px;
      font-weight: 700;
      letter-spacing: 0;
      line-height: 1.2;
    }
    .title p {
      margin: 3px 0 0;
      color: #d8e8f5;
      font-size: 12px;
      line-height: 1.3;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .toolbar select,
    .toolbar input {
      height: 32px;
      border: 1px solid rgba(255,255,255,0.35);
      border-radius: 4px;
      padding: 0 9px;
      font-size: 13px;
      background: #fff;
      color: #1f2933;
      min-width: 145px;
    }
    .toolbar input {
      width: 230px;
    }
    .toolbar button {
      height: 32px;
      border: 1px solid rgba(255,255,255,0.35);
      border-radius: 4px;
      padding: 0 10px;
      background: #f7fbff;
      color: #184e77;
      font-size: 13px;
      cursor: pointer;
    }
    .toolbar button.active {
      background: #f59e0b;
      color: #111827;
      border-color: #fbbf24;
    }
    .main {
      min-height: 0;
      display: grid;
      grid-template-columns: 330px 1fr;
    }
    .sidebar {
      min-height: 0;
      display: grid;
      grid-template-rows: auto auto 1fr;
      border-right: 1px solid #d5dde5;
      background: #fff;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      padding: 10px;
      border-bottom: 1px solid #e3e9ef;
    }
    .stat {
      border: 1px solid #d9e2ec;
      border-radius: 6px;
      padding: 8px;
      background: #f8fbfd;
      min-height: 58px;
    }
    .stat b {
      display: block;
      font-size: 20px;
      line-height: 1.1;
      color: #184e77;
    }
    .stat span {
      display: block;
      margin-top: 4px;
      font-size: 12px;
      color: #52616f;
    }
    .legend {
      padding: 10px 12px;
      border-bottom: 1px solid #e3e9ef;
      font-size: 12px;
      color: #405261;
    }
    .legend-title {
      font-weight: 700;
      color: #1f2933;
      margin-bottom: 6px;
    }
    .legend-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px 10px;
    }
    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
    }
    .dot {
      width: 11px;
      height: 11px;
      border-radius: 50%;
      flex: 0 0 auto;
      border: 1px solid rgba(0,0,0,0.18);
    }
    .result-header {
      padding: 9px 12px;
      border-bottom: 1px solid #e3e9ef;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: #52616f;
    }
    .results {
      min-height: 0;
      overflow: auto;
    }
    .ticket-row {
      width: 100%;
      text-align: left;
      border: 0;
      border-bottom: 1px solid #eef2f5;
      background: #fff;
      padding: 9px 12px;
      cursor: pointer;
    }
    .ticket-row:hover {
      background: #f3f8fc;
    }
    .ticket-main {
      display: flex;
      align-items: center;
      gap: 7px;
      margin-bottom: 4px;
      min-width: 0;
    }
    .ticket-number {
      font-weight: 700;
      color: #14213d;
      font-size: 13px;
    }
    .ticket-status {
      font-size: 11px;
      color: #52616f;
    }
    .ticket-address {
      font-size: 12px;
      color: #405261;
      line-height: 1.3;
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
    #map {
      min-width: 0;
      min-height: 0;
      height: 100%;
      width: 100%;
      background: #e8eef4;
    }
    .marker-dot {
      width: 18px;
      height: 18px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 1px 5px rgba(0,0,0,0.45);
    }
    .marker-dot.edited {
      outline: 3px solid #facc15;
      outline-offset: 1px;
    }
    .edit-panel {
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 1000;
      width: min(330px, calc(100% - 24px));
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      background: #fff;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.2);
      padding: 10px;
      font-size: 12px;
      color: #334155;
      display: none;
    }
    .edit-panel.visible {
      display: block;
    }
    .edit-panel h2 {
      margin: 0 0 7px;
      font-size: 14px;
      color: #14213d;
    }
    .edit-panel p {
      margin: 5px 0;
      line-height: 1.35;
    }
    .edit-actions {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px;
      margin-top: 8px;
    }
    .edit-actions button,
    .popup-actions button {
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      background: #f8fafc;
      color: #1f2933;
      height: 30px;
      padding: 0 8px;
      cursor: pointer;
      font-size: 12px;
    }
    .edit-actions button.primary {
      background: #184e77;
      color: #fff;
      border-color: #184e77;
    }
    .edit-actions button.wide {
      grid-column: 1 / -1;
    }
    .edit-status {
      min-height: 17px;
      margin-top: 8px;
      color: #475569;
    }
    .edit-status.error {
      color: #b91c1c;
    }
    .edit-status.ok {
      color: #166534;
    }
    .leaflet-popup-content-wrapper {
      border-radius: 6px;
    }
    .popup {
      width: min(340px, 72vw);
      font-size: 12px;
      line-height: 1.35;
    }
    .popup h2 {
      margin: 0 0 7px;
      font-size: 15px;
      color: #14213d;
    }
    .popup-row {
      margin: 4px 0;
    }
    .popup-label {
      font-weight: 700;
      color: #405261;
    }
    .popup-description {
      margin-top: 7px;
      padding-top: 7px;
      border-top: 1px solid #e3e9ef;
      max-height: 150px;
      overflow: auto;
      white-space: pre-wrap;
    }
    .popup-coords {
      font-family: Consolas, monospace;
      font-size: 11px;
      color: #475569;
    }
    .popup-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }
    @media (max-width: 820px) {
      body { overflow: auto; }
      .app { min-height: 100vh; height: auto; }
      .topbar { grid-template-columns: 1fr; }
      .toolbar { justify-content: stretch; }
      .toolbar select,
      .toolbar input,
      .toolbar button { flex: 1 1 150px; min-width: 0; width: auto; }
      .main {
        grid-template-columns: 1fr;
        grid-template-rows: 52vh auto;
      }
      .sidebar {
        grid-row: 2;
        border-right: 0;
        border-top: 1px solid #d5dde5;
        max-height: 48vh;
      }
      #map { grid-row: 1; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="title">
        <h1>Mapa de Reclamos Hidricos</h1>
        <p>Resistencia, Chaco. Puntos geolocalizados listos para inspeccion operativa.</p>
      </div>
      <div class="toolbar">
        <select id="estadoFilter" aria-label="Filtrar por estado">
          <option value="">Todos los estados</option>
        </select>
        <select id="problemaFilter" aria-label="Filtrar por problema">
          <option value="">Todos los problemas</option>
        </select>
        <select id="fuenteFilter" aria-label="Filtrar por fuente">
          <option value="">Todas las fuentes</option>
        </select>
        <input id="searchInput" type="search" placeholder="Buscar ticket, direccion o descripcion" aria-label="Buscar" />
        <button id="editButton" type="button">Editar ubicaciones</button>
        <button id="exportButton" type="button">Exportar correcciones</button>
        <button id="fitButton" type="button">Ver todos</button>
      </div>
    </header>
    <main class="main">
      <aside class="sidebar">
        <section class="stats" aria-label="Resumen">
          <div class="stat"><b id="visibleCount">0</b><span>visibles</span></div>
          <div class="stat"><b id="totalCount">0</b><span>geolocalizados</span></div>
          <div class="stat"><b id="pendingCount">0</b><span>pendientes visibles</span></div>
          <div class="stat"><b id="issueCount">0</b><span>tipos de problema</span></div>
        </section>
        <section class="legend">
          <div class="legend-title">Estados</div>
          <div id="legendGrid" class="legend-grid"></div>
        </section>
        <div class="result-header">
          <span>Tickets</span>
          <span id="resultSummary"></span>
        </div>
        <section id="results" class="results" aria-label="Resultados"></section>
      </aside>
      <div style="position:relative;min-width:0;min-height:0;">
        <div id="map"></div>
        <section id="editPanel" class="edit-panel" aria-live="polite">
          <h2>Edicion de ubicaciones</h2>
          <p>Activa el modo edicion y arrastra un punto para corregir su posicion. Los cambios quedan guardados en este navegador.</p>
          <p><b id="editedCount">0</b> puntos corregidos.</p>
          <div class="edit-actions">
            <button id="applyCorrections" class="primary wide" type="button">Actualizar CSV/KMZ</button>
            <button id="downloadCorrections" class="primary" type="button">Descargar CSV</button>
            <button id="downloadGeojson" type="button">Descargar GeoJSON</button>
            <button id="clearCorrections" type="button">Borrar cambios</button>
            <button id="closeEditPanel" type="button">Cerrar</button>
          </div>
          <div id="editStatus" class="edit-status"></div>
        </section>
      </div>
    </main>
  </div>
  <script>
    const TICKETS = __DATA__;
    const COLORS = {
      "Pendiente": "#d97706",
      "Abierto": "#168aad",
      "Resuelto": "#2a9d8f",
      "Cerrado": "#64748b",
      "Cerrado-Conforme": "#4b5563",
      "Cerrado-No responde": "#6b7280",
      "Realizado": "#2a9d8f",
      "Atrasado": "#dc2626",
      "Sin estado": "#475569"
    };
    const DEFAULT_COLOR = "#4f46e5";

    const map = L.map("map", { zoomControl: true }).setView([-27.45, -58.99], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap"
    }).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    const markerByIndex = new Map();
    const STORAGE_KEY = "reclamos_hidricos_location_edits_v1";
    let corrections = loadCorrections();
    let editMode = false;
    let visibleTickets = [];

    const estadoFilter = document.getElementById("estadoFilter");
    const problemaFilter = document.getElementById("problemaFilter");
    const fuenteFilter = document.getElementById("fuenteFilter");
    const searchInput = document.getElementById("searchInput");
    const results = document.getElementById("results");
    const editButton = document.getElementById("editButton");
    const editPanel = document.getElementById("editPanel");
    const editStatus = document.getElementById("editStatus");

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[ch]));
    }

    function colorFor(status) {
      return COLORS[status || "Sin estado"] || DEFAULT_COLOR;
    }

    function ticketKey(ticket) {
      return String(ticket.ticket || ticket.id || "");
    }

    function loadCorrections() {
      try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      } catch (error) {
        return {};
      }
    }

    function saveCorrections() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(corrections));
      updateEditedCount();
    }

    function applyStoredCorrections() {
      TICKETS.forEach(ticket => {
        const correction = corrections[ticketKey(ticket)];
        if (correction) {
          ticket.originalLat = ticket.originalLat ?? ticket.lat;
          ticket.originalLng = ticket.originalLng ?? ticket.lng;
          ticket.lat = correction.lat;
          ticket.lng = correction.lng;
          ticket.edited = true;
          ticket.editedAt = correction.editedAt;
        }
      });
    }

    function markerIcon(status, edited = false) {
      return L.divIcon({
        className: "",
        html: `<div class="marker-dot ${edited ? "edited" : ""}" style="background:${colorFor(status)}"></div>`,
        iconSize: [18, 18],
        iconAnchor: [9, 9],
        popupAnchor: [0, -9]
      });
    }

    function popupHtml(ticket) {
      const original = ticket.edited
        ? `<div class="popup-row popup-coords"><span class="popup-label">Original:</span> ${Number(ticket.originalLat).toFixed(6)}, ${Number(ticket.originalLng).toFixed(6)}</div>`
        : "";
      const edited = ticket.edited
        ? `<div class="popup-row"><span class="popup-label">Correccion:</span> guardada</div>`
        : "";
      return `<div class="popup">
        <h2>Ticket ${escapeHtml(ticket.ticket)}</h2>
        <div class="popup-row"><span class="popup-label">ID:</span> ${escapeHtml(ticket.id)}</div>
        <div class="popup-row"><span class="popup-label">Estado:</span> ${escapeHtml(ticket.estado)}</div>
        <div class="popup-row"><span class="popup-label">Problema:</span> ${escapeHtml(ticket.problema)}</div>
        <div class="popup-row"><span class="popup-label">Direccion:</span> ${escapeHtml(ticket.direccion)}</div>
        <div class="popup-row"><span class="popup-label">Fuente:</span> ${escapeHtml(ticket.fuente)}</div>
        <div class="popup-row popup-coords"><span class="popup-label">Actual:</span> ${Number(ticket.lat).toFixed(6)}, ${Number(ticket.lng).toFixed(6)}</div>
        ${original}
        ${edited}
        <div class="popup-description">${escapeHtml(ticket.descripcion)}</div>
        <div class="popup-actions">
          <button type="button" onclick="window.reclamosMap.copyCoords('${escapeHtml(ticketKey(ticket))}')">Copiar coordenadas</button>
          ${ticket.edited ? `<button type="button" onclick="window.reclamosMap.undoEdit('${escapeHtml(ticketKey(ticket))}')">Revertir punto</button>` : ""}
        </div>
      </div>`;
    }

    function addOptions(select, values) {
      values.forEach(value => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });
    }

    function populateControls() {
      const estados = [...new Set(TICKETS.map(t => t.estado || "Sin estado"))].sort();
      const problemas = [...new Set(TICKETS.map(t => t.problema || "Sin problema"))].sort();
      const fuentes = [...new Set(TICKETS.map(t => t.fuente || "Sin fuente"))].sort();
      addOptions(estadoFilter, estados);
      addOptions(problemaFilter, problemas);
      addOptions(fuenteFilter, fuentes);

      const legendGrid = document.getElementById("legendGrid");
      estados.forEach(estado => {
        const item = document.createElement("div");
        item.className = "legend-item";
        item.innerHTML = `<span class="dot" style="background:${colorFor(estado)}"></span><span>${escapeHtml(estado)}</span>`;
        legendGrid.appendChild(item);
      });
    }

    function matches(ticket) {
      const estado = estadoFilter.value;
      const problema = problemaFilter.value;
      const fuente = fuenteFilter.value;
      const search = searchInput.value.trim().toLowerCase();
      if (estado && (ticket.estado || "Sin estado") !== estado) return false;
      if (problema && (ticket.problema || "Sin problema") !== problema) return false;
      if (fuente && (ticket.fuente || "Sin fuente") !== fuente) return false;
      if (!search) return true;
      const haystack = [
        ticket.ticket,
        ticket.id,
        ticket.estado,
        ticket.problema,
        ticket.direccion,
        ticket.descripcion,
        ticket.fuente
      ].join(" ").toLowerCase();
      return haystack.includes(search);
    }

    function renderMarkers() {
      markersLayer.clearLayers();
      markerByIndex.clear();
      visibleTickets.forEach((ticket, listIndex) => {
        const marker = L.marker([ticket.lat, ticket.lng], {
          icon: markerIcon(ticket.estado, ticket.edited),
          draggable: editMode
        })
          .bindPopup(popupHtml(ticket));
        marker.on("dragend", () => {
          const pos = marker.getLatLng();
          updateTicketLocation(ticket, pos.lat, pos.lng);
          marker.setIcon(markerIcon(ticket.estado, true));
          marker.bindPopup(popupHtml(ticket));
          renderResults();
        });
        marker.addTo(markersLayer);
        markerByIndex.set(listIndex, marker);
      });
    }

    function renderResults() {
      results.innerHTML = "";
      const fragment = document.createDocumentFragment();
      visibleTickets.forEach((ticket, index) => {
        const button = document.createElement("button");
        button.className = "ticket-row";
        button.type = "button";
        button.innerHTML = `<div class="ticket-main">
          <span class="dot" style="background:${ticket.edited ? "#facc15" : colorFor(ticket.estado)}"></span>
          <span class="ticket-number">${escapeHtml(ticket.ticket)}</span>
          <span class="ticket-status">${escapeHtml(ticket.estado)}</span>
        </div>
        <div class="ticket-address">${escapeHtml(ticket.direccion || ticket.descripcion)}</div>`;
        button.addEventListener("click", () => {
          const marker = markerByIndex.get(index);
          if (marker) {
            map.setView(marker.getLatLng(), Math.max(map.getZoom(), 16), { animate: true });
            marker.openPopup();
          }
        });
        fragment.appendChild(button);
      });
      results.appendChild(fragment);
    }

    function updateStats() {
      const pending = visibleTickets.filter(t => (t.estado || "").toLowerCase().includes("pendiente")).length;
      const issueTypes = new Set(visibleTickets.map(t => t.problema || "Sin problema")).size;
      document.getElementById("visibleCount").textContent = visibleTickets.length;
      document.getElementById("totalCount").textContent = TICKETS.length;
      document.getElementById("pendingCount").textContent = pending;
      document.getElementById("issueCount").textContent = issueTypes;
      document.getElementById("resultSummary").textContent = `${visibleTickets.length} de ${TICKETS.length}`;
    }

    function updateEditedCount() {
      document.getElementById("editedCount").textContent = Object.keys(corrections).length;
    }

    function setEditStatus(message, kind = "") {
      editStatus.textContent = message;
      editStatus.className = `edit-status ${kind}`.trim();
    }

    function updateTicketLocation(ticket, lat, lng) {
      if (ticket.originalLat === undefined) ticket.originalLat = ticket.lat;
      if (ticket.originalLng === undefined) ticket.originalLng = ticket.lng;
      ticket.lat = Number(lat);
      ticket.lng = Number(lng);
      ticket.edited = true;
      ticket.editedAt = new Date().toISOString();
      corrections[ticketKey(ticket)] = {
        ticket: ticket.ticket,
        id: ticket.id,
        direccion: ticket.direccion,
        estado: ticket.estado,
        problema: ticket.problema,
        originalLat: ticket.originalLat,
        originalLng: ticket.originalLng,
        lat: ticket.lat,
        lng: ticket.lng,
        editedAt: ticket.editedAt
      };
      saveCorrections();
    }

    function undoEditByKey(key) {
      const ticket = TICKETS.find(item => ticketKey(item) === key);
      if (!ticket || !corrections[key]) return;
      ticket.lat = ticket.originalLat ?? corrections[key].originalLat;
      ticket.lng = ticket.originalLng ?? corrections[key].originalLng;
      ticket.edited = false;
      delete ticket.editedAt;
      delete corrections[key];
      saveCorrections();
      applyFilters({ fit: false });
    }

    function setEditMode(enabled) {
      editMode = enabled;
      editButton.classList.toggle("active", editMode);
      editButton.textContent = editMode ? "Edicion activa" : "Editar ubicaciones";
      editPanel.classList.toggle("visible", editMode);
      renderMarkers();
    }

    function correctionsRows() {
      return Object.values(corrections).sort((a, b) => String(a.ticket).localeCompare(String(b.ticket)));
    }

    function downloadText(filename, mimeType, text) {
      const blob = new Blob([text], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    function csvEscape(value) {
      const text = String(value ?? "");
      return /[",\\n\\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    }

    function exportCorrectionsCsv() {
      const rows = correctionsRows();
      const header = ["ticket", "id", "direccion", "estado", "problema", "originalLat", "originalLng", "lat", "lng", "editedAt"];
      const lines = [header.join(",")].concat(rows.map(row => header.map(key => csvEscape(row[key])).join(",")));
      downloadText("correcciones_ubicacion_reclamos.csv", "text/csv;charset=utf-8", lines.join("\\n"));
    }

    function exportCorrectionsGeoJson() {
      const features = correctionsRows().map(row => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [row.lng, row.lat] },
        properties: row
      }));
      downloadText(
        "correcciones_ubicacion_reclamos.geojson",
        "application/geo+json;charset=utf-8",
        JSON.stringify({ type: "FeatureCollection", features }, null, 2)
      );
    }

    async function applyCorrectionsToFiles() {
      const rows = correctionsRows();
      if (!rows.length) {
        setEditStatus("No hay correcciones para guardar.", "error");
        return;
      }
      const button = document.getElementById("applyCorrections");
      button.disabled = true;
      setEditStatus("Actualizando CSV y KMZ...", "");
      try {
        const response = await fetch("/api/apply-corrections", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ corrections: rows })
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudieron guardar las correcciones.");
        }
        const updatedKeys = new Set(rows.map(row => ticketKey(row)));
        corrections = {};
        localStorage.removeItem(STORAGE_KEY);
        TICKETS.forEach(ticket => {
          if (!updatedKeys.has(ticketKey(ticket))) return;
          ticket.originalLat = ticket.lat;
          ticket.originalLng = ticket.lng;
          ticket.edited = false;
          delete ticket.editedAt;
          if (ticket.fuente) ticket.fuente = "Correccion manual";
        });
        updateEditedCount();
        applyFilters({ fit: false });
        setEditStatus(`CSV y KMZ actualizados: ${payload.updated} puntos.`, "ok");
      } catch (error) {
        setEditStatus(`No se pudo actualizar: ${error.message}. Abrir el mapa con src/edit_server.py.`, "error");
      } finally {
        button.disabled = false;
      }
    }

    function clearCorrections() {
      if (!confirm("Borrar todas las correcciones guardadas en este navegador?")) return;
      corrections = {};
      localStorage.removeItem(STORAGE_KEY);
      TICKETS.forEach(ticket => {
        if (ticket.originalLat !== undefined) ticket.lat = ticket.originalLat;
        if (ticket.originalLng !== undefined) ticket.lng = ticket.originalLng;
        ticket.edited = false;
        delete ticket.editedAt;
      });
      updateEditedCount();
      applyFilters({ fit: false });
    }

    function fitVisible() {
      if (!visibleTickets.length) return;
      const bounds = L.latLngBounds(visibleTickets.map(ticket => [ticket.lat, ticket.lng]));
      map.fitBounds(bounds, { padding: [28, 28], maxZoom: 16 });
    }

    function applyFilters({ fit = false } = {}) {
      visibleTickets = TICKETS.filter(matches);
      renderMarkers();
      renderResults();
      updateStats();
      if (fit) fitVisible();
    }

    [estadoFilter, problemaFilter, fuenteFilter].forEach(select => {
      select.addEventListener("change", () => applyFilters({ fit: true }));
    });
    searchInput.addEventListener("input", () => applyFilters({ fit: true }));
    document.getElementById("fitButton").addEventListener("click", fitVisible);
    editButton.addEventListener("click", () => setEditMode(!editMode));
    document.getElementById("exportButton").addEventListener("click", exportCorrectionsCsv);
    document.getElementById("applyCorrections").addEventListener("click", applyCorrectionsToFiles);
    document.getElementById("downloadCorrections").addEventListener("click", exportCorrectionsCsv);
    document.getElementById("downloadGeojson").addEventListener("click", exportCorrectionsGeoJson);
    document.getElementById("clearCorrections").addEventListener("click", clearCorrections);
    document.getElementById("closeEditPanel").addEventListener("click", () => setEditMode(false));

    window.reclamosMap = {
      copyCoords(key) {
        const ticket = TICKETS.find(item => ticketKey(item) === key);
        if (!ticket) return;
        navigator.clipboard?.writeText(`${ticket.lat.toFixed(7)},${ticket.lng.toFixed(7)}`);
      },
      undoEdit: undoEditByKey,
      applyCorrectionsToFiles,
      exportCorrectionsCsv,
      exportCorrectionsGeoJson
    };

    applyStoredCorrections();
    populateControls();
    updateEditedCount();
    applyFilters({ fit: true });
  </script>
</body>
</html>
"""


def clean_value(value):
    if value is None:
        return ""
    value = str(value).strip()
    if value.endswith(".0"):
        return value[:-2]
    return value


def build_map(input_csv, output_html):
    tickets = []
    with Path(input_csv).open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if not row.get("lat") or not row.get("lng"):
                continue
            tickets.append(
                {
                    "id": clean_value(row.get("id")),
                    "ticket": clean_value(row.get("ticket")),
                    "estado": clean_value(row.get("estado")) or "Sin estado",
                    "direccion": clean_value(row.get("direccion")),
                    "problema": clean_value(row.get("problema")) or "Sin problema",
                    "descripcion": clean_value(row.get("descripcion")),
                    "fuente": clean_value(row.get("fuente")) or "Sin fuente",
                    "lat": float(row["lat"]),
                    "lng": float(row["lng"]),
                }
            )

    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(tickets, ensure_ascii=False))
    output_path = Path(output_html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(json.dumps({"tickets": len(tickets), "output": str(output_path)}, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Genera un mapa HTML interactivo desde el CSV geolocalizado.")
    parser.add_argument("input_csv")
    parser.add_argument("output_html")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    build_map(args.input_csv, args.output_html)
