// Mapa de equipos (nombres en español del formulario) a códigos ISO de bandera.
// Las banderas se sirven en línea desde flagcdn.com.

const norm = (s) =>
  (s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");

const TEAM_CODES = {
  mexico: "mx",
  sudafrica: "za",
  repdecorea: "kr",
  corea: "kr",
  coreadelsur: "kr",
  repcheca: "cz",
  republicacheca: "cz",
  chequia: "cz",
  canada: "ca",
  bosniaherzegovina: "ba",
  qatar: "qa",
  suiza: "ch",
  brasil: "br",
  marruecos: "ma",
  haiti: "ht",
  escocia: "gb-sct",
  estadosunidos: "us",
  paraguay: "py",
  australia: "au",
  turquia: "tr",
  alemania: "de",
  curazao: "cw",
  costademarfil: "ci",
  ecuador: "ec",
  paisesbajos: "nl",
  holanda: "nl",
  japon: "jp",
  suecia: "se",
  tunez: "tn",
  belgica: "be",
  egipto: "eg",
  rideiran: "ir",
  iran: "ir",
  nuevazelanda: "nz",
  espana: "es",
  caboverde: "cv",
  arabiasaudi: "sa",
  arabiasaudita: "sa",
  uruguay: "uy",
  francia: "fr",
  senegal: "sn",
  irak: "iq",
  noruega: "no",
  argentina: "ar",
  argelia: "dz",
  austria: "at",
  jordania: "jo",
  portugal: "pt",
  rdcongo: "cd",
  congo: "cd",
  uzbekistan: "uz",
  colombia: "co",
  inglaterra: "gb-eng",
  croacia: "hr",
  ghana: "gh",
  panama: "pa",
};

export function flagCode(teamName) {
  return TEAM_CODES[norm(teamName)] || null;
}

export function flagUrl(teamName, height = 40) {
  const code = flagCode(teamName);
  return code ? `https://flagcdn.com/h${height}/${code}.png` : null;
}
