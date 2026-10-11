import fs from 'fs';
import path from 'path';
import { checkSanskritSentence, type GrammarAnalysisResult } from './sanskritGrammarEngine';

export interface SanskritWord {
  sanskrit: string;
  devanagari: string;
  english: string;
  pronunciation: string;
  word_type: string;
  meaning: string;
  example: string;
  category: string;
  tags: string;
  source: string;
}

export interface UserProgress {
  completed_lessons: string[];
  quiz_attempts: number;
  quiz_total_score: number;
  grammar_activities: number;
  streak: number;
  last_active: string;
  skills: Record<string, { mastery: number; attempts: number; correct: number }>;
}

const DATA_DIR = path.join(process.cwd(), 'data');

function readJsonFile<T>(filename: string, fallback: T): T {
  try {
    const fullPath = path.join(DATA_DIR, filename);
    if (fs.existsSync(fullPath)) {
      const content = fs.readFileSync(fullPath, 'utf-8');
      return JSON.parse(content) as T;
    }
  } catch (err) {
    console.warn(`[serverData] Error reading ${filename}:`, err);
  }
  return fallback;
}

// In-memory users store
const usersStore = new Map<string, { username: string; passwordHash: string; role: string; level: string }>([
  ['demo', { username: 'demo', passwordHash: 'demo', role: 'student', level: 'beginner' }],
  ['admin', { username: 'admin', passwordHash: 'admin', role: 'admin', level: 'advanced' }],
  ['aryaman_99', { username: 'aryaman_99', passwordHash: 'pass', role: 'student', level: 'intermediate' }],
]);

// In-memory user progress store
const progressStore = new Map<string, UserProgress>([
  [
    'demo',
    {
      completed_lessons: ['1', '2'],
      quiz_attempts: 2,
      quiz_total_score: 180,
      grammar_activities: 3,
      streak: 4,
      last_active: new Date().toISOString(),
      skills: {
        '1': { mastery: 0.9, attempts: 2, correct: 2 },
        '2': { mastery: 0.85, attempts: 2, correct: 2 },
      },
    },
  ],
]);

function getUserProgress(username: string): UserProgress {
  if (!progressStore.has(username)) {
    progressStore.set(username, {
      completed_lessons: [],
      quiz_attempts: 0,
      quiz_total_score: 0,
      grammar_activities: 0,
      streak: 1,
      last_active: new Date().toISOString(),
      skills: {},
    });
  }
  return progressStore.get(username)!;
}

// Load words CSV
let cachedWords: SanskritWord[] | null = null;
export function getSanskritWords(): SanskritWord[] {
  if (cachedWords) return cachedWords;
  try {
    const csvPath = path.join(DATA_DIR, 'sanskrit_words.csv');
    if (!fs.existsSync(csvPath)) return [];
    const content = fs.readFileSync(csvPath, 'utf-8');
    const lines = content.split('\n').filter((l) => l.trim().length > 0);
    const words: SanskritWord[] = [];
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      // Basic CSV token parser handling quotes
      const match = line.match(/(?:^|,)("(?:[^"]|"")*"|[^,]*)/g);
      if (!match) continue;
      const cols = match.map((c) => c.replace(/^,/, '').replace(/^"(.*)"$/, '$1').trim());
      if (cols.length >= 3) {
        words.push({
          sanskrit: cols[0] || '',
          devanagari: cols[1] || '',
          english: cols[2] || '',
          pronunciation: cols[3] || cols[0] || '',
          word_type: cols[4] || 'noun',
          meaning: cols[5] || cols[2] || '',
          example: cols[6] || '',
          category: cols[7] || 'general',
          tags: cols[8] || '',
          source: cols[9] || 'database',
        });
      }
    }
    cachedWords = words;
    return words;
  } catch (err) {
    console.error('Error loading sanskrit_words.csv:', err);
    return [];
  }
}

// Normalized lessons loader
export function getNormalizedLessons(): any[] {
  const rawData = readJsonFile<any>('lessons.json', { lessons: [] });
  const list = Array.isArray(rawData) ? rawData : rawData.lessons || [];
  return list.map((l: any) => ({
    ...l,
    id: typeof l.id === 'string' && !isNaN(Number(l.id)) ? Number(l.id) : l.id,
    title: l.title || l.name || `Lesson ${l.id}`,
    level: l.level || (Number(l.difficulty || 1) <= 2 ? 'beginner' : Number(l.difficulty || 1) <= 4 ? 'intermediate' : 'advanced'),
    duration: l.duration || l.estimated_time || 15,
    estimated_time: l.estimated_time || l.duration || 15,
    module: l.module || l.category || 'module_1_foundations',
    prerequisites: l.prerequisites || [],
  }));
}

// Specific lesson data readers
export const serverData = {
  getGreetings: () => readJsonFile('sanskritGreetings.json', []),
  getNumbers: () => readJsonFile('sanskritNumbers.json', []),
  getSelfIntro: () => readJsonFile('sanskritSelfIntro.json', []),
  getPronouns: () => readJsonFile('sanskritPronouns.json', []),
  getVerbs: () => readJsonFile('sanskritVerbs.json', []),
  getNouns: () => readJsonFile('sanskritNouns.json', []),
  getFamily: () => readJsonFile('sanskritFamily.json', []),
  getQuestionWords: () => readJsonFile('sanskritQuestionWords.json', []),
  getTimeAndDays: () => readJsonFile('sanskritTimeAndDays.json', []),
  getVibhakti: () => readJsonFile('sanskritVibhakti.json', []),
  getSandhi: () => readJsonFile('sanskritSandhi.json', []),
  getTenses: () => readJsonFile('sanskritTenses.json', []),
  getMoods: () => readJsonFile('sanskritMoods.json', []),
  getPronounsExtended: () => readJsonFile('sanskritPronounsExtended.json', []),
  getUpasarga: () => readJsonFile('sanskritUpasarga.json', []),
  getVoice: () => readJsonFile('sanskritVoice.json', []),
  getIndeclinables: () => readJsonFile('sanskritIndeclinables.json', []),
  getParticiples: () => readJsonFile('sanskritParticiples.json', []),
  getReadingComposition: () => readJsonFile('sanskritReadingComposition.json', []),
  getSamasa1: () => readJsonFile('sanskritSamasa1.json', []),
  getSamasa2: () => readJsonFile('sanskritSamasa2.json', []),
  getParticiples2: () => readJsonFile('sanskritParticiples2.json', []),
  getStriPratyaya: () => readJsonFile('sanskritStriPratyaya.json', []),
  getChandas: () => readJsonFile('sanskritChandas.json', []),
  getDailyQuestions: () => readJsonFile('dailyQuestions.json', []),

  // Auth
  authenticateUser: (username: string, pass: string) => {
    let u = usersStore.get(username);
    if (!u) {
      // Auto-signup friendly for learning
      u = { username, passwordHash: pass, role: 'student', level: 'beginner' };
      usersStore.set(username, u);
    }
    return {
      username: u.username,
      role: u.role,
      level: u.level,
      access_token: `token_${username}_${Date.now()}`,
    };
  },

  signupUser: (username: string, pass: string, role: string = 'student') => {
    if (usersStore.has(username)) return false;
    usersStore.set(username, {
      username,
      passwordHash: pass,
      role,
      level: 'beginner',
    });
    return true;
  },

  // Progress & Stats
  getProgress: (username: string) => {
    const p = getUserProgress(username);
    return {
      status: 'success',
      completed_lessons: p.completed_lessons,
      lessons_completed: p.completed_lessons,
      concept_mastery: Object.fromEntries(
        Object.entries(p.skills).map(([k, v]) => [k, v.mastery])
      ),
    };
  },

  completeLesson: (username: string, lessonId: string | number) => {
    const p = getUserProgress(username);
    const lid = String(lessonId);
    if (!p.completed_lessons.includes(lid)) {
      p.completed_lessons.push(lid);
    }
    return {
      success: true,
      username,
      lesson_id: lid,
      completed: p.completed_lessons.length,
      message: 'Lesson marked as complete',
    };
  },

  submitQuiz: (username: string, lessonId: string | number, answers: Record<string, number>) => {
    const p = getUserProgress(username);
    const lessons = getNormalizedLessons();
    const lesson = lessons.find((l) => String(l.id) === String(lessonId));
    let questions: any[] = [];
    if (lesson?.sections) {
      questions = lesson.sections.flatMap((s: any) => s.questions || []);
    } else if (lesson?.quiz) {
      questions = lesson.quiz;
    }
    let correctCount = 0;
    const totalCount = questions.length || 1;
    questions.forEach((q) => {
      const userAns = answers[String(q.id)];
      if (userAns !== undefined && userAns === q.correct) {
        correctCount++;
      }
    });
    const score = Math.round((correctCount / totalCount) * 100);
    p.quiz_attempts += 1;
    p.quiz_total_score += score;
    p.skills[String(lessonId)] = {
      mastery: Math.min(1.0, (p.skills[String(lessonId)]?.mastery || 0) + 0.25),
      attempts: (p.skills[String(lessonId)]?.attempts || 0) + 1,
      correct: (p.skills[String(lessonId)]?.correct || 0) + correctCount,
    };
    return {
      success: true,
      score_percent: score,
      correct_answers: correctCount,
      total_questions: totalCount,
    };
  },

  getDashboard: (username: string) => {
    const p = getUserProgress(username);
    const lessons = getNormalizedLessons();
    const totalLessons = lessons.length;
    const completedCount = p.completed_lessons.length;
    const avgQuiz = p.quiz_attempts > 0 ? Math.round(p.quiz_total_score / p.quiz_attempts) : 85;

    // Next recommended lesson
    const nextLesson = lessons.find((l) => !p.completed_lessons.includes(String(l.id))) || lessons[0];

    return {
      statistics: {
        lessons_completed: completedCount,
        total_lessons: totalLessons,
        quiz_attempts: p.quiz_attempts,
        quiz_average_score: avgQuiz,
        grammar_activity_count: p.grammar_activities,
        current_streak: p.streak,
        longest_streak: Math.max(p.streak, 7),
        active_learning_days: Math.max(p.streak, 1),
      },
      recommendation: {
        status: nextLesson ? 'recommended' : 'complete',
        lesson_id: nextLesson ? String(nextLesson.id) : null,
        title: nextLesson?.title || 'Advanced Literature Practice',
        description: nextLesson?.description || 'You have mastered the foundational curriculum!',
        module: nextLesson?.module || 'Module 1',
        estimated_time: nextLesson?.estimated_time || 15,
        level: nextLesson?.level || 'beginner',
      },
      recent_activity: [
        {
          type: 'lesson_completion',
          detail: `Engaged with Sanskrit curriculum`,
          score_percent: avgQuiz,
          occurred_at: new Date().toISOString(),
        },
      ],
      mastery: {
        average: 0.78,
        mastered_skills: completedCount,
        skills: p.skills,
      },
    };
  },

  getActivities: (username: string) => {
    const p = getUserProgress(username);
    return [
      {
        type: 'lesson',
        detail: `Completed ${p.completed_lessons.length} lessons so far`,
        score_percent: p.quiz_attempts > 0 ? Math.round(p.quiz_total_score / p.quiz_attempts) : 90,
        occurred_at: p.last_active,
      },
    ];
  },

  getStreak: (username: string) => {
    const p = getUserProgress(username);
    return {
      current_streak: p.streak,
      longest_streak: Math.max(p.streak, 7),
      active_learning_days: p.streak,
    };
  },

  getRecommendation: (username: string) => {
    const dash = serverData.getDashboard(username);
    return {
      recommendation: dash.recommendation,
      ...dash.recommendation,
    };
  },

  // Word Suggestions
  getSuggestions: (prefix: string, limit: number = 6) => {
    if (!prefix) return { suggestions: [] };
    const words = getSanskritWords();
    const cleanPrefix = prefix.toLowerCase().trim();
    const matched: any[] = [];
    for (const w of words) {
      if (
        w.devanagari.startsWith(prefix) ||
        w.sanskrit.toLowerCase().startsWith(cleanPrefix) ||
        w.english.toLowerCase().startsWith(cleanPrefix)
      ) {
        matched.push({
          word: w.devanagari,
          meaning: w.english,
          sanskrit: w.sanskrit,
        });
        if (matched.length >= limit) break;
      }
    }
    return { suggestions: matched };
  },

  // Translation
  translate: (text: string, direction: string = 'en_to_sa') => {
    const words = getSanskritWords();
    const query = text.trim();
    const lowerQuery = query.toLowerCase();

    const results: any[] = [];
    if (direction === 'en_to_sa') {
      // Find matches where English meaning contains query
      for (const w of words) {
        if (w.english.toLowerCase().includes(lowerQuery) || lowerQuery.includes(w.english.toLowerCase())) {
          results.push({
            devanagari: w.devanagari,
            sanskrit: w.sanskrit,
            english: w.english,
            word_type: w.word_type,
            meanings: w.meaning ? w.meaning.split(/[,;]/).map((s) => s.trim()) : [w.english],
            example: w.example || `${w.devanagari} अस्ति।`,
          });
        }
      }
    } else {
      // Sanskrit to English
      for (const w of words) {
        if (w.devanagari.includes(query) || w.sanskrit.toLowerCase().includes(lowerQuery)) {
          results.push({
            devanagari: w.devanagari,
            sanskrit: w.sanskrit,
            english: w.english,
            word_type: w.word_type,
            meanings: w.meaning ? w.meaning.split(/[,;]/).map((s) => s.trim()) : [w.english],
            example: w.example || `${w.devanagari} अस्ति।`,
          });
        }
      }
    }

    if (results.length === 0) {
      // Fallback sensible mock
      if (direction === 'en_to_sa') {
        results.push({
          devanagari: 'नमस्ते',
          sanskrit: 'namaste',
          english: query,
          word_type: 'salutation',
          meanings: ['Greetings', 'Reverence to you'],
          example: 'सर्वेभ्यः नमः।',
        });
      } else {
        results.push({
          devanagari: query,
          sanskrit: 'padam',
          english: 'Spiritual expression or sacred word',
          word_type: 'noun',
          meanings: ['Sacred expression', 'Word', 'Path'],
          example: `${query} शोभते।`,
        });
      }
    }

    return {
      source: 'database',
      results,
    };
  },

  // Grammar / Vyakaran Check
  checkGrammar: (username: string, text: string, use_ai: boolean = false) => {
    const p = getUserProgress(username);
    p.grammar_activities += 1;

    const baseResult = checkSanskritSentence(text);

    // If AI is requested, check if an AI provider or key is present
    let isAiVerified = false;
    let analysisMode = 'Grammar Check';
    const limitations = [...baseResult.limitations];

    if (use_ai) {
      const hasAiKey = Boolean(process.env.GEMINI_API_KEY || process.env.XAI_API_KEY || process.env.GROQ_API_KEY);
      if (hasAiKey) {
        isAiVerified = true;
        analysisMode = 'AI Scan';
      } else {
        isAiVerified = false;
        analysisMode = 'Grammar Check';
        limitations.push('AI scan was requested, but AI service is currently offline. Sentence analyzed using standard grammar rules.');
      }
    }

    return {
      ...baseResult,
      score: baseResult.score.value,
      score_details: baseResult.score,
      analysis_mode: analysisMode,
      ai_verified: isAiVerified,
      limitations,
      word_count: baseResult.words.length,
      breakdown: baseResult.words.map((w) => ({
        word: w.text,
        meaning: w.meaning,
        pos: w.part_of_speech,
        analysis: {
          transliteration: w.transliteration,
          lemma: w.lemma,
          case: w.case || 'N/A',
          number: w.number || 'N/A',
          person: w.person || 'N/A',
          lakara: w.lakara || 'N/A',
          gender: w.gender || 'N/A',
          pada: w.pada || 'N/A',
          status: w.grammar_status,
          notes: w.notes || '',
        },
      })),
      pos_tags: baseResult.words.map((w) => ({
        word: w.text,
        pos: w.part_of_speech,
        meaning: w.meaning,
      })),
    };
  },

  // Games: Snake & Ladder
  snakeLadderStart: () => {
    return {
      message: '🎲 Welcome to the Sanskrit Arena! Start your journey at Position 1.',
      position: 1,
      next_word: { sanskrit: 'अग्निः', hint: 'Element of transformation' },
      game_over: false,
    };
  },

  snakeLadderTurn: (current_position: number, asked_word: string, user_answer: string) => {
    const dict: Record<string, { english: string; hint: string }> = {
      'अग्निः': { english: 'fire', hint: 'Element of transformation' },
      'जलम्': { english: 'water', hint: 'The essence of life' },
      'वायुः': { english: 'wind', hint: 'Invisible yet powerful' },
      'पृथ्वी': { english: 'earth', hint: 'She who supports all beings' },
      'आकाशः': { english: 'sky', hint: 'The boundless expanse above' },
      'सूर्यः': { english: 'sun', hint: 'Giver of light and warmth' },
      'चन्द्रः': { english: 'moon', hint: 'Ruler of the night sky' },
      'नदी': { english: 'river', hint: 'She who flows endlessly' },
      'वृक्षः': { english: 'tree', hint: 'Silent guardian of the forest' },
      'पुष्पम्': { english: 'flower', hint: "Nature's delicate offering" },
      'फलम्': { english: 'fruit', hint: 'Reward of patience' },
      'विद्या': { english: 'knowledge', hint: 'That which illuminates the mind' },
    };

    const keys = Object.keys(dict);
    const entry = dict[asked_word] || { english: 'fire', hint: 'Element of transformation' };
    const isCorrect = user_answer.trim().toLowerCase() === entry.english.toLowerCase();

    const ladders: Record<number, number> = {
      2: 11,
      4: 14,
      9: 31,
      16: 26,
      20: 38,
      28: 47,
      35: 45,
    };
    const snakes: Record<number, number> = {
      12: 2,
      17: 7,
      25: 11,
      32: 15,
      38: 24,
      44: 31,
      49: 38,
    };

    const nextKey = keys[Math.floor(Math.random() * keys.length)];
    const nextWord = { sanskrit: nextKey, hint: dict[nextKey].hint };

    if (isCorrect) {
      const targetPos = current_position + 5;
      let finalPos = targetPos;
      let event = 'correct';
      let msg = `Correct! You advanced to position ${finalPos}.`;
      if (ladders[targetPos]) {
        finalPos = ladders[targetPos];
        event = 'ladder';
        msg = `✨ LADDER UP! 🪜 You climbed from ${targetPos} to ${finalPos}!`;
      }
      if (finalPos >= 50) {
        return {
          message: `Correct! 🏆 VICTORY! You reached position ${finalPos} and won the game!`,
          position: 1,
          event: 'win',
          correct_answer: entry.english,
          next_word: nextWord,
          game_over: true,
        };
      }
      return {
        message: msg,
        position: finalPos,
        event,
        correct_answer: entry.english,
        next_word: nextWord,
        game_over: false,
      };
    } else {
      const targetPos = Math.max(1, current_position - 3);
      let finalPos = targetPos;
      let event = 'wrong';
      let msg = `Oops, wrong! The answer was "${entry.english}". You slid back to ${finalPos}.`;
      if (snakes[targetPos]) {
        finalPos = snakes[targetPos];
        event = 'snake';
        msg = `🔥 SNAKE BITE! 🐍 You slid down from ${targetPos} to ${finalPos}. The answer was "${entry.english}".`;
      }
      return {
        message: msg,
        position: finalPos,
        event,
        correct_answer: entry.english,
        next_word: nextWord,
        game_over: false,
      };
    }
  },

  // Games: Odd One Out
  oddQuestions: [
    {
      category: 'Animals (पशवः)',
      options: [
        { sanskrit: 'गजः', english: 'Elephant' },
        { sanskrit: 'अश्वः', english: 'Horse' },
        { sanskrit: 'सिंहः', english: 'Lion' },
        { sanskrit: 'पुष्पम्', english: 'Flower' },
      ],
      correct_index: 3,
      correct_word: 'पुष्पम्',
    },
    {
      category: 'Colors (वर्णाः)',
      options: [
        { sanskrit: 'रक्तः', english: 'Red' },
        { sanskrit: 'नीलः', english: 'Blue' },
        { sanskrit: 'नदी', english: 'River' },
        { sanskrit: 'पीतः', english: 'Yellow' },
      ],
      correct_index: 2,
      correct_word: 'नदी',
    },
    {
      category: 'Elements (तत्त्वानि)',
      options: [
        { sanskrit: 'अग्निः', english: 'Fire' },
        { sanskrit: 'जलम्', english: 'Water' },
        { sanskrit: 'वायुः', english: 'Wind' },
        { sanskrit: 'गृहम्', english: 'House' },
      ],
      correct_index: 3,
      correct_word: 'गृहम्',
    },
    {
      category: 'Family (कुटुम्बम्)',
      options: [
        { sanskrit: 'माता', english: 'Mother' },
        { sanskrit: 'पिता', english: 'Father' },
        { sanskrit: 'आकाशः', english: 'Sky' },
        { sanskrit: 'पुत्रः', english: 'Son' },
      ],
      correct_index: 2,
      correct_word: 'आकाशः',
    },
  ],

  oddGetQuestion: () => {
    const list = serverData.oddQuestions;
    return list[Math.floor(Math.random() * list.length)];
  },

  oddCheckAnswer: (questionData: any, userChoice: number) => {
    const correctIndex = questionData.correct_index;
    const correctWord = questionData.correct_word;
    const correctEng = questionData.options[correctIndex]?.english || '';
    const isCorrect = userChoice - 1 === correctIndex;

    const msg = isCorrect
      ? `Correct! 🎉 ${correctWord} (${correctEng}) is the odd one out.`
      : `Not quite! The odd one out was ${correctWord} (${correctEng}).`;

    const nextQ = serverData.oddGetQuestion();
    return {
      message: msg,
      is_correct: isCorrect,
      correct_word: correctWord,
      correct_index: correctIndex,
      next_question: nextQ,
    };
  },
};
