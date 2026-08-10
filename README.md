# Epic Free Games Widget

macOS [Ubersicht](https://tracesof.net/uebersicht/) widget，顯示 Epic Games Store：

- 目前免費遊戲與領取期限
- 可點擊的領取按鈕與本機已領取標記
- Steam 玩家好評率與可點擊連結
- 下個週期即將開放領取的遊戲
- 每日自動更新，也可以按「更新」立即重新抓取
- 網路中斷時顯示最後一次成功抓取的結果
- 可縮小成只顯示標題，並記住上次的顯示狀態
- 可解除位置鎖定後拖動標題列，並記住調整後的位置

## 安裝

將專案直接 clone 到 Ubersicht widgets 目錄：

```bash
git clone https://github.com/twdreamer/epic-free-games-widget.git \
  "$HOME/Library/Application Support/Übersicht/widgets/epic-free-games.widget"
```

Ubersicht 會自動載入 widget。看板預設位於右上角，排列在 RSI widget 下方。

## 已領取標記

點擊「領取」會開啟 Epic 商店頁面，並在目前這台 Mac 上標記為「已領取」。
再次點擊可以取消標記。這是保存在 Ubersicht `localStorage` 的本機紀錄，
不會讀取或修改 Epic 帳號資料。

## 最後結果快取

每次成功更新時，widget 會在資料夾內寫入 `epic_games_cache.json`。
若 Epic 或 Steam 暫時無法連線，widget 會顯示最後一次成功結果並標示為快取資料。
遊戲圖片也會下載到本機 `image_cache/`，避免 Epic CDN 圖片暫時失效時破圖。
圖片會轉成最長邊 160px、品質 82 的 JPEG 縮圖，降低磁碟與常駐記憶體用量。
當快取內所有遊戲的免費週期都結束後，widget 會刪除 JSON 快取和本機圖片。

## 移動與縮小

按標題列右側的鎖頭按鈕解除位置鎖定後，可以拖動標題列調整 widget 位置；
拖到想要的位置後，再按一次鎖頭即可避免誤移動。位置會保存在 Ubersicht 本機。

按「−」可以把 widget 縮小成只顯示標題，縮小後點擊標題或「＋」即可展開。
