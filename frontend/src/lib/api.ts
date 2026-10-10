export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8005';

export type DashboardRecommendation = {
  status: string;
  lesson_id: string | null;
  title: string | null;
  description: string | null;
  module?: string | null;
  estimated_time?: number | null;
  level?: string | null;
};

export type DashboardActivity = {
  type: string;
  detail: string;
  score_percent: number | null;
  occurred_at: string;
};

export type DashboardResponse = {
  statistics: {
    lessons_completed: number;
    total_lessons: number;
    quiz_attempts: number;
    quiz_average_score: number;
    grammar_activity_count: number;
    current_streak: number;
    longest_streak: number;
    active_learning_days: number;
  };
  recommendation: DashboardRecommendation;
  recent_activity: DashboardActivity[];
  mastery?: {
    average: number;
    mastered_skills: number;
    skills: Record<string, { mastery: number; attempts: number; correct: number }>;
  };
};

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const accessToken = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    if (response.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.assign('/');
    }
    throw new Error(error.detail || 'API request failed');
  }

  return response.json();
}

export const api = {
  auth: {
    login: (credentials: { username: string; password: string }) => apiRequest('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
    signup: (data: { username: string; password: string; role: string }) => apiRequest('/auth/signup', { method: 'POST', body: JSON.stringify(data) }),
    logout: () => apiRequest('/auth/logout', { method: 'POST' }),
  },
  lesson: {
    attempt: (data: { lesson_id: number; correct: boolean; username: string }) =>
      apiRequest('/lesson/attempt', {
        method: 'POST',
        body: JSON.stringify({
          lesson_id: data.lesson_id,
          correct: data.correct,
          username: data.username,
        }),
      }),
  },
  lessons: {
    getAll: (level?: string) => apiRequest(`/api/lessons/all${level ? `?level=${level}` : ''}`),
    getById: (id: string | number) => apiRequest(`/api/lessons/${id}`),
    attempt: (data: { lesson_id: number; correct: boolean; username: string }) =>
      apiRequest('/lesson/attempt', {
        method: 'POST',
        body: JSON.stringify({
          lesson_id: data.lesson_id,
          correct: data.correct,
          username: data.username,
        }),
      }),
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
    getAllLessons: () => apiRequest('/api/lessons/all'),
    getLessonById: (id: string) => apiRequest(`/api/lessons/${id}`),
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
    getProgress: (username: string) => apiRequest(`/progress/${username}`),
    getActivities: (username: string) => apiRequest(`/activities/${username}`),
    getDashboardStats: (username: string) => apiRequest(`/dashboard/stats/${username}`),
    getStreak: (username: string) => apiRequest(`/streak/${username}`),
    getRecommendation: (username: string) => apiRequest(`/recommendation/${username}`),
    getDashboard: (username: string): Promise<DashboardResponse> => apiRequest(`/dashboard/${username}`),
    getBKTSummary: (username: string) => apiRequest(`/bkt/summary/${username}`),
    getBKTMastery: (username: string) => apiRequest(`/bkt/mastery/${username}`),
  },
  tools: {
    translate: (data: { text: string; direction: string; use_api?: boolean }) =>
      apiRequest('/translate', { method: 'POST', body: JSON.stringify(data) }),
    checkGrammar: (username: string, text: string, use_ai: boolean = false) =>
      apiRequest('/grammar/check', { method: 'POST', body: JSON.stringify({ username, text, use_ai }) }),
  },
  bkt: {
    getProgress: (username: string) => apiRequest(`/progress/${username}`),
    markLessonComplete: (username: string, lessonId: string | number) =>
      apiRequest(`/progress/${username}/complete`, {
        method: 'POST',
        body: JSON.stringify({ lesson_id: lessonId }),
      }),
    submitQuiz: (username: string, lessonId: string, answers: Record<string, number>) =>
      apiRequest(`/progress/${username}/quiz`, {
        method: 'POST',
        body: JSON.stringify({ lesson_id: lessonId, answers }),
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
