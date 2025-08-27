/**
 * きぐるみ予約システム
 * Frontend JavaScript - 完全修正版
 */

// =====================================
// 名前空間とモジュール
// =====================================
const KigurumiReservationSystem = (() => {
  // =====================================
  // 設定と定数
  // =====================================
  // きぐるみの定義
  const KIGURUMI_LIST = [
    {
      id: "きぐるみ1 ※本社保管",
      display: "きぐるみ1 ※本社保管",
      dataKey: "きぐるみ1 ※本社保管",
    },
    {
      id: "きぐるみ2（空気） ※本社保管",
      display: "きぐるみ2（空気） ※本社保管",
      dataKey: "きぐるみ2（空気） ※本社保管",
    },
    {
      id: "きぐるみ3（たてがみに不具合あり） ※札幌支店保管",
      display: "きぐるみ3（たてがみに不具合あり） ※札幌支店保管",
      dataKey: "きぐるみ3（たてがみに不具合あり） ※札幌支店保管",
    },
    {
      id: "きぐるみ4 ※旭川保管",
      display: "きぐるみ4 ※旭川保管",
      dataKey: "きぐるみ4 ※旭川保管",
    },
    {
      id: "きぐるみ5 ※帯広保管",
      display: "きぐるみ5 ※帯広保管",
      dataKey: "きぐるみ5 ※帯広保管",
    },
    {
      id: "きぐるみ6（空気） ※釧路保管",
      display: "きぐるみ6（空気） ※釧路保管",
      dataKey: "きぐるみ6（空気） ※釧路保管",
    },
    {
      id: "きぐるみ7 ※函館保管",
      display: "きぐるみ7 ※函館保管",
      dataKey: "きぐるみ7 ※函館保管",
    },
    {
      id: "コンシェルジュのみ（きぐるみ不要）",
      display: "コンシェルジュのみ（きぐるみ不要）",
      dataKey: "コンシェルジュのみ（きぐるみ不要）",
    },
  ];

  // Google Apps Script のデプロイ URL
  const GAS_ENDPOINT =
    "https://script.google.com/macros/s/AKfycbyEHl9JPivz818Wq63xyxiHL2wq_eBODviMwE14SaJ4DzD_aFR_1dhl_2oG8l6bomfv/exec";

  // Firebase設定（外部設定ファイルから読み込み）
  const FIREBASE_CONFIG = window.AppConfig?.firebase || {
    apiKey: "AIzaSyCB_Yox8ExDJw6JyGy_Doomi0kAOFiIRDA",
    authDomain: "kigurumi-reserve.firebaseapp.com",
    projectId: "kigurumi-reserve",
    storageBucket: "kigurumi-reserve.appspot.com",
    messagingSenderId: "96443629109",
    appId: "1:96443629109:web:792feab35bffe733b2bb7c",
  };

  // セッション有効期間（24時間）
  const MAX_SESSION_DURATION = 1000 * 60 * 60 * 24;

  // アプリケーション状態
  const state = {
    calendarData: {}, // カレンダーデータ
    selectedCharacter: "all", // 現在選択中のきぐるみ
    advanceDays: 15, // 予約可能日数
    currentDate: new Date(), // 現在の日付
    currentYear: null, // 現在表示中の年
    currentMonth: null, // 現在表示中の月
    isLoggedIn: false, // ログイン状態
    isInitialized: false, // 初期化状態
    authProcessing: false, // 認証処理中フラグ
    csrfToken: null, // CSRFトークン
  };

  // =====================================
  // DOM要素セレクタ
  // =====================================
  const DOM = {
    mainContent: () => document.querySelector(".container.mx-auto"),
    calendarBody: () => document.getElementById("calendar-body"),
    currentMonth: () => document.getElementById("current-month"),
    prevMonthBtn: () => document.getElementById("prev-month"),
    nextMonthBtn: () => document.getElementById("next-month"),
    dateInput: () => document.getElementById("date"),
    characterSelect: () => document.getElementById("character-select"),
    characterField: () => document.getElementById("character"),
    conciergeSection: () => document.getElementById("concierge-section"),
    conciergeRadios: () => document.querySelectorAll('input[name="concierge"]'),
    advanceDaysText: () => document.getElementById("advance-days-notice"),
    reservationForm: () => document.getElementById("reservation-form"),
    submitBtn: () => document.querySelector('button[type="submit"]'),
    messageDiv: () => document.getElementById("message"),
    phoneInput: () => document.getElementById("phone"),
  };

  // =====================================
  // セキュリティ関数
  // =====================================

  /**
   * CSRFトークンを生成
   * @returns {string} CSRFトークン
   */
  const generateCSRFToken = () => {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  };

  /**
   * セッション用CSRFトークンを取得または生成
   * @returns {string} CSRFトークン
   */
  const getCSRFToken = () => {
    if (!state.csrfToken) {
      state.csrfToken = generateCSRFToken();
      // セッションストレージに保存（ページリロード対応）
      sessionStorage.setItem('csrfToken', state.csrfToken);
      console.log("🔐 新しいCSRFトークンを生成:", state.csrfToken.substring(0, 8) + "...");
    }
    return state.csrfToken;
  };

  /**
   * CSRFトークンを初期化
   */
  const initializeCSRFToken = () => {
    // セッションストレージから復元を試行
    const savedToken = sessionStorage.getItem('csrfToken');
    if (savedToken && savedToken.length === 64) {
      state.csrfToken = savedToken;
      console.log("🔐 CSRFトークンを復元:", savedToken.substring(0, 8) + "...");
    } else {
      // 新しいトークンを生成
      getCSRFToken();
    }
  };

  // =====================================
  // ユーティリティ関数
  // =====================================

  /**
   * 日付をISO形式（YYYY-MM-DD）に変換
   * @param {Date} date - 日付オブジェクト
   * @returns {string} - ISO形式の日付文字列
   */
  const formatDateISO = (date) => {
    const year = date.getFullYear();
    const month = ("0" + (date.getMonth() + 1)).slice(-2);
    const day = ("0" + date.getDate()).slice(-2);
    return `${year}-${month}-${day}`;
  };

  /**
   * 選択肢を作成
   * @param {string} value - 値
   * @param {string} text - 表示テキスト
   * @returns {HTMLOptionElement} - オプション要素
   */
  const createOption = (value, text) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    return option;
  };

  /**
   * エラーメッセージを表示
   * @param {HTMLElement} messageElement - メッセージ要素
   * @param {string} message - 表示するメッセージ
   */
  const showErrorMessage = (messageElement, message) => {
    if (!messageElement) {
      alert(message); // フォールバックとしてアラートを表示
      return;
    }

    messageElement.textContent = message;
    messageElement.className =
      "mt-4 text-center text-red-600 block text-xs sm:text-sm md:text-base";
    messageElement.style.display = "block";
  };

  // =====================================
  // API通信
  // =====================================
  /**
   * JSONP通信を安全に実行（失敗時に2回まで再試行）
   * @param {Object} options - APIリクエストオプション
   * @param {number} retryCount - リトライ回数（初回は省略可）
   */
  const safeInvokeJsonpApi = (options = {}, retryCount = 0) => {
    invokeJsonpApi({
      ...options,
      errorCallback: () => {
        if (retryCount < 2) {
          // リトライ回数を増やす
          console.warn(
            `JSONPリトライ: ${options.action} (${retryCount + 1}/2)`
          );
          setTimeout(() => safeInvokeJsonpApi(options, retryCount + 1), 1000); // 待機時間を延長
        } else {
          console.error(`JSONP失敗: ${options.action}`);
          if (options.errorCallback) options.errorCallback();
        }
      },
    });
  };

  /**
   * JSONP APIを呼び出す汎用関数
   * @param {Object} options - APIリクエストオプション
   * @param {string} options.action - 実行するアクション
   * @param {Function} options.callback - 成功時のコールバック関数
   * @param {Function} [options.errorCallback] - エラー時のコールバック関数
   * @param {Object} [options.data] - 送信データ
   */
  const invokeJsonpApi = (options) => {
    const script = document.createElement("script");
    const callbackName = `callback_${Date.now()}_${Math.floor(
      Math.random() * 1000
    )}`;

    // グローバルスコープにコールバック関数を定義
    window[callbackName] = (data) => {
      if (options.callback) {
        options.callback(data);
      }

      // 不要になったスクリプトとコールバックを削除
      document.body.removeChild(script);
      delete window[callbackName];
    };

    // URLパラメータを構築
    let url = `${GAS_ENDPOINT}?action=${options.action}&callback=${callbackName}`;

    // データがある場合は追加
    if (options.data) {
      const encodedData = encodeURIComponent(JSON.stringify(options.data));
      url += `&data=${encodedData}`;
    }

    // スクリプトのURL設定とページに追加
    script.src = url;
    document.body.appendChild(script);

    // エラーハンドリング（タイムアウト設定）
    const timeout = setTimeout(() => {
      if (options.errorCallback) {
        options.errorCallback();
      }

      // クリーンアップ
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
      delete window[callbackName];
    }, 10000); // 10秒タイムアウト

    script.onerror = () => {
      clearTimeout(timeout);
      if (options.errorCallback) {
        options.errorCallback();
      }

      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
      delete window[callbackName];
    };

    // 成功時はタイムアウトをクリア
    const originalCallback = window[callbackName];
    window[callbackName] = (data) => {
      clearTimeout(timeout);
      originalCallback(data);
    };
  };

  /**
   * 予約必要日数を取得する
   */
  const fetchAdvanceDays = () => {
    console.log("予約日数取得開始");

    // 簡単なJSONP呼び出し
    const script = document.createElement("script");
    const callbackName = `advanceCallback_${Date.now()}`;

    window[callbackName] = (data) => {
      console.log("予約日数データ受信:", data);
      if (data && data.advanceDays) {
        state.advanceDays = data.advanceDays;
        updateMinDate();
        updateAdvanceDaysText();
        
        // 予約日数取得後にカレンダー表示月を正しく設定
        const minReservationDate = new Date(state.currentDate);
        minReservationDate.setDate(state.currentDate.getDate() + state.advanceDays);
        state.currentYear = minReservationDate.getFullYear();
        state.currentMonth = minReservationDate.getMonth();
        
        // カレンダーを再描画
        renderCalendar(state.currentYear, state.currentMonth);
      }
      document.body.removeChild(script);
      delete window[callbackName];
    };

    // エラー処理
    const timeout = setTimeout(() => {
      console.log("予約日数取得タイムアウト - デフォルト値使用");
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
      delete window[callbackName];
      // デフォルト値でUI更新
      updateMinDate();
      updateAdvanceDaysText();
      
      // タイムアウト時もカレンダー表示月を正しく設定
      const minReservationDate = new Date(state.currentDate);
      minReservationDate.setDate(state.currentDate.getDate() + state.advanceDays);
      state.currentYear = minReservationDate.getFullYear();
      state.currentMonth = minReservationDate.getMonth();
      
      // カレンダーを再描画
      renderCalendar(state.currentYear, state.currentMonth);
    }, 3000);

    script.onerror = () => {
      console.log("予約日数取得エラー - デフォルト値使用");
      clearTimeout(timeout);
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
      delete window[callbackName];
      updateMinDate();
      updateAdvanceDaysText();
      
      // エラー時もカレンダー表示月を正しく設定
      const minReservationDate = new Date(state.currentDate);
      minReservationDate.setDate(state.currentDate.getDate() + state.advanceDays);
      state.currentYear = minReservationDate.getFullYear();
      state.currentMonth = minReservationDate.getMonth();
      
      // カレンダーを再描画
      renderCalendar(state.currentYear, state.currentMonth);
    };

    // 成功時はタイムアウトをクリア
    const originalCallback = window[callbackName];
    window[callbackName] = (data) => {
      clearTimeout(timeout);
      originalCallback(data);
    };

    script.src = `${GAS_ENDPOINT}?action=getAdvanceDays&callback=${callbackName}`;
    document.body.appendChild(script);
  };

  /**
   * カレンダーデータを取得する
   */
  const fetchCalendarData = () => {
    const calendarBody = DOM.calendarBody();

    // データ読み込み中の表示
    if (calendarBody) {
      calendarBody.innerHTML =
        '<tr><td colspan="7" class="text-center py-8"><div class="animate-pulse">データを読み込み中です...</div></td></tr>';
    }

    // 直接JSONPでデータ取得を試行（疎通確認をスキップ）
    console.log("カレンダーデータ取得開始");

    // 簡単なJSONP呼び出しに変更
    const script = document.createElement("script");
    const callbackName = `calendarCallback_${Date.now()}`;

    window[callbackName] = (data) => {
      console.log("📥 カレンダーデータ受信:", data);
      handleCalendarDataSuccess(data);
      document.body.removeChild(script);
      delete window[callbackName];
    };
    
    console.log("🎯 コールバック関数定義:", callbackName, typeof window[callbackName]);

    // エラー処理とタイムアウト
    const timeout = setTimeout(() => {
      console.log("カレンダーデータ取得タイムアウト");
      handleCalendarDataError();
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
      delete window[callbackName];
    }, 15000); // 15秒に延長

    script.onerror = (error) => {
      console.error("📡 スクリプトロードエラー:", error);
      clearTimeout(timeout);
      handleCalendarDataError();
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
      delete window[callbackName];
    };

    // 成功時はタイムアウトをクリア
    const originalCallback = window[callbackName];
    window[callbackName] = (data) => {
      clearTimeout(timeout);
      originalCallback(data);
    };

    const url = `${GAS_ENDPOINT}?action=getCalendarData&callback=${callbackName}`;
    console.log("📡 JSONP URL:", url);
    script.src = url;
    document.body.appendChild(script);
  };

  /**
   * カレンダーデータ取得成功時の処理
   */
  const handleCalendarDataSuccess = (data) => {
    const calendarBody = DOM.calendarBody();
    console.log("データ処理開始:", data);

    if (!data || Object.keys(data).length === 0) {
      console.log("データが空または無効");
      if (calendarBody) {
        calendarBody.innerHTML =
          '<tr><td colspan="7" class="text-center py-8 text-orange-600">データが取得できませんでした。<br>テスト用にダミーデータで表示します。<br><button onclick="location.reload()" class="mt-2 bg-cyan-500 text-white px-4 py-2 rounded hover:bg-cyan-600">再読み込み</button></td></tr>';
      }

      // ダミーデータで代替
      const today = new Date();
      const dummyData = {};
      for (let i = 20; i < 40; i++) {
        const date = new Date(today);
        date.setDate(today.getDate() + i);
        const dateStr = formatDateISO(date);
        dummyData[dateStr] = {};
        KIGURUMI_LIST.forEach((kigurumi) => {
          dummyData[dateStr][kigurumi.dataKey] =
            Math.random() > 0.7 ? "✕" : "○";
        });
      }
      state.calendarData = dummyData;
      renderCalendar(state.currentYear, state.currentMonth);
      return;
    }

    // データを保存
    state.calendarData = data;
    console.log("カレンダーデータ保存完了");

    // カレンダーを描画
    renderCalendar(state.currentYear, state.currentMonth);

    // 日付入力フィールドの初期値がある場合はきぐるみ選択肢を更新
    const initialDate = DOM.dateInput()?.value;
    if (initialDate) {
      updateAvailableCharacters(initialDate);
    }
  };

  /**
   * カレンダーデータ取得失敗時の処理
   */
  const handleCalendarDataError = () => {
    const calendarBody = DOM.calendarBody();
    console.log("カレンダーデータ取得失敗 - ダミーデータで代替");

    if (calendarBody) {
      calendarBody.innerHTML =
        '<tr><td colspan="7" class="text-center py-8 text-orange-600">サーバーからデータを取得できません。<br>テスト用にダミーデータで表示します。<br><button onclick="location.reload()" class="mt-2 bg-cyan-500 text-white px-4 py-2 rounded hover:bg-cyan-600">再読み込み</button></td></tr>';
    }

    // ダミーデータを生成して表示
    setTimeout(() => {
      const today = new Date();
      const dummyData = {};

      // 20日後から40日後までのダミーデータを生成
      for (let i = 20; i < 60; i++) {
        const date = new Date(today);
        date.setDate(today.getDate() + i);
        const dateStr = formatDateISO(date);
        dummyData[dateStr] = {};

        KIGURUMI_LIST.forEach((kigurumi) => {
          // ランダムに予約済み/予約可能を設定
          dummyData[dateStr][kigurumi.dataKey] =
            Math.random() > 0.7 ? "✕" : "○";
        });
      }

      state.calendarData = dummyData;
      renderCalendar(state.currentYear, state.currentMonth);
      console.log("ダミーデータでカレンダー表示完了");
    }, 1000);
  };

  // =====================================
  // 認証関連
  // =====================================

  /**
   * Firebaseを初期化する
   */
  const initializeFirebase = () => {
    try {
      // Firebaseの初期化（重複防止）
      if (!firebase.apps.length) {
        firebase.initializeApp(FIREBASE_CONFIG);
      }

      // 認証状態の監視
      firebase.auth().onAuthStateChanged((user) => {
        // 認証処理中の場合は何もしない
        if (state.authProcessing) {
          console.log("認証処理中のため監視をスキップ");
          return;
        }

        if (user) {
          // セッション時間制限チェック
          const loginTime = parseInt(localStorage.getItem("loginTime"), 10);
          const now = Date.now();

          if (loginTime && now - loginTime > MAX_SESSION_DURATION) {
            console.log("セッション期限切れ");
            state.authProcessing = true;
            firebase.auth().signOut().then(() => {
              localStorage.removeItem("loginTime");
              state.authProcessing = false;
              showLoginScreen();
            }).catch((error) => {
              console.error("ログアウトエラー:", error);
              state.authProcessing = false;
              showLoginScreen();
            });
          } else {
            console.log("ユーザーログイン済み");
            state.isLoggedIn = true;
            removeLoginScreen();
            showContent();
          }
        } else {
          console.log("ユーザー未ログイン");
          state.isLoggedIn = false;
          showLoginScreen();
        }
      });
    } catch (error) {
      console.error("Firebase初期化エラー:", error);
      showLoginScreen();
    }
  };

  /**
   * ログイン画面を削除する
   */
  const removeLoginScreen = () => {
    const loginScreen = document.getElementById("login-screen");
    if (loginScreen) {
      loginScreen.remove();
    }
  };

  /**
   * ログイン画面を表示する
   */
  const showLoginScreen = () => {
    // 既にログイン画面がある場合は何もしない
    if (document.getElementById("login-screen")) return;

    // メインコンテンツを非表示にする
    hideMainContent();

    // ログイン画面のHTML
    const loginDiv = document.createElement("div");
    loginDiv.id = "login-screen";
    loginDiv.className = "flex justify-center items-start pt-16 w-full";
    loginDiv.innerHTML = `
      <div class="bg-white rounded-lg shadow-[0_0_5px_0_rgba(0,0,0,0.05)] mx-4 p-8 w-full max-w-lg text-zinc-600">
        <h2 class="text-xl font-bold text-center text-cyan-500 mb-6">きぐるみ予約システム</h2>
        <form id="login-form" class="space-y-4">
          <div class="flex flex-col">
            <label for="password" class="block font-medium mb-1 w-full">パスワード</label>
            <input type="password" id="password" class="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-cyan-500" placeholder="パスワードを入力">
          </div>
          <button type="submit" class="w-full bg-cyan-500 hover:bg-cyan-600 text-white font-bold py-2 px-4 rounded transition">
            ログイン
          </button>
          <p id="error-message" class="text-red-500 text-center hidden"></p>
        </form>
      </div>
    `;
    document.body.insertBefore(loginDiv, document.body.firstChild);

    // DOM挿入の完了を確実に待つ
    requestAnimationFrame(() => {
      setTimeout(() => {
        // ログインフォームのイベントリスナー
        const loginForm = document.getElementById("login-form");
        if (loginForm) {
          console.log("🔧 ログインフォームイベント設定開始");
          loginForm.addEventListener("submit", (e) => {
            console.log("📝 ログインフォーム送信イベント発火");
            e.preventDefault();
            const password = document.getElementById("password").value;
            console.log("🔑 パスワード取得:", password ? "あり" : "なし");

            // 認証処理中フラグを設定
            state.authProcessing = true;

            // 設定ファイルからメールアドレスを取得してログイン
            const authEmail = window.AppConfig?.authEmail || "kanaya.h.heim@gmail.com";
            firebase
              .auth()
              .setPersistence(firebase.auth.Auth.Persistence.LOCAL)
              .then(() => {
                console.log("🔧 Persistence設定完了（LOCAL）");
                return firebase
                  .auth()
                  .signInWithEmailAndPassword(
                    authEmail,
                    password
                  );
              })
              .then(() => {
                console.log("✅ ログイン成功");
                localStorage.setItem("loginTime", Date.now());
                // フラグをリセットしてからsetTimeoutで確実にonAuthStateChangedを発火させる
                setTimeout(() => {
                  state.authProcessing = false;
                  console.log("🔄 認証処理フラグをリセット");
                  
                  // 認証状態を確認して画面切り替えを強制実行
                  const currentUser = firebase.auth().currentUser;
                  if (currentUser) {
                    console.log("🚀 ログイン後の画面切り替えを強制実行");
                    state.isLoggedIn = true;
                    removeLoginScreen();
                    showContent();
                  }
                }, 100);
              })
              .catch((error) => {
                console.error("❌ ログインエラー:", error.code, error.message);
                state.authProcessing = false;
                const errorMessage = document.getElementById("error-message");
                if (errorMessage) {
                  if (error.code === "auth/invalid-credential" || error.code === "auth/wrong-password") {
                    errorMessage.textContent = "パスワードが正しくありません";
                  } else if (error.code === "auth/too-many-requests") {
                    errorMessage.textContent = "ログイン試行回数が多すぎます。しばらく待ってから再試行してください";
                  } else {
                    errorMessage.textContent = "ログインに失敗しました";
                  }
                  errorMessage.classList.remove("hidden");
                }
              });
          });

          console.log("✅ ログインフォームイベント設定完了");
        } else {
          console.error("❌ ログインフォームが見つかりません");
        }
      }, 50);
    });
  };

  /**
   * メインコンテンツを表示する
   */
  const showContent = () => {
    const mainContent = DOM.mainContent();
    if (mainContent) {
      mainContent.style.display = "block";
    }

    // 初期化処理を実行（未初期化の場合のみ）
    if (!state.isInitialized) {
      state.isInitialized = true;
      initializeApp();

      // ログイン完了後に確実にデータ取得
      setTimeout(() => {
        fetchAdvanceDays();
        fetchCalendarData(); // ← ここで呼ぶのが安全
      }, 3000);
    }
  };

  /**
   * メインコンテンツを非表示にする
   */
  const hideMainContent = () => {
    const mainContent = DOM.mainContent();
    if (mainContent) {
      mainContent.style.display = "none";
    }
  };

  // =====================================
  // アプリケーション初期化
  // =====================================

  /**
   * アプリケーションの初期化処理
   */
  const initializeApp = () => {
    console.log("アプリケーション初期化開始");

    // CSRFトークンを初期化
    initializeCSRFToken();

    // 現在の日付から表示月を設定
    initializeCurrentMonth();

    // きぐるみ選択肢を初期化
    initializeKigurumiSelect();

    // 各種イベントリスナーを設定
    setupEventListeners();

    // 初期化時は予約日数テキストを取得中表示にしておく
    const advanceDaysText = DOM.advanceDaysText();
    if (advanceDaysText) {
      advanceDaysText.textContent = "※予約日数を取得中...";
    }

    // データ取得処理を実行（少し遅延させてDOMの準備を確実にする）
    // setTimeout(() => {
    //   fetchAdvanceDays();
    //   fetchCalendarData();
    // }, 100);
  };

  /**
   * 現在月を初期化
   */
  const initializeCurrentMonth = () => {
    // API取得前は現在月を表示（予約日数取得後に適切な月に移動）
    const currentDate = new Date();
    state.currentYear = currentDate.getFullYear();
    state.currentMonth = currentDate.getMonth();
  };

  // =====================================
  // UI更新処理
  // =====================================

  /**
   * 最小日付を更新する
   */
  const updateMinDate = () => {
    const dateInput = DOM.dateInput();
    if (dateInput) {
      // 最小日付設定
      const minDate = new Date();
      minDate.setDate(minDate.getDate() + state.advanceDays);
      dateInput.min = formatDateISO(minDate);

      // 最大日付を設定
      const maxDate = new Date();
      maxDate.setDate(maxDate.getDate() + 365); // 1年後
      dateInput.max = formatDateISO(maxDate);
    }
  };

  /**
   * 予約日数の表示文言を更新する
   */
  const updateAdvanceDaysText = () => {
    const advanceDaysText = DOM.advanceDaysText();
    if (advanceDaysText) {
      advanceDaysText.textContent = `※${state.advanceDays}日前からの予約が可能です`;
    }
  };

  /**
   * きぐるみ選択肢を初期化する
   */
  const initializeKigurumiSelect = () => {
    const characterSelect = DOM.characterSelect();
    if (!characterSelect) return;

    // 既にオプションがある場合は一度クリア
    characterSelect.innerHTML = "";

    // 「すべて表示」オプションを追加
    characterSelect.appendChild(createOption("all", "すべて表示"));

    // 他のきぐるみオプションを追加
    KIGURUMI_LIST.forEach((kigurumi) => {
      characterSelect.appendChild(createOption(kigurumi.id, kigurumi.display));
    });

    // 初期値を設定
    characterSelect.value = "all";
  };

  /**
   * 予約可能なきぐるみを更新する
   * @param {string} dateStr - 選択された日付
   */
  const updateAvailableCharacters = (dateStr) => {
    const characterSelect = DOM.characterField();
    if (!characterSelect) return;

    // セレクトボックスをクリア
    characterSelect.innerHTML = '<option value="">選択してください</option>';

    // 日付が選択されていない場合は何もしない
    if (!dateStr) return;

    // コンシェルジュのみが選択されている場合
    if (state.selectedCharacter === "コンシェルジュのみ（きぐるみ不要）") {
      // 「コンシェルジュのみ」も含めて全てのきぐるみを選択肢に追加する
      KIGURUMI_LIST.forEach((kigurumi) => {
        characterSelect.appendChild(
          createOption(kigurumi.id, kigurumi.display)
        );
      });
      return;
    }

    // カレンダーデータがある場合は予約状況をチェック
    if (state.calendarData[dateStr]) {
      // 各きぐるみについて予約状況をチェック
      KIGURUMI_LIST.forEach((kigurumi) => {
        // データが存在しない場合は予約可能として扱う
        const status = state.calendarData[dateStr][kigurumi.dataKey];

        if (status !== "✕") {
          const exists = Array.from(characterSelect.options).some(
            (option) => option.value === kigurumi.id
          );
          if (!exists) {
            characterSelect.appendChild(
              createOption(kigurumi.id, kigurumi.display)
            );
          }
        }
      });
    } else {
      // カレンダーデータに日付がない場合は全て表示
      KIGURUMI_LIST.forEach((kigurumi) => {
        const exists = Array.from(characterSelect.options).some(
          (option) => option.value === kigurumi.id
        );
        if (!exists) {
          characterSelect.appendChild(
            createOption(kigurumi.id, kigurumi.display)
          );
        }
      });
    }
  };

  /**
   * カレンダーを描画する
   * @param {number} year - 年
   * @param {number} month - 月（0-11）
   */
  const renderCalendar = (year, month) => {
    // 月名を更新
    const monthNames = [
      "1月",
      "2月",
      "3月",
      "4月",
      "5月",
      "6月",
      "7月",
      "8月",
      "9月",
      "10月",
      "11月",
      "12月",
    ];
    const currentMonthElement = DOM.currentMonth();
    if (currentMonthElement) {
      currentMonthElement.textContent = `${year}年${monthNames[month]}`;
    }

    // カレンダーを生成
    const calendarBody = DOM.calendarBody();
    if (!calendarBody) return;

    calendarBody.innerHTML = "";

    // 月の初日と最終日
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    // 初日の曜日（0:日曜日 - 6:土曜日）
    const startDay = firstDay.getDay();

    // 月の日数
    const daysInMonth = lastDay.getDate();

    // 現在の日付
    const today = new Date();
    today.setHours(0, 0, 0, 0); // 時刻部分をリセット

    // 予約可能な最小日付（advanceDays日後）
    const minDate = new Date(today);
    minDate.setDate(today.getDate() + state.advanceDays);
    minDate.setHours(0, 0, 0, 0);

    // カレンダーの行数を計算（最大6週）
    const totalRows = Math.ceil((startDay + daysInMonth) / 7);

    // 日付カウンター
    let date = 1;

    // 週ごとの行を生成
    for (let i = 0; i < totalRows; i++) {
      const row = document.createElement("tr");

      // 各曜日のセルを生成
      for (let j = 0; j < 7; j++) {
        const cell = document.createElement("td");
        cell.className =
          "border-l border-t p-1 day-cell relative h-16 sm:h-20 md:h-20";

        // 曜日クラスを追加
        if (j === 0) cell.classList.add("text-red-700");
        if (j === 6) cell.classList.add("text-cyan-700");

        // 第1週で前月の日付
        if (i === 0 && j < startDay) {
          renderEmptyCell(cell);
        }
        // 当月の日数を超えた場合は翌月の日付
        else if (date > daysInMonth) {
          renderEmptyCell(cell);
        }
        // 当月の日付
        else {
          renderDateCell(cell, date, year, month, today, minDate);
          date++;
        }

        row.appendChild(cell);
      }

      calendarBody.appendChild(row);

      // 月の日付をすべて表示したら終了
      if (date > daysInMonth && i >= 3) {
        break;
      }
    }
  };

  /**
   * 空のセルを描画
   * @param {HTMLElement} cell - セル要素
   */
  const renderEmptyCell = (cell) => {
    cell.classList.add("bg-zinc-50");
    // 空のdivを追加して高さを維持
    const emptyDiv = document.createElement("div");
    emptyDiv.className = "mb-1";
    cell.appendChild(emptyDiv);
  };

  /**
   * 日付セルを描画
   * @param {HTMLElement} cell - セル要素
   * @param {number} date - 日
   * @param {number} year - 年
   * @param {number} month - 月
   * @param {Date} today - 今日の日付
   * @param {Date} minDate - 予約可能最小日
   */
  const renderDateCell = (cell, date, year, month, today, minDate) => {
    // 日付表示用div
    const dayNumber = document.createElement("div");
    dayNumber.className =
      "text-center mb-1 day-number text-xs sm:text-sm md:text-base";
    dayNumber.textContent = date;

    // 日付オブジェクト作成
    const cellDate = new Date(year, month, date);
    cellDate.setHours(0, 0, 0, 0);

    // 今日の日付にクラスを追加
    if (cellDate.getTime() === today.getTime()) {
      cell.classList.add("bg-amber-50");
      dayNumber.classList.add("font-bold");
    }

    // 状態表示用のマーカー
    const statusMarker = document.createElement("div");
    statusMarker.className =
      "status-marker mx-auto w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6 leading-4 sm:leading-5 md:leading-6 text-xs sm:text-sm md:text-base";

    // 過去日付または予約期間外の日付
    if (cellDate < minDate) {
      renderUnavailableCell(cell, statusMarker);
    } else {
      // 最大予約日（1年後）をチェック
      const maxDate = new Date(today);
      maxDate.setDate(today.getDate() + 365); // 1年後
      maxDate.setHours(0, 0, 0, 0);
      if (cellDate > maxDate) {
        renderUnavailableCell(cell, statusMarker);
      } else {
        // 日付を文字列に変換（YYYY-MM-DD形式）
        const dateStr = formatDateISO(cellDate);

        // コンシェルジュのみが選択されている場合は常に予約可能とする
        if (state.selectedCharacter === "コンシェルジュのみ（きぐるみ不要）") {
          const isAvailable = checkAvailability(dateStr);
          if (isAvailable) {
            renderAvailableCell(cell, statusMarker, cellDate);
          } else {
            renderBookedCell(statusMarker);
          }
        } else {
          // 予約状況をチェック
          const isAvailable = checkAvailability(dateStr);

          if (isAvailable) {
            renderAvailableCell(cell, statusMarker, cellDate);
          } else {
            renderBookedCell(statusMarker);
          }
        }
      }
    }

    cell.appendChild(dayNumber);
    cell.appendChild(statusMarker);
  };

  /**
   * 予約不可セルを描画
   * @param {HTMLElement} cell - セル要素
   * @param {HTMLElement} statusMarker - 状態表示マーカー
   */
  const renderUnavailableCell = (cell, statusMarker) => {
    cell.classList.add("cursor-not-allowed", "bg-zinc-50", "text-zinc-300");
    statusMarker.classList.add("text-zinc-300");
    statusMarker.textContent = "-";
  };

  /**
   * 予約可能セルを描画
   * @param {HTMLElement} cell - セル要素
   * @param {HTMLElement} statusMarker - 状態表示マーカー
   * @param {Date} cellDate - セルの日付
   */
  const renderAvailableCell = (cell, statusMarker, cellDate) => {
    statusMarker.classList.add("text-cyan-600", "font-bold");
    statusMarker.textContent = "◯";
    cell.classList.add("cursor-pointer", "hover:bg-cyan-50");

    // 日付クリック時のイベント
    cell.addEventListener("click", () => {
      handleDateClick(cellDate);
    });
  };

  /**
   * 予約済みセルを描画
   * @param {HTMLElement} statusMarker - 状態表示マーカー
   */
  const renderBookedCell = (statusMarker) => {
    statusMarker.classList.add("text-red-600", "font-bold");
    statusMarker.textContent = "✕";
  };

  /**
   * 日付クリック時の処理
   * @param {Date} cellDate - クリックされた日付
   */
  const handleDateClick = (cellDate) => {
    const dateInput = DOM.dateInput();
    if (!dateInput) return;

    const dateValue = formatDateISO(cellDate);
    dateInput.value = dateValue;

    // 予約可能なきぐるみを更新
    updateAvailableCharacters(dateValue);

    // 特定のきぐるみが選択されている場合はフォームに設定
    if (state.selectedCharacter !== "all") {
      // コンシェルジュのみが選択されている場合
      if (state.selectedCharacter === "コンシェルジュのみ（きぐるみ不要）") {
        // コンシェルジュのみ予約の場合、ラジオボタンの「必要」を自動選択
        const conciergeRadios = DOM.conciergeRadios();
        for (const radio of conciergeRadios) {
          if (radio.value === "必要") {
            radio.checked = true;
            break;
          }
        }
        // コンシェルジュのみを自動選択
        const characterSelect = DOM.characterField();
        if (characterSelect) {
          characterSelect.value = "コンシェルジュのみ（きぐるみ不要）";
        }
        // コンシェルジュ欄の非表示処理
        toggleConciergeSection("コンシェルジュのみ（きぐるみ不要）");
      } else {
        const characterSelect = DOM.characterField();
        if (characterSelect) {
          // 選択されたきぐるみが予約可能かチェック
          for (let i = 0; i < characterSelect.options.length; i++) {
            if (characterSelect.options[i].value === state.selectedCharacter) {
              characterSelect.value = state.selectedCharacter;
              break;
            }
          }
        }
        toggleConciergeSection(state.selectedCharacter);
      }
    }

    // 予約フォームにスクロール
    const formElement = document.querySelector("form");
    if (formElement) {
      formElement.scrollIntoView({ behavior: "smooth" });
    }
  };

  /**
   * 予約可能かチェック
   * @param {string} dateStr - 日付文字列
   * @returns {boolean} 予約可能ならtrue
   */
  const checkAvailability = (dateStr) => {
    if (state.selectedCharacter === "all") {
      // すべてのきぐるみをチェック
      if (state.calendarData[dateStr]) {
        const allBooked = KIGURUMI_LIST.every(
          (kigurumi) => state.calendarData[dateStr][kigurumi.dataKey] === "✕"
        );
        return !allBooked;
      }
      return true;
    } else if (
      state.selectedCharacter === "コンシェルジュのみ（きぐるみ不要）"
    ) {
      // コンシェルジュのみは手動で✕にされていない限り予約可能
      if (
        state.calendarData[dateStr] &&
        state.calendarData[dateStr]["コンシェルジュのみ（きぐるみ不要）"] ===
          "✕"
      ) {
        return false;
      }
      return true;
    } else {
      // 特定のきぐるみをチェック
      const selectedKigurumi = KIGURUMI_LIST.find(
        (k) => k.id === state.selectedCharacter
      );
      if (selectedKigurumi && state.calendarData[dateStr]) {
        return state.calendarData[dateStr][selectedKigurumi.dataKey] !== "✕";
      }
      return true;
    }
  };

  /**
   * コンシェルジュ欄の表示/非表示を切り替える
   * @param {string} characterValue - 選択されたきぐるみ名
   */
  const toggleConciergeSection = (characterValue) => {
    const conciergeSection = DOM.conciergeSection();
    const conciergeRadios = DOM.conciergeRadios();
    if (!conciergeSection || conciergeRadios.length === 0) return;

    if (characterValue === "コンシェルジュのみ（きぐるみ不要）") {
      conciergeSection.style.display = "none";
      conciergeRadios.forEach((radio) => {
        radio.checked = radio.value === "必要";
      });
    } else {
      conciergeSection.style.display = "";
    }
  };

  // =====================================
  // イベントリスナー
  // =====================================

  /**
   * 各種イベントリスナーを設定
   */
  const setupEventListeners = () => {
    // 前月ボタンのイベント
    const prevMonthBtn = DOM.prevMonthBtn();
    if (prevMonthBtn) {
      prevMonthBtn.addEventListener("click", () => {
        state.currentMonth--;
        if (state.currentMonth < 0) {
          state.currentMonth = 11;
          state.currentYear--;
        }
        renderCalendar(state.currentYear, state.currentMonth);
      });
    }

    // 翌月ボタンのイベント
    const nextMonthBtn = DOM.nextMonthBtn();
    if (nextMonthBtn) {
      nextMonthBtn.addEventListener("click", () => {
        state.currentMonth++;
        if (state.currentMonth > 11) {
          state.currentMonth = 0;
          state.currentYear++;
        }
        renderCalendar(state.currentYear, state.currentMonth);
      });
    }

    // きぐるみ選択変更イベント
    const characterSelect = DOM.characterSelect();
    if (characterSelect) {
      characterSelect.addEventListener("change", function () {
        state.selectedCharacter = this.value;
        renderCalendar(state.currentYear, state.currentMonth);
      });
    }

    // 日付が変更されたときのイベント
    const dateInput = DOM.dateInput();
    if (dateInput) {
      dateInput.addEventListener("change", function () {
        updateAvailableCharacters(this.value);
      });
    }

    // 電話番号入力フィールドに自動フォーマットを適用
    const phoneInput = DOM.phoneInput();
    if (phoneInput) {
      phoneInput.addEventListener("input", function (e) {
        // カーソル位置を保存
        const start = this.selectionStart;
        const end = this.selectionEnd;

        // 現在の値から数字だけを抽出
        let value = this.value.replace(/\D/g, "");

        // 桁数に応じてフォーマット
        if (value.length > 3 && value.length <= 7) {
          this.value = value.slice(0, 3) + "-" + value.slice(3);
        } else if (value.length > 7) {
          this.value =
            value.slice(0, 3) + "-" + value.slice(3, 7) + "-" + value.slice(7);
        } else {
          this.value = value;
        }

        // 文字数制限（ハイフン込みで13文字まで）
        if (this.value.length > 13) {
          this.value = this.value.substring(0, 13);
        }

        // カーソル位置を適切に調整
        if (
          this.value.charAt(start - 1) === "-" &&
          this.value.charAt(start) !== "-"
        ) {
          this.setSelectionRange(start + 1, end + 1);
        } else {
          this.setSelectionRange(start, end);
        }
      });
    }

    // フォーム送信処理
    const reservationForm = DOM.reservationForm();
    if (reservationForm) {
      reservationForm.addEventListener("submit", (e) => {
        e.preventDefault();
        submitReservation();
      });
    }

    // フォーム内きぐるみプルダウン変更時、コンシェルジュ有無を非表示 or 表示
    const characterField = DOM.characterField();
    if (characterField) {
      characterField.addEventListener("change", function () {
        toggleConciergeSection(this.value);
      });
    }

    // 備考欄の文字数カウンター
    const remarksField = document.getElementById("remarks");
    const remarksCount = document.getElementById("remarks-count");
    if (remarksField && remarksCount) {
      const updateCount = () => {
        const length = remarksField.value.length;
        remarksCount.textContent = length;
        
        // 文字数が上限に近づいたら色を変更
        if (length >= 140) {
          remarksCount.style.color = "#ef4444"; // 赤色
        } else if (length >= 120) {
          remarksCount.style.color = "#f59e0b"; // 黄色
        } else {
          remarksCount.style.color = "#6b7280"; // グレー
        }
      };
      
      remarksField.addEventListener("input", updateCount);
      updateCount(); // 初期表示
    }
  };

  // =====================================
  // 予約フォーム処理
  // =====================================

  /**
   * フォームデータを取得
   * @returns {Object} フォームデータ
   */
  const getFormData = () => {
    // ラジオボタンの値を取得
    const conciergeRadios = DOM.conciergeRadios();
    let conciergeValue = "不要"; // デフォルト値

    for (const radio of conciergeRadios) {
      if (radio.checked) {
        conciergeValue = radio.value;
        break;
      }
    }

    return {
      date: DOM.dateInput()?.value || "",
      character: DOM.characterField()?.value || "",
      office: document.getElementById("office")?.value || "",
      location: document.getElementById("location")?.value || "",
      concierge: conciergeValue,
      name: document.getElementById("name")?.value || "",
      email: document.getElementById("email")?.value || "",
      phone: DOM.phoneInput()?.value || "",
      remarks: document.getElementById("remarks")?.value || "",
    };
  };

  /**
   * 予約フォームを送信
   */
  let isSubmitting = false; // 二重送信防止フラグ
  const submitReservation = () => {
    if (isSubmitting) return; // 二重送信を防止
    isSubmitting = true;

    const formData = getFormData();

    // 送信ボタンを無効化
    const submitBtn = DOM.submitBtn();
    if (!submitBtn) {
      isSubmitting = false;
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "送信中...";

    // POSTリクエストのフォームデータ（CSRFトークン付き）
    const requestData = {
      action: "processReservation",
      formData: formData,
      csrfToken: getCSRFToken(),
    };

    // JSONP形式でリクエスト
    safeInvokeJsonpApi({
      action: "processReservation",
      data: requestData,
      callback: (response) => {
        onSuccess(response);
        isSubmitting = false;
      },
      errorCallback: () => {
        onFailure(new Error("サーバーとの通信に失敗しました"));
        isSubmitting = false;
      },
    });
  };

  /**
   * フォーム送信成功時の処理
   * @param {Object} result - 処理結果
   */
  const onSuccess = (result) => {
    const messageDiv = DOM.messageDiv();
    const submitBtn = DOM.submitBtn();
    const reservationForm = DOM.reservationForm();
    const mainContainer = DOM.mainContent();

    // ボタンを元に戻す
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "予約する";
    }

    if (result.success) {
      // コンテナ内の全要素を非表示にする
      if (mainContainer) {
        Array.from(mainContainer.children).forEach((child) => {
          child.style.display = "none";
        });

        // 完了画面を表示
        showCompletionScreen(mainContainer, reservationForm, messageDiv);

        // カレンダーデータを更新しておく
        fetchCalendarData();
      }
    } else {
      showErrorMessage(messageDiv, result.message || "予約できませんでした。");
    }
  };

  /**
   * フォーム送信失敗時の処理
   * @param {Error} error - エラーオブジェクト
   */
  const onFailure = (error) => {
    const messageDiv = DOM.messageDiv();
    const submitBtn = DOM.submitBtn();

    // ボタンを元に戻す
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "予約する";
    }

    showErrorMessage(
      messageDiv,
      "エラーが発生しました: " + (error.message || "不明なエラー")
    );
  };

  /**
   * 完了画面を表示
   * @param {HTMLElement} mainContainer - コンテナ要素
   * @param {HTMLElement} reservationForm - フォーム要素
   * @param {HTMLElement} messageDiv - メッセージ要素
   */
  const showCompletionScreen = (mainContainer, reservationForm, messageDiv) => {
    const completionContainer = document.createElement("div");
    completionContainer.id = "completion-screen";
    completionContainer.className =
      "bg-white rounded-lg shadow-[0_0_5px_0_rgba(0,0,0,0.05)] text-center pt-2 pb-4 px-4 md:pt-6 md:pb-8 md:px-6";

    completionContainer.innerHTML = `
      <div class="mb-3 sm:mb-4 text-center">
        <svg class="w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16 text-green-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
        </svg>
      </div>
      <h2 class="text-xl sm:text-xl md:text-2xl font-bold text-center text-cyan-500 mb-2 sm:mb-3 md:mb-4">予約が完了しました！</h2>
      <p class="text-xs sm:text-sm md:text-base text-zinc-600 mb-4 sm:mb-5 md:mb-6">予約内容の確認メールをお送りしましたのでご確認ください。</p>
      <button id="new-reservation-btn" class="bg-cyan-500 hover:bg-cyan-600 text-white font-bold py-2 sm:py-2 md:py-3 px-3 sm:px-4 md:px-6 text-xs sm:text-sm md:text-base rounded transition mb-3 sm:mb-4">
        新しい予約をする
      </button>
      <div class="text-center">
        <a href="reservations.html" class="text-cyan-600 hover:text-cyan-700 hover:underline text-xs sm:text-sm md:text-base transition">
          予約状況を確認する
        </a>
      </div>
    `;

    // mainContainerに完了画面を追加
    mainContainer.appendChild(completionContainer);

    // 「新しい予約をする」ボタンのイベントリスナーを追加
    requestAnimationFrame(() => {
      const newReservationBtn = document.getElementById("new-reservation-btn");
      if (newReservationBtn) {
        newReservationBtn.addEventListener("click", () => {
          handleNewReservation(mainContainer, reservationForm, messageDiv);
        });
      }
    });
  };

  /**
   * 新しい予約処理を行う
   * @param {HTMLElement} mainContainer - コンテナ要素
   * @param {HTMLElement} reservationForm - フォーム要素
   * @param {HTMLElement} messageDiv - メッセージ要素
   */
  const handleNewReservation = (mainContainer, reservationForm, messageDiv) => {
    // 完了画面を削除
    const completionScreen = document.getElementById("completion-screen");
    if (completionScreen) {
      completionScreen.remove();
    }

    // すべての要素を再表示
    if (mainContainer) {
      Array.from(mainContainer.children).forEach((child) => {
        child.style.display = "";
      });
    }

    // フォームをリセット
    if (reservationForm) {
      reservationForm.reset();
    }

    if (messageDiv) {
      messageDiv.style.display = "none";
    }

    // カレンダーデータを更新して再描画
    fetchCalendarData();

    // イベントリスナーを再設定
    setupEventListeners();

    // トップにスクロール
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // =====================================
  // 初期化処理
  // =====================================

  /**
   * アプリケーションの初期化
   */
  const initialize = () => {
    console.log("システム初期化開始");

    // ページコンテンツを非表示にする
    hideMainContent();

    // Firebaseの初期化
    initializeFirebase();
  };

  // 公開メソッド
  return {
    initialize,
  };
})();

// DOMContentLoadedイベントでアプリケーションを初期化
document.addEventListener(
  "DOMContentLoaded",
  KigurumiReservationSystem.initialize
);
