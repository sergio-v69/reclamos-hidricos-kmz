const CONFIG = {
  SHEET_NAME: 'tickets',
  OUTPUT_FOLDER_NAME: 'Reclamos Hidricos KMZ',
  BOUNDS: {
    latMin: -27.55,
    latMax: -27.30,
    lngMin: -59.10,
    lngMax: -58.85
  }
};

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Normalizador Reclamos Hidricos')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function setupWorkbook() {
  const sheet = getTicketSheet_();
  ensureColumns_(sheet, [
    'direccion_corregida',
    'nota_correccion',
    'requiere_llamada_vecino',
    'estado_geocodificacion',
    'fecha_correccion',
    'usuario_correccion'
  ]);
  return { ok: true, message: 'Estructura verificada.' };
}

function getPendingTickets() {
  const rows = readRows_();
  return rows
    .filter(row => !row.lat || !row.lng)
    .map(row => ({
      rowNumber: row._rowNumber,
      ticket: cleanValue_(row.ticket || row.id),
      id: cleanValue_(row.id),
      fecha: cleanValue_(row.fecha),
      estado: cleanValue_(row.estado),
      direccion: cleanValue_(row.direccion),
      problema: cleanValue_(row.problema),
      descripcion: cleanValue_(row.descripcion),
      direccion_corregida: cleanValue_(row.direccion_corregida),
      nota_correccion: cleanValue_(row.nota_correccion),
      requiere_llamada_vecino: cleanValue_(row.requiere_llamada_vecino)
    }));
}

function saveCorrection(payload) {
  const sheet = getTicketSheet_();
  const headers = getHeaders_(sheet);
  const rowNumber = Number(payload.rowNumber);
  if (!rowNumber || rowNumber < 2) throw new Error('Fila invalida.');
  writeByHeader_(sheet, headers, rowNumber, {
    direccion_corregida: payload.correctedAddress || '',
    nota_correccion: payload.note || '',
    requiere_llamada_vecino: payload.needsPrecision ? 'SI' : '',
    estado_geocodificacion: payload.correctedAddress ? 'CORREGIDA' : (payload.needsPrecision ? 'LLAMAR_VECINO' : ''),
    fecha_correccion: new Date(),
    usuario_correccion: Session.getActiveUser().getEmail() || ''
  });
  return { ok: true };
}

function markNeedsCall(payload) {
  payload = payload || {};
  payload.needsPrecision = true;
  payload.note = payload.note || 'Requiere llamada al vecino para precisar ubicacion.';
  return saveCorrection(payload);
}

function testGeocode(address) {
  const result = geocodeAddress_(address);
  if (!result) {
    return { found: false, message: 'No se encontro una ubicacion dentro del area esperada.' };
  }
  return { found: true, lat: result.lat, lng: result.lng, displayName: result.displayName };
}

function applyCorrectedGeocodes() {
  const sheet = getTicketSheet_();
  const headers = getHeaders_(sheet);
  const rows = readRows_();
  let updated = 0;
  rows.forEach(row => {
    if (row.lat && row.lng) return;
    if (String(row.requiere_llamada_vecino || '').toUpperCase() === 'SI') return;
    const address = cleanValue_(row.direccion_corregida);
    if (!address) return;
    const result = geocodeAddress_(address);
    if (!result) {
      writeByHeader_(sheet, headers, row._rowNumber, { estado_geocodificacion: 'NO_ENCONTRADA' });
      return;
    }
    writeByHeader_(sheet, headers, row._rowNumber, {
      lat: result.lat,
      lng: result.lng,
      fuente: 'Direccion corregida manual',
      estado_geocodificacion: 'GEOLOCALIZADA',
      fecha_correccion: new Date(),
      usuario_correccion: Session.getActiveUser().getEmail() || ''
    });
    updated += 1;
    Utilities.sleep(1100);
  });
  const file = generateKmz();
  return { ok: true, updated, kmzUrl: file.getUrl() };
}

function generateKmz() {
  const rows = readRows_().filter(row => row.lat && row.lng);
  const placemarks = rows.map(row => {
    const name = xmlEscape_(cleanValue_(row.ticket || row.id || 'Sin ticket'));
    const description = [
      ['Ticket', row.ticket],
      ['ID', row.id],
      ['Fecha', row.fecha],
      ['Estado', row.estado],
      ['Problema', row.problema],
      ['Direccion', row.direccion],
      ['Direccion corregida', row.direccion_corregida],
      ['Descripcion del reclamo', row.descripcion],
      ['Fuente', row.fuente]
    ].map(pair => `<b>${xmlEscape_(pair[0])}:</b> ${xmlEscape_(cleanValue_(pair[1]))}`).join('<br/>');
    return `<Placemark><name>${name}</name><description><![CDATA[${description}]]></description><Point><coordinates>${row.lng},${row.lat},0</coordinates></Point></Placemark>`;
  }).join('\n');
  const kml = `<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Reclamos Hidricos</name>${placemarks}</Document></kml>`;
  const blob = Utilities.newBlob(kml, 'application/vnd.google-earth.kml+xml', 'doc.kml');
  const kmzBlob = Utilities.zip([blob], 'reclamos_hidricos_geolocalizados.kmz');
  return getOutputFolder_().createFile(kmzBlob);
}

function geocodeAddress_(address) {
  address = cleanValue_(address);
  if (!address) throw new Error('Ingrese una direccion.');
  const query = `${address}, Resistencia, Chaco, Argentina`;
  const params = {
    q: query,
    format: 'jsonv2',
    limit: 1,
    addressdetails: 0,
    bounded: 1,
    viewbox: `${CONFIG.BOUNDS.lngMin},${CONFIG.BOUNDS.latMax},${CONFIG.BOUNDS.lngMax},${CONFIG.BOUNDS.latMin}`
  };
  const url = 'https://nominatim.openstreetmap.org/search?' + Object.keys(params)
    .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`).join('&');
  const response = UrlFetchApp.fetch(url, {
    headers: { 'User-Agent': 'reclamos-hidricos-apps-script/1.0' },
    muteHttpExceptions: true
  });
  if (response.getResponseCode() >= 400) {
    throw new Error(`Nominatim respondio ${response.getResponseCode()}. Reintente mas tarde.`);
  }
  const data = JSON.parse(response.getContentText());
  if (!data.length) return null;
  const lat = Number(data[0].lat);
  const lng = Number(data[0].lon);
  if (!inBounds_(lat, lng)) return null;
  return { lat, lng, displayName: data[0].display_name || '' };
}

function readRows_() {
  const sheet = getTicketSheet_();
  const values = sheet.getDataRange().getValues();
  const headers = values.shift().map(cleanHeader_);
  return values.map((row, index) => {
    const item = { _rowNumber: index + 2 };
    headers.forEach((header, columnIndex) => item[header] = row[columnIndex]);
    return item;
  });
}

function getTicketSheet_() {
  const sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) throw new Error(`No existe la hoja ${CONFIG.SHEET_NAME}.`);
  return sheet;
}

function getHeaders_(sheet) {
  return sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(cleanHeader_);
}

function ensureColumns_(sheet, names) {
  const headers = getHeaders_(sheet);
  names.forEach(name => {
    if (headers.indexOf(name) === -1) {
      sheet.getRange(1, sheet.getLastColumn() + 1).setValue(name);
      headers.push(name);
    }
  });
}

function writeByHeader_(sheet, headers, rowNumber, data) {
  Object.keys(data).forEach(key => {
    const index = headers.indexOf(cleanHeader_(key));
    if (index !== -1) sheet.getRange(rowNumber, index + 1).setValue(data[key]);
  });
}

function getOutputFolder_() {
  const folders = DriveApp.getFoldersByName(CONFIG.OUTPUT_FOLDER_NAME);
  return folders.hasNext() ? folders.next() : DriveApp.createFolder(CONFIG.OUTPUT_FOLDER_NAME);
}

function inBounds_(lat, lng) {
  return lat >= CONFIG.BOUNDS.latMin && lat <= CONFIG.BOUNDS.latMax && lng >= CONFIG.BOUNDS.lngMin && lng <= CONFIG.BOUNDS.lngMax;
}

function cleanHeader_(value) {
  return cleanValue_(value).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, '_');
}

function cleanValue_(value) {
  return value === null || value === undefined ? '' : String(value).trim();
}

function xmlEscape_(value) {
  return cleanValue_(value).replace(/[<>&'"]/g, char => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[char]));
}
