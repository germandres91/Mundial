import { flagUrl } from "../utils/flags";

const ROUNDS = [
  { key: "r32", title: "Dieciseisavos" },
  { key: "r16", title: "Octavos" },
  { key: "qf", title: "Cuartos" },
  { key: "sf", title: "Semifinales" },
  { key: "final", title: "Final" },
];

// Orden de siembra estándar para un cuadro de 32 (posiciones de los slots).
function seedOrder(n) {
  let arr = [1, 2];
  while (arr.length < n) {
    const len = arr.length * 2;
    const next = [];
    for (const s of arr) {
      next.push(s);
      next.push(len + 1 - s);
    }
    arr = next;
  }
  return arr;
}

function Flag({ name }) {
  const url = flagUrl(name);
  if (!url) {
    return <span className="h-3.5 w-5 shrink-0 rounded-sm bg-slate-200 dark:bg-slate-700" />;
  }
  return (
    <img
      src={url}
      alt=""
      loading="lazy"
      className="h-3.5 w-5 shrink-0 rounded-sm object-cover ring-1 ring-black/10"
      onError={(e) => {
        e.currentTarget.style.visibility = "hidden";
      }}
    />
  );
}

function TeamRow({ team, score, isWinner, dimmed }) {
  return (
    <div
      className={`flex items-center gap-1.5 px-1.5 py-0.5 ${
        isWinner ? "font-bold" : ""
      } ${dimmed ? "opacity-50" : ""}`}
    >
      {team ? <Flag name={team.equipo} /> : <span className="h-3.5 w-5 shrink-0 rounded-sm bg-slate-200 dark:bg-slate-700" />}
      <span className="flex-1 truncate text-[11px] leading-tight">
        {team ? team.equipo : "Por definir"}
        {team && (
          <span className="ml-1 text-[9px] font-normal text-slate-400">
            {team.posicion}º{team.grupo}
          </span>
        )}
      </span>
      {score != null && (
        <span className="ml-1 w-3 text-right text-[11px] tabular-nums">{score}</span>
      )}
    </div>
  );
}

function MatchCard({ match, showIn }) {
  const { a, b, scoreA, scoreB, winner } = match;
  const aWin = winner && a && winner.equipo === a.equipo;
  const bWin = winner && b && winner.equipo === b.equipo;
  return (
    <div className="tb-match">
      {showIn && <span className="tb-line-in" />}
      <div className="tb-card overflow-hidden rounded-lg border border-slate-200 bg-white text-slate-800 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100">
        <TeamRow team={a} score={scoreA} isWinner={aWin} dimmed={winner && !aWin} />
        <div className="border-t border-slate-100 dark:border-slate-700/70" />
        <TeamRow team={b} score={scoreB} isWinner={bWin} dimmed={winner && !bWin} />
      </div>
    </div>
  );
}

export default function Bracket({ qualified = [], knockout = [] }) {
  const teams = qualified.slice(0, 32);

  const finished = (knockout || []).filter(
    (m) => m.estado === "FINISHED" && m.goles_local != null
  );

  // Busca el resultado real de un cruce por nombres de equipo.
  const findResult = (a, b) => {
    if (!a || !b) return null;
    const m = finished.find(
      (k) =>
        (k.local === a.equipo && k.visitante === b.equipo) ||
        (k.local === b.equipo && k.visitante === a.equipo)
    );
    if (!m) return null;
    const aIsHome = m.local === a.equipo;
    const sA = aIsHome ? m.goles_local : m.goles_visitante;
    const sB = aIsHome ? m.goles_visitante : m.goles_local;
    const winner = sA === sB ? null : sA > sB ? a : b;
    return { scoreA: sA, scoreB: sB, winner };
  };

  const decorate = (pairs) =>
    pairs.map(({ a, b }) => {
      const r = findResult(a, b);
      return {
        a,
        b,
        scoreA: r ? r.scoreA : null,
        scoreB: r ? r.scoreB : null,
        winner: r ? r.winner : null,
      };
    });

  // Construye la primera ronda (32 -> 16 cruces) por siembra.
  const order = seedOrder(32);
  const slots = order.map((seed) => teams[seed - 1] || null);
  const firstPairs = [];
  for (let i = 0; i < 32; i += 2) firstPairs.push({ a: slots[i], b: slots[i + 1] });

  const rounds = [];
  let current = decorate(firstPairs);
  rounds.push(current);
  for (let r = 1; r < ROUNDS.length; r++) {
    const winners = current.map((m) => m.winner);
    const pairs = [];
    for (let i = 0; i < winners.length; i += 2) {
      pairs.push({ a: winners[i] || null, b: winners[i + 1] || null });
    }
    current = decorate(pairs);
    rounds.push(current);
  }

  const champion = rounds[rounds.length - 1][0]?.winner || null;

  if (!teams.length) {
    return (
      <div className="card text-center text-sm text-slate-500">
        El cuadro se generará cuando haya posiciones de grupo disponibles.
      </div>
    );
  }

  return (
    <div className="card p-3">
      <div className="tb-scroll">
        <div className="tb">
          {ROUNDS.map((round, ri) => (
            <div key={round.key} className="tb-col">
              <div className="tb-col-title">{round.title}</div>
              <div className="tb-body">
                {rounds[ri].map((m, mi) => (
                  <MatchCard key={mi} match={m} showIn={ri > 0} />
                ))}
              </div>
            </div>
          ))}

          {/* Columna del campeón */}
          <div className="tb-col" style={{ minWidth: 180 }}>
            <div className="tb-col-title">Campeón</div>
            <div className="tb-body flex items-center justify-center">
              <div className="tb-match !flex-none">
                <span className="tb-line-in" />
                <div className="flex flex-col items-center gap-1 rounded-2xl border border-amber-400/60 bg-gradient-to-b from-amber-400/20 to-amber-500/5 px-4 py-4 text-center">
                  <span className="text-3xl">🏆</span>
                  {champion ? (
                    <>
                      <Flag name={champion.equipo} />
                      <span className="text-sm font-extrabold">{champion.equipo}</span>
                    </>
                  ) : (
                    <span className="text-xs text-slate-500">Por definir</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
