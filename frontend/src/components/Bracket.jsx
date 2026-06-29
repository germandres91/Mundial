import { flagUrl } from "../utils/flags";

const ROUNDS = [
  { key: "Dieciseisavos de final", title: "Dieciseisavos" },
  { key: "Octavos de final", title: "Octavos" },
  { key: "Cuartos de final", title: "Cuartos" },
  { key: "Semifinales", title: "Semifinales" },
  { key: "Final", title: "Final" },
];

function toTeam(name, meta = {}) {
  if (!name) return null;
  return { equipo: name, ...meta };
}

function matchToCard(k) {
  const finished = k.estado === "FINISHED" && k.goles_local != null && k.goles_visitante != null;
  let winner = null;
  if (finished) {
    if (k.goles_local > k.goles_visitante) winner = toTeam(k.local);
    else if (k.goles_visitante > k.goles_local) winner = toTeam(k.visitante);
  }
  return {
    a: toTeam(k.local),
    b: toTeam(k.visitante),
    scoreA: finished ? k.goles_local : null,
    scoreB: finished ? k.goles_visitante : null,
    winner,
  };
}

function winnersFromRound(cards) {
  return cards.map((m) => m.winner).filter(Boolean);
}

function pairWinners(winners) {
  const pairs = [];
  for (let i = 0; i < winners.length; i += 2) {
    pairs.push({ a: winners[i] || null, b: winners[i + 1] || null });
  }
  return pairs.map((p) => ({
    ...p,
    scoreA: null,
    scoreB: null,
    winner: null,
  }));
}

function buildRounds(knockout) {
  const byPhase = {};
  for (const k of knockout || []) {
    if (!k.fase) continue;
    (byPhase[k.fase] ||= []).push(k);
  }
  for (const phase of Object.keys(byPhase)) {
    byPhase[phase].sort((a, b) => (a.fifa_id || "").localeCompare(b.fifa_id || ""));
  }

  const rounds = [];
  let projectedWinners = null;

  for (const { key } of ROUNDS) {
    if (byPhase[key]?.length) {
      const cards = byPhase[key].map(matchToCard);
      rounds.push(cards);
      projectedWinners = winnersFromRound(cards);
      continue;
    }
    if (projectedWinners?.length) {
      const cards = pairWinners(projectedWinners);
      rounds.push(cards);
      projectedWinners = winnersFromRound(cards);
    } else {
      rounds.push([]);
    }
  }

  return rounds;
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
        {team?.grupo && (
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

export default function Bracket({ knockout = [] }) {
  const rounds = buildRounds(knockout);
  const champion = rounds[rounds.length - 1]?.[0]?.winner || null;
  const hasKnockout = (knockout || []).length > 0;

  if (!hasKnockout) {
    return (
      <div className="card text-center text-sm text-slate-500">
        El cuadro de eliminatorias se mostrará cuando el administrador publique los
        dieciseisavos de final.
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
                {(rounds[ri] || []).map((m, mi) => (
                  <MatchCard key={mi} match={m} showIn={ri > 0} />
                ))}
              </div>
            </div>
          ))}

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
