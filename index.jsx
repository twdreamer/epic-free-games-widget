import { run } from "uebersicht"

export const refreshFrequency = 1000 * 60 * 60 * 24

const epicCommand = `
cd "$HOME/Library/Application Support/Übersicht/widgets/epic-free-games.widget" && /usr/bin/python3 epic_games.py
`
const collapseKey = "epic-free-games-widget:collapsed"
const positionKey = "epic-free-games-widget:position"
const defaultPosition = { x: 0, y: 0 }

let blockHeaderClickUntil = 0
let activeDragPosition = null

const loadPosition = () => {
  try {
    const position = JSON.parse(window.localStorage.getItem(positionKey) || "null")
    return Number.isFinite(position && position.x) && Number.isFinite(position && position.y)
      ? position
      : defaultPosition
  } catch (error) {
    return defaultPosition
  }
}

const savePosition = (position) =>
  window.localStorage.setItem(positionKey, JSON.stringify(position))

const widgetRoot = (element) => element && element.closest(".widget")

const applyPosition = (element, position) => {
  const root = widgetRoot(element)
  if (!root) return position

  const requestedPosition = activeDragPosition || position || defaultPosition
  root.style.transform = `translate3d(${requestedPosition.x}px, ${requestedPosition.y}px, 0)`

  if (activeDragPosition) return requestedPosition

  const rect = root.getBoundingClientRect()
  const correctionX =
    rect.width >= window.innerWidth
      ? -rect.left
      : rect.left < 0
        ? -rect.left
        : rect.right > window.innerWidth
          ? window.innerWidth - rect.right
          : 0
  const correctionY =
    rect.height >= window.innerHeight
      ? -rect.top
      : rect.top < 0
        ? -rect.top
        : rect.bottom > window.innerHeight
          ? window.innerHeight - rect.bottom
          : 0

  if (!correctionX && !correctionY) return requestedPosition

  const fittedPosition = {
    x: Math.round(requestedPosition.x + correctionX),
    y: Math.round(requestedPosition.y + correctionY),
  }
  root.style.transform = `translate3d(${fittedPosition.x}px, ${fittedPosition.y}px, 0)`
  savePosition(fittedPosition)
  return fittedPosition
}

const startDrag = (event, isPositionUnlocked, position, dispatch) => {
  if (
    !isPositionUnlocked ||
    event.button !== 0 ||
    event.target.closest("button, a, input, select, textarea")
  ) {
    return
  }

  const dragHandle = event.currentTarget
  const root = widgetRoot(dragHandle)
  if (!root) return

  event.preventDefault()

  const startX = event.clientX
  const startY = event.clientY
  const startRect = root.getBoundingClientRect()
  const startPosition = loadPosition()
  const previousZIndex = root.style.zIndex
  const previousCursor = dragHandle.style.cursor
  const previousUserSelect = document.body.style.userSelect
  let nextPosition = startPosition
  let didMove = false

  root.style.zIndex = "10000"
  dragHandle.style.cursor = "grabbing"
  document.body.style.userSelect = "none"
  activeDragPosition = startPosition

  const handleMouseMove = (moveEvent) => {
    const deltaX = moveEvent.clientX - startX
    const deltaY = moveEvent.clientY - startY
    const boundedX = Math.min(
      window.innerWidth - startRect.right,
      Math.max(-startRect.left, deltaX),
    )
    const boundedY = Math.min(
      window.innerHeight - startRect.bottom,
      Math.max(-startRect.top, deltaY),
    )

    didMove = didMove || Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2
    nextPosition = {
      x: Math.round(startPosition.x + boundedX),
      y: Math.round(startPosition.y + boundedY),
    }
    activeDragPosition = nextPosition
    applyPosition(dragHandle, nextPosition)
  }

  const handleMouseUp = () => {
    window.removeEventListener("mousemove", handleMouseMove)
    window.removeEventListener("mouseup", handleMouseUp)
    window.removeEventListener("blur", handleMouseUp)
    root.style.zIndex = previousZIndex
    dragHandle.style.cursor = previousCursor
    document.body.style.userSelect = previousUserSelect

    if (didMove) {
      savePosition(nextPosition)
      blockHeaderClickUntil = Date.now() + 120
    }

    activeDragPosition = null
    if (didMove) {
      dispatch({ type: "POSITION_CHANGED", position: nextPosition })
    } else {
      applyPosition(dragHandle, startPosition)
    }
  }

  window.addEventListener("mousemove", handleMouseMove)
  window.addEventListener("mouseup", handleMouseUp)
  window.addEventListener("blur", handleMouseUp)
}

const LockIcon = ({ isPositionUnlocked }) => (
  <svg
    viewBox="0 0 24 24"
    width="14"
    height="14"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <rect x="5" y="10" width="14" height="10" rx="2" />
    <path
      d={
        isPositionUnlocked
          ? "M8 10V7a4 4 0 0 1 7.5-2"
          : "M8 10V7a4 4 0 0 1 8 0v3"
      }
    />
  </svg>
)

const PositionLockButton = ({ isPositionUnlocked, dispatch }) => (
  <button
    onClick={(event) => {
      event.stopPropagation()
      dispatch({
        type: "POSITION_LOCK_TOGGLED",
        isPositionUnlocked: !isPositionUnlocked,
      })
    }}
    title={isPositionUnlocked ? "鎖定位置" : "解除位置鎖定"}
    aria-label={isPositionUnlocked ? "鎖定位置" : "解除位置鎖定"}
    aria-pressed={isPositionUnlocked}
    style={{
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      width: 28,
      height: 28,
      padding: 0,
      cursor: "pointer",
      border: isPositionUnlocked
        ? "1px solid rgba(126, 210, 255, 0.58)"
        : "1px solid rgba(255,255,255,0.25)",
      background: isPositionUnlocked
        ? "rgba(72, 166, 216, 0.24)"
        : "rgba(255,255,255,0.12)",
      color: isPositionUnlocked ? "#9edbff" : "white",
      borderRadius: 8,
    }}
  >
    <LockIcon isPositionUnlocked={isPositionUnlocked} />
  </button>
)

const loadCollapsed = () => window.localStorage.getItem(collapseKey) === "true"
const saveCollapsed = (isCollapsed) =>
  window.localStorage.setItem(collapseKey, String(isCollapsed))

const toggleCollapsed = (isCollapsed, dispatch) => {
  const nextCollapsed = !isCollapsed
  saveCollapsed(nextCollapsed)
  dispatch({ type: "COLLAPSE_TOGGLED", isCollapsed: nextCollapsed })
}

const refreshEpic = async (dispatch) => {
  dispatch({ type: "REFRESH_STARTED" })

  try {
    const output = await run(epicCommand)
    dispatch({ type: "OUTPUT_UPDATED", output, error: null })
  } catch (error) {
    dispatch({ type: "OUTPUT_UPDATED", output: "", error: String(error) })
  }
}

export const command = epicCommand

export const className = `
  top: 185px;
  left: calc(100% - 480px);
  width: fit-content;
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

const panelStyle = (isCollapsed = false) => ({
  width: isCollapsed ? "fit-content" : 456,
  boxSizing: "border-box",
  padding: "12px 14px 13px",
  background: "rgba(8, 12, 20, 0.84)",
  borderRadius: 14,
  boxShadow: "0 10px 28px rgba(0, 0, 0, 0.28)",
  backdropFilter: "blur(10px)",
})

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

const Header = ({
  data = {},
  isCollapsed,
  isLoading,
  isPositionUnlocked,
  position,
  dispatch,
}) => (
  <div
    ref={(element) => applyPosition(element, position)}
    onMouseDown={(event) =>
      startDrag(event, isPositionUnlocked, position, dispatch)
    }
    onClickCapture={(event) => {
      if (Date.now() < blockHeaderClickUntil) {
        event.preventDefault()
        event.stopPropagation()
      }
    }}
    style={{
      display: "flex",
      justifyContent: isCollapsed ? "flex-start" : "space-between",
      alignItems: "center",
      gap: isCollapsed ? 8 : 0,
      cursor: isPositionUnlocked ? "grab" : "default",
    }}
  >
    <div
      onClick={
        isCollapsed ? () => toggleCollapsed(isCollapsed, dispatch) : undefined
      }
      title={isCollapsed ? "展開 Epic Games 免費遊戲" : undefined}
      style={{
        cursor: isPositionUnlocked ? "grab" : isCollapsed ? "pointer" : "default",
      }}
    >
      <div style={{ fontWeight: 850, fontSize: 14 }}>Epic Games 免費遊戲</div>
      {!isCollapsed ? (
        <div style={{ opacity: 0.68, fontSize: 11 }}>
          每日更新｜{data.updatedDate ? `${data.updatedDate} ` : ""}
          {data.updatedAt || "--:--"}
          {data.cached ? "｜快取資料" : ""}
        </div>
      ) : null}
    </div>
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <PositionLockButton
        isPositionUnlocked={isPositionUnlocked}
        dispatch={dispatch}
      />
      {!isCollapsed ? (
        <button
          onClick={() => refreshEpic(dispatch)}
          disabled={isLoading}
          style={{
            cursor: isLoading ? "default" : "pointer",
            border: "1px solid rgba(255,255,255,0.25)",
            background: "rgba(255,255,255,0.12)",
            color: "white",
            opacity: isLoading ? 0.62 : 1,
            borderRadius: 8,
            padding: "4px 8px",
            fontSize: 11,
          }}
        >
          {isLoading ? "更新中" : "更新"}
        </button>
      ) : null}
      <button
        onClick={() => toggleCollapsed(isCollapsed, dispatch)}
        title={isCollapsed ? "展開" : "縮小"}
        aria-label={isCollapsed ? "展開" : "縮小"}
        style={{
          width: 28,
          height: 28,
          padding: 0,
          cursor: "pointer",
          border: "1px solid rgba(255,255,255,0.25)",
          background: "rgba(255,255,255,0.12)",
          color: "white",
          borderRadius: 8,
          fontSize: 18,
          lineHeight: "26px",
        }}
      >
        {isCollapsed ? "+" : "−"}
      </button>
    </div>
  </div>
)

export const updateState = (event, previousState) => {
  if (event.type === "REFRESH_STARTED") {
    return { ...previousState, isLoading: true }
  }

  if (event.type === "OUTPUT_UPDATED") {
    return {
      ...previousState,
      output: event.output,
      error: event.error,
      isLoading: false,
    }
  }

  if (event.type === "CLAIM_TOGGLED") {
    return {
      ...previousState,
      claimed: { ...(previousState.claimed || {}), [claimKey(event.game)]: event.claimed },
    }
  }

  if (event.type === "COLLAPSE_TOGGLED") {
    return { ...previousState, isCollapsed: event.isCollapsed }
  }

  if (event.type === "POSITION_LOCK_TOGGLED") {
    return {
      ...previousState,
      isPositionUnlocked: event.isPositionUnlocked,
    }
  }

  if (event.type === "POSITION_CHANGED") {
    return { ...previousState, position: event.position }
  }

  return { ...previousState, output: event.output, error: event.error, isLoading: false }
}

export const initialState = {
  output: "",
  error: null,
  claimed: {},
  isLoading: false,
  isCollapsed: null,
  isPositionUnlocked: false,
  position: null,
}

export const render = (
  {
    output,
    error,
    claimed = {},
    isLoading,
    isCollapsed,
    isPositionUnlocked = false,
  },
  dispatch,
) => {
  const collapsed = isCollapsed == null ? loadCollapsed() : isCollapsed
  const position = loadPosition()

  if (collapsed) {
    return (
      <div style={panelStyle(collapsed)}>
        <Header
          isCollapsed={collapsed}
          isLoading={isLoading}
          isPositionUnlocked={isPositionUnlocked}
          position={position}
          dispatch={dispatch}
        />
      </div>
    )
  }

  if (!output && !error) {
    return (
      <div style={panelStyle(collapsed)}>
        <Header
          isCollapsed={collapsed}
          isLoading={isLoading}
          isPositionUnlocked={isPositionUnlocked}
          position={position}
          dispatch={dispatch}
        />
        <div style={{ marginTop: 10, opacity: 0.62, fontWeight: 750 }}>
          讀取最後一次結果中
        </div>
      </div>
    )
  }

  let data = {}
  try {
    data = output ? JSON.parse(output) : {}
  } catch (parseError) {
    data = { error: String(parseError) }
  }

  if (error || data.error) {
    return (
      <div style={panelStyle(collapsed)}>
        <Header
          isCollapsed={collapsed}
          isLoading={isLoading}
          isPositionUnlocked={isPositionUnlocked}
          position={position}
          dispatch={dispatch}
        />
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
    <div style={panelStyle(collapsed)}>
      <Header
        data={data}
        isCollapsed={collapsed}
        isLoading={isLoading}
        isPositionUnlocked={isPositionUnlocked}
        position={position}
        dispatch={dispatch}
      />
      {data.cached ? (
        <div
          title={data.cacheReason || ""}
          style={{
            marginTop: 9,
            padding: "6px 8px",
            border: "1px solid rgba(255, 196, 94, 0.28)",
            background: "rgba(212, 142, 34, 0.14)",
            color: "#ffd98c",
            borderRadius: 8,
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          使用最後一次成功結果
        </div>
      ) : null}
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
