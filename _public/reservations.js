document.addEventListener("DOMContentLoaded", () => {
  const GAS_ENDPOINT =
    "https://script.google.com/macros/s/AKfycbyEHl9JPivz818Wq63xyxiHL2wq_eBODviMwE14SaJ4DzD_aFR_1dhl_2oG8l6bomfv/exec";
  const loadingIndicator = document.getElementById("loading");
  const errorIndicator = document.getElementById("error");
  const reservationsContainer = document.getElementById("reservations-container");
  const reservationsList = document.getElementById("reservations-list");

  const fetchReservations = () => {
    const callbackName = `jsonp_callback_${Date.now()}`;
    const script = document.createElement("script");
    script.src = `${GAS_ENDPOINT}?action=fetchReservationsData&callback=${callbackName}`;

    window[callbackName] = (response) => {
      console.log("Response from GAS:", response);
      loadingIndicator.style.display = "none";
      if (response && response.reservations) {
        displayData(response.reservations);
      } else {
        showError();
        console.error("Failed to fetch reservations", response);
      }
      document.body.removeChild(script);
      delete window[callbackName];
    };

    script.onerror = (event) => {
      loadingIndicator.style.display = "none";
      showError();
      console.error("Error loading reservation data.", event);
      document.body.removeChild(script);
      delete window[callbackName];
    };

    document.body.appendChild(script);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const dayOfWeek = ["日", "月", "火", "水", "木", "金", "土"][date.getDay()];
    return `${year}年${month}月${day}日(${dayOfWeek})`;
  };

  const displayData = (data) => {
    reservationsContainer.classList.remove("hidden");
    reservationsList.innerHTML = "";

    if (data.length === 0) {
      reservationsList.innerHTML =
        '<div class="text-center p-4">現在、予約されている情報はありません。</div>';
      return;
    }

    const headers = ['予約日', 'きぐるみ', '営業所', '利用場所', 'コンシェルジュ', 'ステータス'];
    const keys = ['date', 'character', 'office', 'place', 'concierge', 'status'];

    data.forEach((row) => {
      const item = document.createElement("div");
      item.className = "grid grid-cols-1 md:grid-cols-6 gap-x-4 gap-y-2 p-3 border-b last:border-b-0 hover:bg-zinc-50 items-center";

      keys.forEach((key, index) => {
        const cell = document.createElement("div");
        cell.className = "text-sm flex items-center md:block";
        
        const value = key === 'date' ? formatDate(row[key]) : row[key];
        
        let valueHtml;
        if (key === 'status') {
            let statusClass = 'inline-block py-1 px-3 rounded-full text-xs font-semibold';
            if (value === '予約完了') {
                statusClass += " bg-zinc-100 text-zinc-800";
            } else if (value === '調整中') {
                statusClass += ' bg-orange-100 text-zinc-800';
            } else {
                statusClass = 'text-zinc-700';
            }
            valueHtml = `<span class="${statusClass}">${escapeHtml(value)}</span>`;
        } else {
            valueHtml = `<div>${escapeHtml(value)}</div>`;
        }

        cell.innerHTML = `
          <div class="md:hidden font-semibold text-zinc-500 w-28 shrink-0">${headers[index]}</div>
          ${valueHtml}
        `;
        item.appendChild(cell);
      });
      reservationsList.appendChild(item);
    });
  };

  const showError = () => {
    errorIndicator.classList.remove("hidden");
  };

  const escapeHtml = (str) => {
    if (str === null || str === undefined) return "";
    return str
      .toString()
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  };

  fetchReservations();
});
