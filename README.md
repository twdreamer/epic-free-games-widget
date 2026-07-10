# Epic Free Games Widget

macOS [Ubersicht](https://tracesof.net/uebersicht/) widget，顯示 Epic Games Store：

- 目前免費遊戲與領取期限
- 可點擊的領取按鈕與本機已領取標記
- Steam 玩家好評率與可點擊連結
- 下個週期即將開放領取的遊戲
- 網路中斷時顯示最後一次成功抓取的結果

## 安裝

將 `epic-free-games.widget` 複製到 Ubersicht widgets 目錄：

```bash
cp -R epic-free-games.widget "$HOME/Library/Application Support/Übersicht/widgets/"
```

Ubersicht 會自動載入 widget。看板預設位於右上角，排列在 RSI widget 下方。

## 已領取標記

點擊「領取」會開啟 Epic 商店頁面，並在目前這台 Mac 上標記為「已領取」。
再次點擊可以取消標記。這是保存在 Ubersicht `localStorage` 的本機紀錄，
不會讀取或修改 Epic 帳號資料。

## 最後結果快取

每次成功更新時，widget 會在資料夾內寫入 `epic_games_cache.json`。
若 Epic 或 Steam 暫時無法連線，widget 會顯示最後一次成功結果並標示為快取資料。
