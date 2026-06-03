import argparse
import csv
import json
from pathlib import Path

from address_correction_geocoder import load_address_corrections, ticket_key


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Normalizar direcciones pendientes</title>
  <style>
    * { box-sizing: border-box; }
    html, body { height: 100%; margin: 0; overflow: hidden; }
    body { font-family: Arial, Helvetica, sans-serif; color: #1f2933; background: #f4f7f9; }
    .app { height: 100vh; min-height: 0; display: grid; grid-template-rows: auto minmax(0, 1fr); overflow: hidden; }
    header {
      background: #184e77; color: white; padding: 12px 14px;
      display: grid; grid-template-columns: minmax(240px, 1fr) auto; gap: 12px; align-items: center;
    }
    h1 { margin: 0; font-size: 18px; line-height: 1.2; }
    header p { margin: 3px 0 0; color: #d8e8f5; font-size: 12px; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
    input, textarea, select, button {
      font: inherit; border: 1px solid #cbd5e1; border-radius: 4px;
    }
    .toolbar input, .toolbar select, .toolbar button { height: 32px; padding: 0 9px; }
    button { cursor: pointer; background: #f8fafc; color: #184e77; }
    button.primary { background: #184e77; color: #fff; border-color: #184e77; }
    button.danger { color: #991b1b; }
    .main { min-height: 0; overflow: hidden; display: grid; grid-template-columns: 390px minmax(0, 1fr); }
    .list { height: 100%; min-height: 0; overflow-y: auto; overflow-x: hidden; background: #fff; border-right: 1px solid #d5dde5; }
    .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 10px; border-bottom: 1px solid #e5e7eb; }
    .stat { border: 1px solid #d9e2ec; border-radius: 6px; padding: 8px; background: #f8fbfd; }
    .stat b { display: block; font-size: 20px; color: #184e77; }
    .stat span { font-size: 12px; color: #52616f; }
    .ticket-row {
      width: 100%; text-align: left; border: 0; border-bottom: 1px solid #eef2f5;
      background: #fff; padding: 9px 12px; border-radius: 0;
    }
    .ticket-row:hover, .ticket-row.active { background: #edf6fb; }
    .ticket-row.saved .ticket-number::after { content: " corregido"; color: #166534; font-weight: 400; margin-left: 6px; }
    .ticket-row.call .ticket-number::after { content: " llamar"; color: #9a3412; font-weight: 400; margin-left: 6px; }
    .ticket-main { display: flex; gap: 8px; align-items: baseline; }
    .ticket-number { font-weight: 700; color: #14213d; }
    .ticket-date, .ticket-status { font-size: 11px; color: #64748b; }
    .ticket-address { margin-top: 5px; font-size: 12px; line-height: 1.3; color: #405261; }
    .editor { height: 100%; min-width: 0; padding: 14px; overflow-y: auto; overflow-x: hidden; }
    .panel { max-width: 980px; margin: 0 auto; }
    .section { margin-bottom: 12px; }
    .label { display: block; font-size: 12px; font-weight: 700; color: #405261; margin-bottom: 5px; }
    .value, textarea, .corrected-input {
      width: 100%; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px;
      padding: 9px; line-height: 1.35;
    }
    .value { min-height: 39px; white-space: pre-wrap; }
    textarea { min-height: 110px; resize: vertical; }
    .corrected-input { height: 38px; }
    .corrected-input[readonly], textarea[readonly] { background: #eef2f6; color: #52616f; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .status { min-height: 20px; font-size: 12px; margin-top: 8px; color: #475569; }
    .status.ok { color: #166534; }
    .status.error { color: #b91c1c; }
    .empty { padding: 20px; color: #64748b; }
    @media (max-width: 860px) {
      header { grid-template-columns: 1fr; }
      .toolbar { justify-content: stretch; }
      .toolbar input, .toolbar select, .toolbar button { flex: 1 1 150px; }
      .main { grid-template-columns: 1fr; grid-template-rows: minmax(180px, 42vh) minmax(0, 1fr); }
      .list { max-height: none; border-right: 0; border-bottom: 1px solid #d5dde5; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div>
        <h1>Normalizar direcciones pendientes</h1>
        <p>Tickets sin coordenadas. Edita la direccion, guarda y luego geolocaliza las corregidas.</p>
      </div>
      <div class="toolbar">
        <input id="searchInput" type="search" placeholder="Buscar ticket, direccion o descripcion" />
        <select id="statusFilter"><option value="">Todos</option><option value="saved">Con correccion</option><option value="call">Llamar vecino</option><option value="pending">Sin correccion</option></select>
        <button id="saveAll" class="primary" type="button">Guardar correcciones</button>
        <button id="geocodeAll" type="button">Geolocalizar corregidas</button>
      </div>
    </header>
    <main class="main">
      <aside class="list">
        <div class="summary">
          <div class="stat"><b id="visibleCount">0</b><span>visibles</span></div>
          <div class="stat"><b id="totalCount">0</b><span>pendientes</span></div>
          <div class="stat"><b id="savedCount">0</b><span>corregidos</span></div>
          <div class="stat"><b id="callCount">0</b><span>llamar</span></div>
        </div>
        <div id="ticketList"></div>
      </aside>
      <section class="editor">
        <div id="editorPanel" class="panel">
          <div class="empty">Selecciona un ticket para normalizar su direccion.</div>
        </div>
      </section>
    </main>
  </div>

  <form id="saveForm" method="POST" action="http://127.0.0.1:8765/api/address-corrections" style="display:none">
    <input id="savePayload" name="corrections" type="hidden" />
  </form>
  <form id="geocodeForm" method="POST" action="http://127.0.0.1:8765/api/geocode-corrected-addresses" style="display:none">
    <input id="geocodePayload" name="corrections" type="hidden" />
  </form>

  <script>
    const TICKETS = __TICKETS__;
    const INITIAL_CORRECTIONS = __CORRECTIONS__;
    const STORAGE_KEY = "reclamos_hidricos_address_corrections_v1";
    let corrections = loadCorrections();
    let currentKey = TICKETS[0] ? ticketKey(TICKETS[0]) : "";
    let visibleTickets = [];

    function ticketKey(ticket) {
      return String(ticket.ticket || ticket.id || "").replace(/\\.0$/, "");
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
      }[ch]));
    }

    function loadCorrections() {
      try {
        const stored = window.localStorage ? JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") : {};
        return { ...INITIAL_CORRECTIONS, ...stored };
      } catch (error) {
        return { ...INITIAL_CORRECTIONS };
      }
    }

    function persistLocal() {
      try {
        if (window.localStorage) {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(corrections));
        }
      } catch (error) {
        console.warn("No se pudo guardar el borrador local", error);
      }
      updateCounts();
    }

    function correctionRows() {
      return Object.values(corrections).filter(item => item.correctedAddress || item.note || item.needsPrecision);
    }

    function updateCurrentFromInputs({ rerenderList = false } = {}) {
      if (!currentKey) return;
      const ticket = TICKETS.find(item => ticketKey(item) === currentKey);
      const existing = corrections[currentKey] || {};
      corrections[currentKey] = {
        ticket: currentKey,
        id: ticket?.id || "",
        correctedAddress: document.getElementById("correctedAddress")?.value.trim() || "",
        note: document.getElementById("note")?.value.trim() || "",
        needsPrecision: !!existing.needsPrecision,
        updatedAt: new Date().toISOString()
      };
      if (!corrections[currentKey].correctedAddress && !corrections[currentKey].note && !corrections[currentKey].needsPrecision) {
        delete corrections[currentKey];
      }
      persistLocal();
      if (rerenderList) renderList();
    }

    function matches(ticket) {
      const search = document.getElementById("searchInput").value.trim().toLowerCase();
      const mode = document.getElementById("statusFilter").value;
      const correction = corrections[ticketKey(ticket)] || {};
      const saved = !!correction.correctedAddress;
      const call = !!correction.needsPrecision;
      if (mode === "saved" && !saved) return false;
      if (mode === "call" && !call) return false;
      if (mode === "pending" && (saved || call)) return false;
      if (!search) return true;
      return [ticket.ticket, ticket.id, ticket.fecha, ticket.estado, ticket.direccion, ticket.problema, ticket.descripcion, ticket.consulta_sugerida]
        .join(" ").toLowerCase().includes(search);
    }

    function renderList() {
      visibleTickets = TICKETS.filter(matches);
      const list = document.getElementById("ticketList");
      if (!visibleTickets.length) {
        list.innerHTML = '<div class="empty">No hay tickets para los filtros actuales.</div>';
      } else {
        list.innerHTML = visibleTickets.map(ticket => {
          const key = ticketKey(ticket);
          const correction = corrections[key] || {};
          const saved = !!correction.correctedAddress;
          const call = !!correction.needsPrecision;
          return `<button class="ticket-row ${key === currentKey ? "active" : ""} ${saved ? "saved" : ""} ${call ? "call" : ""}" type="button" data-key="${escapeHtml(key)}">
            <div class="ticket-main"><span class="ticket-number">${escapeHtml(ticket.ticket)}</span><span class="ticket-date">${escapeHtml(ticket.fecha)}</span><span class="ticket-status">${escapeHtml(ticket.estado)}</span></div>
            <div class="ticket-address">${escapeHtml(ticket.direccion || ticket.descripcion || "Sin direccion")}</div>
          </button>`;
        }).join("");
      }
      list.querySelectorAll("[data-key]").forEach(button => {
        button.addEventListener("click", () => {
          updateCurrentFromInputs({ rerenderList: true });
          currentKey = button.dataset.key;
          renderEditor();
          renderList();
        });
      });
      updateCounts();
    }

    function renderEditor() {
      const ticket = TICKETS.find(item => ticketKey(item) === currentKey);
      const panel = document.getElementById("editorPanel");
      if (!ticket) {
        panel.innerHTML = '<div class="empty">Selecciona un ticket para normalizar su direccion.</div>';
        return;
      }
      const correction = corrections[currentKey] || {};
      panel.innerHTML = `
        <div class="section"><span class="label">Ticket</span><div class="value"><b>${escapeHtml(ticket.ticket)}</b> - ${escapeHtml(ticket.fecha)} - ${escapeHtml(ticket.estado)}</div></div>
        <div class="section"><span class="label">Direccion original</span><div class="value">${escapeHtml(ticket.direccion || "")}</div></div>
        <div class="section"><span class="label">Descripcion</span><div class="value">${escapeHtml(ticket.descripcion || "")}</div></div>
        <div class="section"><span class="label">Consultas sugeridas</span><div class="value">${escapeHtml(ticket.consulta_sugerida || "")}</div></div>
        <div class="section"><label class="label" for="correctedAddress">Direccion corregida para geolocalizar</label><input id="correctedAddress" class="corrected-input" value="${escapeHtml(correction.correctedAddress || "")}" placeholder="Ej: Leandro N Alem 2900" readonly /></div>
        <div class="section"><label class="label" for="note">Nota interna</label><textarea id="note" placeholder="Motivo, referencia barrial, aclaracion..." readonly>${escapeHtml(correction.note || "")}</textarea></div>
        <div class="actions">
          <button id="editCurrent" type="button">Editar ticket</button>
          <button id="testGeocode" type="button">Probar geolocalizacion</button>
          <button id="markCall" type="button">Llamar al vecino</button>
          <button id="saveCurrent" class="primary" type="button">Guardar este ticket</button>
          <button id="clearCurrent" class="danger" type="button">Borrar correccion</button>
        </div>
        <div id="editorStatus" class="status"></div>`;
      setEditing(false);
      document.getElementById("editCurrent").addEventListener("click", () => {
        setEditing(true);
        document.getElementById("correctedAddress").focus();
        setEditorStatus("Edicion activa para este ticket.", "ok");
      });
      document.getElementById("testGeocode").addEventListener("click", testCurrentGeocode);
      document.getElementById("markCall").addEventListener("click", markNeedsCall);
      document.getElementById("saveCurrent").addEventListener("click", () => {
        updateCurrentFromInputs({ rerenderList: true });
        setEditing(false);
        setEditorStatus("Correccion guardada en esta sesion. Usa Guardar correcciones para escribirla en disco.", "ok");
      });
      document.getElementById("clearCurrent").addEventListener("click", () => {
        delete corrections[currentKey];
        persistLocal();
        renderEditor();
        renderList();
      });
      ["correctedAddress", "note"].forEach(id => {
        document.getElementById(id).addEventListener("input", persistCurrentDraft);
      });
    }

    function setEditing(enabled) {
      const corrected = document.getElementById("correctedAddress");
      const note = document.getElementById("note");
      const save = document.getElementById("saveCurrent");
      if (!corrected || !note || !save) return;
      corrected.readOnly = !enabled;
      note.readOnly = !enabled;
      save.disabled = !enabled;
    }

    function persistCurrentDraft() {
      updateCurrentFromInputs();
    }

    function setEditorStatus(message, kind = "") {
      const node = document.getElementById("editorStatus");
      if (!node) return;
      node.textContent = message;
      node.className = `status ${kind}`.trim();
    }

    function testCurrentGeocode() {
      const address = document.getElementById("correctedAddress")?.value.trim() || "";
      if (!address) {
        setEditorStatus("Primero ingresa una direccion corregida.", "error");
        return;
      }
      updateCurrentFromInputs();
      const button = document.getElementById("testGeocode");
      button.disabled = true;
      setEditorStatus("Probando geolocalizacion...", "");
      const request = new XMLHttpRequest();
      request.open("POST", "/api/test-geocode", true);
      request.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
      request.onload = () => {
        button.disabled = false;
        try {
          const result = JSON.parse(request.responseText || "{}");
          if (!result.ok) {
            setEditorStatus(`No se pudo probar: ${result.error || "error desconocido"}`, "error");
            return;
          }
          if (!result.found) {
            setEditorStatus(result.message || result.error || "No se encontro una ubicacion.", "error");
            return;
          }
          const cacheText = result.from_cache ? "cache" : "Nominatim";
          const place = result.display_name ? ` - ${result.display_name}` : "";
          setEditorStatus(`Encontrada: ${result.lat}, ${result.lng} (${cacheText})${place}`, "ok");
        } catch (error) {
          setEditorStatus("No se pudo interpretar la respuesta del servidor.", "error");
        }
      };
      request.onerror = () => {
        button.disabled = false;
        setEditorStatus("No se pudo conectar con el servidor editable.", "error");
      };
      request.send(JSON.stringify({ address }));
    }

    function markNeedsCall() {
      updateCurrentFromInputs();
      const ticket = TICKETS.find(item => ticketKey(item) === currentKey);
      const existing = corrections[currentKey] || {};
      const note = existing.note || document.getElementById("note")?.value.trim() || "";
      corrections[currentKey] = {
        ticket: currentKey,
        id: ticket?.id || "",
        correctedAddress: existing.correctedAddress || "",
        note: note || "Requiere llamada al vecino para precisar ubicacion.",
        needsPrecision: true,
        updatedAt: new Date().toISOString()
      };
      persistLocal();
      renderEditor();
      renderList();
      setEditorStatus("Marcado para llamar al vecino y pedir precision.", "ok");
    }

    function updateCounts() {
      document.getElementById("visibleCount").textContent = visibleTickets.length;
      document.getElementById("totalCount").textContent = TICKETS.length;
      document.getElementById("savedCount").textContent = correctionRows().length;
      document.getElementById("callCount").textContent = Object.values(corrections).filter(item => item.needsPrecision).length;
    }

    function submitForm(formId, payloadId) {
      updateCurrentFromInputs({ rerenderList: true });
      const rows = correctionRows();
      if (!rows.length) {
        alert("No hay direcciones corregidas para guardar.");
        return;
      }
      document.getElementById(payloadId).value = JSON.stringify(rows);
      document.getElementById(formId).submit();
    }

    document.getElementById("searchInput").addEventListener("input", renderList);
    document.getElementById("statusFilter").addEventListener("change", renderList);
    document.getElementById("saveAll").addEventListener("click", () => submitForm("saveForm", "savePayload"));
    document.getElementById("geocodeAll").addEventListener("click", () => {
      if (confirm("Guardar y geolocalizar las direcciones corregidas? Esto puede tardar si hay muchas.")) {
        submitForm("geocodeForm", "geocodePayload");
      }
    });

    renderList();
    renderEditor();
  </script>
</body>
</html>
"""


def clean_value(value):
    value = "" if value is None else str(value).strip()
    return value[:-2] if value.endswith(".0") else value


def build_normalizer(input_csv, corrections_json, output_html):
    corrections = load_address_corrections(corrections_json)
    tickets = []
    with Path(input_csv).open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get("lat") and row.get("lng"):
                continue
            key = ticket_key(row)
            correction = corrections.get(key, {})
            tickets.append(
                {
                    "excel_row": clean_value(row.get("excel_row")),
                    "id": clean_value(row.get("id")),
                    "ticket": clean_value(row.get("ticket")),
                    "fecha": clean_value(row.get("fecha")),
                    "estado": clean_value(row.get("estado")),
                    "direccion": clean_value(row.get("direccion")),
                    "problema": clean_value(row.get("problema")),
                    "descripcion": clean_value(row.get("descripcion")),
                    "fuente": clean_value(row.get("fuente")),
                    "consulta_sugerida": clean_value(row.get("consulta_sugerida")),
                    "direccion_corregida": correction.get("correctedAddress", clean_value(row.get("direccion_corregida"))),
                    "nota_correccion": correction.get("note", clean_value(row.get("nota_correccion"))),
                    "requiere_llamada_vecino": "SI"
                    if correction.get("needsPrecision")
                    else clean_value(row.get("requiere_llamada_vecino")),
                }
            )

    html = HTML_TEMPLATE.replace("__TICKETS__", json.dumps(tickets, ensure_ascii=False))
    html = html.replace("__CORRECTIONS__", json.dumps(corrections, ensure_ascii=False))
    output_path = Path(output_html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(json.dumps({"tickets": len(tickets), "output": str(output_path)}, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Genera un normalizador HTML para tickets sin geolocalizar.")
    parser.add_argument("input_csv")
    parser.add_argument("corrections_json")
    parser.add_argument("output_html")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    build_normalizer(args.input_csv, args.corrections_json, args.output_html)
