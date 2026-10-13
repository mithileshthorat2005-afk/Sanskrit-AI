const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL?.trim() || 'http://127.0.0.1:8005'
).replace(/\/+$/, '');

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  let response: Response;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Add Authorization header if token exists
  if (authToken) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${authToken}`;
  }

  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (error) {
    const reason = error instanceof Error ? ` (${error.message})` : '';
    throw new Error(
      `Cannot reach the SanskritAI backend at ${API_BASE_URL}${reason}. ` +
        'Start it from the backend folder with "python main.py", or set ' +
        'NEXT_PUBLIC_API_URL to the backend URL and restart the frontend.'
    );
  }

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired or invalid - clear auth
      authToken = null;
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      if (typeof window !== 'undefined') {
        window.location.href = "/";
      }
    }
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    throw new Error(error.detail || 'API request failed');
  }

  return response.json();
}

export const api = {
  auth: {
    login: (credentials: any) => apiRequest('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
    signup: (data: any) => apiRequest('/auth/signup', { method: 'POST', body: JSON.stringify(data) }),
    logout: () => apiRequest('/auth/logout', { method: 'POST' }),
    me: () => apiRequest('/auth/me'),
  },
  lesson: {
    attempt: (data: { lesson_id: number; correct: boolean }) =>
      apiRequest('/lesson/attempt', {
        method: 'POST',
        body: JSON.stringify({
          lesson_id: data.lesson_id,
          correct: data.correct,
        }),
      }),
  },
  lessons: {
    attempt: (data: { lesson_id: number; correct: boolean }) =>
      apiRequest('/lesson/attempt', {
        method: 'POST',
        body: JSON.stringify({
          lesson_id: data.lesson_id,
          correct: data.correct,
        }),
      }),
    getAll: (level?: string) => apiRequest(`/lessons${level ? `?level=${level}` : ''}`),
    getById: (id: string | number) => apiRequest(`/lessons/${id}`),
    getGreetings: () => apiRequest('/api/lessons/greetings'),
    getNumbers: () => apiRequest('/api/lessons/numbers'),
    getSelfIntro: () => apiRequest('/api/lessons/self-intro'),
    getPronouns: () => apiRequest('/api/lessons/pronouns'),
    getVerbs: () => apiRequest('/api/lessons/verbs'),
    getNouns: () => apiRequest('/api/lessons/nouns'),
    getFamily: () => apiRequest('/api/lessons/family'),
    getQuestionWords: () => apiRequest('/api/lessons/questions'),
    getTimeAndDays: () => apiRequest('/api/lessons/time'),
    getDailyQuestions: () => apiRequest('/api/daily-questions'),
    getVibhakti: () => apiRequest('/api/lessons/vibhakti'),
    getSandhi: () => apiRequest('/api/lessons/sandhi'),
    getTenses: () => apiRequest('/api/lessons/tenses'),
    getMoods: () => apiRequest('/api/lessons/moods'),
    getPronounsExtended: () => apiRequest('/api/lessons/pronouns-extended'),
    getUpasarga: () => apiRequest('/api/lessons/upasarga'),
    getVoice: () => apiRequest('/api/lessons/voice'),
    getIndeclinables: () => apiRequest('/api/lessons/indeclinables'),
    getParticiples: () => apiRequest('/api/lessons/participles'),
    getReadingComposition: () => apiRequest('/api/lessons/reading-composition'),
    getSamasa1: () => apiRequest('/api/lessons/samasa1'),
    getSamasa2: () => apiRequest('/api/lessons/samasa2'),
    getParticiples2: () => apiRequest('/api/lessons/participles2'),
    getStriPratyaya: () => apiRequest('/api/lessons/stri-pratyaya'),
    getChandas: () => apiRequest('/api/lessons/chandas'),
  },
  user: {
    getProgress: () => apiRequest('/progress'),
    getActivities: () => apiRequest('/activities'),
    getDashboardStats: () => apiRequest('/dashboard/stats'),
    getRecommendation: () => apiRequest('/recommendation'),
    getBKTSummary: () => apiRequest('/bkt/summary'),
    getBKTMastery: () => apiRequest('/bkt/mastery'),
    getPersistentDashboard: () => apiRequest('/dashboard'),
    getStreak: () => apiRequest('/streak'),
    getGrammarHistory: (limit = 20) => apiRequest(`/grammar/history?limit=${limit}`),
    recordDailyActivity: (score_percent = 100) =>
      apiRequest('/streak/activity', {
        method: 'POST',
        body: JSON.stringify({ score_percent }),
      }),
    completeLesson: (lesson_id: number | string) =>
      apiRequest('/progress/complete', {
        method: 'POST',
        body: JSON.stringify({ lesson_id }),
      }),
    submitQuiz: (data: { lesson_id: string; answers: Record<string, number>; quiz_id?: string }) =>
      apiRequest('/progress/quiz', { method: 'POST', body: JSON.stringify(data) }),
  },
  tools: {
    translate: (data: { text: string; direction: string; use_api?: boolean }) => 
      apiRequest('/translate', { method: 'POST', body: JSON.stringify(data) }),
    checkGrammar: (text: string, use_ai: boolean = false) =>
      apiRequest('/grammar/check', {
        method: 'POST',
        body: JSON.stringify({ text, use_ai }),
      }),
  },
  game: {
    start: () => apiRequest('/game/start'),
    turn: (data: { current_position: number; asked_word: string; user_answer: string }) =>
      apiRequest('/game/turn', { method: 'POST', body: JSON.stringify(data) }),
    oddQuestion: () => apiRequest('/game/odd/question'),
    oddAnswer: (data: { question_data: any; user_choice: number }) =>
      apiRequest('/game/odd/answer', { method: 'POST', body: JSON.stringify(data) }),
  }
};
