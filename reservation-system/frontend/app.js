// URL
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
  container.innerHTML = 'Loading...';

  // allReservationsが未取得なら取得
  if (allReservations.length === 0) {
    allReservations = await fetchReservations();
  }

  // 検索テキストとソートオプションを取得
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
    container.innerHTML = '<p>No Reservations Found</p>';
    return;
  }

  container.innerHTML = '';
  filtered.forEach(item => {
    const div = document.createElement('div');
    div.className = 'reservation-item';
    div.innerHTML = `
      <strong>ID:</strong> ${item.reservationId}<br>
      <strong>Resource:</strong> ${item.resourceName}<br>
      <strong>Time:</strong> ${item.time}<br>
      <button onclick="deleteReservation('${item.reservationId}')">Delete</button>
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
    alert('Reservation created!');
    document.getElementById('resourceName').value = '';
    document.getElementById('time').value = '';
    // 新規作成後はallReservationsをクリアして再取得
    allReservations = [];
    await renderReservations();
  } else {
    alert('Failed to create reservation');
  }
});

// 検索・ソートイベントハンドラ
document.getElementById('search').addEventListener('input', renderReservations);
document.getElementById('sort').addEventListener('change', renderReservations);

// 初期表示
renderReservations();
