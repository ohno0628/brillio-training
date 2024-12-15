// URLは適宜変更してください
const API_BASE_URL = "https://e6pv868gzj.execute-api.ap-northeast-1.amazonaws.com/Prod";

let allReservations = []; // 全件を保持

// 予約一覧取得関数
async function fetchReservations() {
  const res = await fetch(`${API_BASE_URL}/reservations`);
  const data = await res.json();
  return data;
}

// フィルタ・ソートして描画
async function renderReservations() {
  const container = document.getElementById('reservations-container');
  container.innerHTML = '読み込み中...';

  // allReservationsが未取得なら取得
  if (allReservations.length === 0) {
    allReservations = await fetchReservations();
  }

  const searchText = document.getElementById('search').value.toLowerCase();
  const sortOption = document.getElementById('sort').value;

  // 検索フィルタ適用
  let filtered = allReservations.filter(item =>
    item.resourceName.toLowerCase().includes(searchText)
  );

  // ソート適用
  if (sortOption === 'resourceNameAsc') {
    filtered.sort((a,b) => a.resourceName.localeCompare(b.resourceName));
  } else if (sortOption === 'resourceNameDesc') {
    filtered.sort((a,b) => b.resourceName.localeCompare(a.resourceName));
  } else if (sortOption === 'timeAsc') {
    filtered.sort((a,b) => new Date(a.time) - new Date(b.time));
  } else if (sortOption === 'timeDesc') {
    filtered.sort((a,b) => new Date(b.time) - new Date(a.time));
  }

  if (filtered.length === 0) {
    container.innerHTML = '<p>予約が見つかりません</p>';
    return;
  }

  container.innerHTML = '';
  filtered.forEach(item => {
    const div = document.createElement('div');
    div.className = 'reservation-item';
    div.innerHTML = `
      <strong>ID:</strong> ${item.reservationId}<br>
      <strong>リソース名：</strong> ${item.resourceName}<br>
      <strong>日時：</strong> ${item.time}<br>
      <button onclick="deleteReservation('${item.reservationId}')">削除</button>
      <button onclick="startEditReservation('${item.reservationId}', '${item.resourceName}', '${item.time}')">更新</button>
    `;
    container.appendChild(div);
  });
}

// 予約削除
async function deleteReservation(id) {
  await fetch(`${API_BASE_URL}/reservations/${id}`, {
    method: 'DELETE'
  });
  // 削除後はallReservationsをクリアして再取得
  allReservations = [];
  await renderReservations();
}

// 編集開始（更新用）
function startEditReservation(id, currentResource, currentTime) {
  const newResource = prompt("新しいリソース名を入力してください：", currentResource);
  if (newResource === null) return;
  const newTime = prompt("新しい日時(YYYY-MM-DDTHH:MM)を入力してください：", currentTime);
  if (newTime === null) return;

  updateReservation(id, newResource, newTime);
}

// 予約更新
async function updateReservation(id, resourceName, time) {
  const res = await fetch(`${API_BASE_URL}/reservations/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resourceName, time })
  });

  if (res.ok) {
    alert('予約が更新されました！');
    allReservations = [];
    await renderReservations();
  } else {
    alert('予約の更新に失敗しました');
  }
}

// 予約作成フォームハンドリング
document.getElementById('create-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const resourceName = document.getElementById('resourceName').value;
  const time = document.getElementById('time').value;

  const res = await fetch(`${API_BASE_URL}/reservations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({resourceName, time})
  });

  if (res.ok) {
    alert('予約が作成されました！');
    document.getElementById('resourceName').value = '';
    document.getElementById('time').value = '';
    // 新規作成後はallReservationsをクリアして再取得
    allReservations = [];
    await renderReservations();
  } else {
    alert('予約の作成に失敗しました');
  }
});

// 検索・ソートイベントハンドラ
document.getElementById('search').addEventListener('input', renderReservations);
document.getElementById('sort').addEventListener('change', renderReservations);

// 初期表示
renderReservations();
