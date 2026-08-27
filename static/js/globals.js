// Cardinal Shalom - Globals JS (tipos, utils)

// Tipos esperados por el frontend
const UserRole = {
  SUPER_ADMIN: 'super_admin',
  ACADEMIC_ADMIN: 'academic_admin',
  ACTIVITY_ADMIN: 'activity_admin',
  TEACHER: 'teacher',
  STUDENT: 'student',
};

const SystemMode = {
  NORMAL: 'normal',
  VACATIONS: 'vacations',
};

const TaskContentType = {
  TEXT: 'text',
  FILE: 'file',
  IMAGE: 'image',
  LINK: 'link',
};

// Utilidades
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// Carga datos JSON desde un endpoint y los pasa a un callback
async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Accept': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

// Formatea fecha ISO a string legible en español
function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('es-DO', { day: '2-digit', month: 'short', year: 'numeric' });
}
function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('es-DO', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

// Construye query string para filtros de ranking
function rankingQuery(gradeId, subjectId) {
  const params = new URLSearchParams();
  if (gradeId) params.set('grade_id', gradeId);
  if (subjectId) params.set('subject_id', subjectId);
  return params.toString();
}

// Para uso futuro: pulsar ranking live (polling cada 15s cuando viste ranking.html)
let rankingInterval = null;
function startRankingPolling() {
  if (rankingInterval) clearInterval(rankingInterval);
  rankingInterval = setInterval(() => {
    // recargar ranking si la pagina es ranking
    // handled in ranking.html via dedicated script
    console.log('[Ranking] polling check — implement in page');
  }, 15000);
}
function stopRankingPolling() {
  if (rankingInterval) clearInterval(rankingInterval);
  rankingInterval = null;
}
