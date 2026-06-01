import { run } from "uebersicht"

export const refreshFrequency = 1000 * 60 * 60 * 6

export const command = `
cd "$HOME/Library/Application Support/Übersicht/widgets/epic-free-games.widget" && /usr/bin/python3 epic_games.py
`

export const className = `
  top: 185px;
  right: 24px;
  width: 456px;
  color: white;
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
  font-size: 13px;
  line-height: 1.35;
  z-index: 9998;
`

const shellEscape = (value) => `'${String(value).replace(/'/g, "'\\''")}'`
const openUrl = (url) => url && run(`/usr/bin/open ${shellEscape(url)}`)
const claimKey = (game) => `epic-free-games-widget:claimed:${game.epicUrl}`
const isClaimed = (game) => window.localStorage.getItem(claimKey(game)) === "true"
const saveClaim = (game, claimed) =>
  window.localStorage.setItem(claimKey(game), String(claimed))

const panelStyle = {
  padding: "12px 14px 13px",
  background: "rgba(8, 12, 20, 0.84)",
  borderRadius: 14,
  boxShadow: "0 10px 28px rgba(0, 0, 0, 0.28)",
  backdropFilter: "blur(10px)",
}

const SectionTitle = ({ children }) => (
  <div
    style={{
      margin: "12px 0 7px",
      color: "rgba(255,255,255,0.62)",
      fontSize: 11,
      fontWeight: 800,
      letterSpacing: 0.7,
    }}
  >
    {children}
  </div>
)

const SteamScore = ({ steam }) => (
  <button
    onClick={(event) => {
      event.stopPropagation()
      openUrl(steam.url)
    }}
    style={{
      cursor: "pointer",
      border: "1px solid rgba(110, 198, 255, 0.28)",
      background: "rgba(34, 124, 184, 0.18)",
      color: "#9edbff",
      borderRadius: 8,
      padding: "3px 7px",
      fontSize: 11,
      fontWeight: 750,
      whiteSpace: "nowrap",
    }}
  >
    {steam.rating == null ? "Steam 搜尋" : `Steam ${steam.rating}%`}
  </button>
)

const ClaimButton = ({ game, claimed, dispatch }) => {
  const toggle = (event) => {
    event.stopPropagation()
    const nextClaimed = !claimed
    saveClaim(game, nextClaimed)
    dispatch({ type: "CLAIM_TOGGLED", game, claimed: nextClaimed })
    if (nextClaimed) openUrl(game.epicUrl)
  }

  return (
    <button
      onClick={toggle}
      title={claimed ? "點擊可取消已領取標記" : "開啟 Epic 領取頁並標記為已領取"}
      style={{
        cursor: "pointer",
        border: claimed
          ? "1px solid rgba(109, 226, 149, 0.38)"
          : "1px solid rgba(255, 196, 94, 0.4)",
        background: claimed ? "rgba(46, 160, 91, 0.22)" : "rgba(212, 142, 34, 0.2)",
        color: claimed ? "#a8f0bd" : "#ffd98c",
        borderRadius: 8,
        padding: "3px 7px",
        fontSize: 11,
        fontWeight: 750,
        whiteSpace: "nowrap",
      }}
    >
      {claimed ? "已領取 ✓" : "領取"}
    </button>
  )
}

const Game = ({ game, current, claimed, dispatch }) => (
  <div
    onClick={() => openUrl(game.epicUrl)}
    style={{
      display: "grid",
      gridTemplateColumns: "58px minmax(0, 1fr) auto",
      gap: 10,
      alignItems: "center",
      padding: "7px 0",
      cursor: "pointer",
      borderTop: "1px solid rgba(255,255,255,0.08)",
    }}
  >
    {game.image ? (
      <img
        src={game.image}
        style={{ width: 58, height: 32, borderRadius: 6, objectFit: "cover" }}
      />
    ) : (
      <div style={{ width: 58, height: 32 }} />
    )}
    <div style={{ minWidth: 0 }}>
      <div
        style={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          fontWeight: 820,
        }}
      >
        {game.title}
      </div>
      <div style={{ opacity: 0.62, fontSize: 11 }}>
        {current ? `免費至 ${game.end}` : `${game.start} 開放領取`}
      </div>
    </div>
    {current ? (
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <ClaimButton game={game} claimed={claimed} dispatch={dispatch} />
        {game.steam ? <SteamScore steam={game.steam} /> : null}
      </div>
    ) : null}
  </div>
)

const Header = ({ updatedAt }) => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
    <div>
      <div style={{ fontWeight: 850, fontSize: 14 }}>Epic Games 免費遊戲</div>
      <div style={{ opacity: 0.68, fontSize: 11 }}>每 6 小時更新｜{updatedAt || "--:--"}</div>
    </div>
    <button
      onClick={() => window.location.reload()}
      style={{
        cursor: "pointer",
        border: "1px solid rgba(255,255,255,0.25)",
        background: "rgba(255,255,255,0.12)",
        color: "white",
        borderRadius: 8,
        padding: "4px 8px",
        fontSize: 11,
      }}
    >
      更新
    </button>
  </div>
)

export const updateState = (event, previousState) => {
  if (event.type === "CLAIM_TOGGLED") {
    return {
      ...previousState,
      claimed: { ...(previousState.claimed || {}), [claimKey(event.game)]: event.claimed },
    }
  }

  return { ...previousState, output: event.output, error: event.error }
}

export const initialState = { output: "", error: null, claimed: {} }

export const render = ({ output, error, claimed = {} }, dispatch) => {
  let data = {}
  try {
    data = output ? JSON.parse(output) : {}
  } catch (parseError) {
    data = { error: String(parseError) }
  }

  if (error || data.error) {
    return (
      <div style={panelStyle}>
        <Header />
        <div style={{ marginTop: 10, color: "#ff9da4", fontWeight: 750 }}>
          無法取得 Epic 免費遊戲
        </div>
        <div style={{ marginTop: 4, opacity: 0.65, fontSize: 11 }}>
          {data.error || String(error)}
        </div>
      </div>
    )
  }

  const current = data.current || []
  const upcoming = data.upcoming || []

  return (
    <div style={panelStyle}>
      <Header updatedAt={data.updatedAt} />
      <SectionTitle>目前免費</SectionTitle>
      {current.length ? (
        current.map((game) => (
          <Game
            key={`current-${game.title}`}
            game={game}
            current
            claimed={claimed[claimKey(game)] == null ? isClaimed(game) : claimed[claimKey(game)]}
            dispatch={dispatch}
          />
        ))
      ) : (
        <div style={{ opacity: 0.62 }}>目前沒有免費項目</div>
      )}
      <SectionTitle>下個週期</SectionTitle>
      {upcoming.length ? (
        upcoming.map((game) => <Game key={`upcoming-${game.title}`} game={game} />)
      ) : (
        <div style={{ opacity: 0.62 }}>尚未公布</div>
      )}
    </div>
  )
}
