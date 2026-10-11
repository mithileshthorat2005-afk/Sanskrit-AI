"use client";

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import AudioPronounceButton from '@/components/AudioPronounceButton';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  Award,
  BookOpen,
  CheckCircle,
  ChevronRight,
  Circle,
  Clock,
  Lock,
  Sparkles,
  Star,
  TrendingUp,
  Unlock,
} from 'lucide-react';

interface LessonSection {
  type?: string;
  title?: string;
  content?: string;
  words?: Array<{ sanskrit?: string; transliteration?: string; english?: string; fun_fact?: string }>;
  questions?: Array<{
    id?: number | string;
    question?: string;
    options?: string[];
    correct?: number;
    explanation?: string;
  }>;
}

interface Lesson {
  id: string;
  title: string;
  description: string;
  level: string;
  module: string;
  difficulty: number;
  prerequisites: string[];
  estimated_time: number;
  sections: LessonSection[];
  badge?: {
    name: string;
    description: string;
    icon: string;
  };
}

interface ProgressState {
  completed_lessons: string[];
  concept_mastery: Record<string, number>;
}

const EMPTY_PROGRESS: ProgressState = {
  completed_lessons: [],
  concept_mastery: {},
};

function normalizeProgress(raw: any): ProgressState {
  if (!raw) return EMPTY_PROGRESS;

  if (Array.isArray(raw.completed_lessons)) {
    return {
      completed_lessons: raw.completed_lessons,
      concept_mastery: raw.concept_mastery || {},
    };
  }

  if (raw.status === 'success') {
    return {
      completed_lessons: raw.lessons_completed || raw.completed_lessons || [],
      concept_mastery: raw.progress?.concept_mastery || raw.concept_mastery || {},
    };
  }

  return {
    completed_lessons: raw.lessons_completed || raw.completed_lessons || [],
    concept_mastery: raw.progress?.concept_mastery || raw.concept_mastery || {},
  };
}

function isLessonAvailable(lesson: Lesson, completed: string[]) {
  if (!lesson.prerequisites || lesson.prerequisites.length === 0) return true;
  return lesson.prerequisites.every((prereq) => completed.includes(prereq));
}

export default function LessonDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [allLessons, setAllLessons] = useState<Lesson[]>([]);
  const [progress, setProgress] = useState<ProgressState>(EMPTY_PROGRESS);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [available, setAvailable] = useState(true);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [quizIndex, setQuizIndex] = useState(0);
  const [quizSubmitting, setQuizSubmitting] = useState(false);
  const [quizSubmitted, setQuizSubmitted] = useState(false);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const accessToken = localStorage.getItem('access_token');
    if (!storedUser || !accessToken) {
      router.replace('/');
      return;
    }

    const currentUser = JSON.parse(storedUser);
    setUser(currentUser);

    const fetchData = async () => {
      try {
        setAnswers({});
        setQuizSubmitted(false);
        const [lessonsResponse, lessonResponse, progressResponse] = await Promise.all([
          api.lessons.getAll().catch(() => ({ success: false })),
          api.lessons.getById(params.id as string).catch(() => ({ success: false })),
          api.bkt.getProgress(currentUser.username).catch(() => ({ status: 'error' })),
        ]);

        if (lessonsResponse?.success) {
          setAllLessons(lessonsResponse.data || []);
        }

        if (lessonResponse?.success) {
          setLesson(lessonResponse.data || null);
        }

        const normalizedProgress = normalizeProgress(progressResponse);
        setProgress(normalizedProgress);
        setCompleted(normalizedProgress.completed_lessons.includes(params.id as string));
      } catch (error) {
        console.error('Failed to load lesson data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [params.id, router]);

  useEffect(() => {
    if (!lesson) return;
    setAvailable(isLessonAvailable(lesson, progress.completed_lessons));
    setCompleted(progress.completed_lessons.includes(lesson.id));
  }, [lesson, progress]);

  const quizQuestions = useMemo(() => {
    return (lesson?.sections || []).flatMap((section) => section.questions || []);
  }, [lesson]);

  const answeredCount = Object.keys(answers).length;
  const correctCount = quizQuestions.filter((question) => {
    const qid = String(question.id ?? '');
    return answers[qid] === question.correct;
  }).length;
  const score = quizQuestions.length ? Math.round((correctCount / quizQuestions.length) * 100) : 0;

  const nextLesson = useMemo(() => {
    return allLessons.find((item) => {
      if (progress.completed_lessons.includes(item.id)) return false;
      return isLessonAvailable(item, progress.completed_lessons);
    });
  }, [allLessons, progress]);

  const currentQuestion = quizQuestions[quizIndex] || null;

  const handleAnswer = (questionId: string | number, optionIndex: number) => {
    setAnswers((prev) => ({ ...prev, [String(questionId)]: optionIndex }));
  };

  const goToQuestion = (index: number) => {
    if (quizQuestions.length === 0) return;
    setQuizIndex(Math.max(0, Math.min(index, quizQuestions.length - 1)));
  };

  const submitQuiz = async () => {
    if (!user?.username || !lesson?.id || answeredCount !== quizQuestions.length) return;

    setQuizSubmitting(true);
    try {
      await api.bkt.submitQuiz(user.username, lesson.id, answers);
      setQuizSubmitted(true);
    } catch (error) {
      console.error('Failed to submit quiz:', error);
      alert('Failed to save quiz result.');
    } finally {
      setQuizSubmitting(false);
    }
  };

  const markComplete = async () => {
    if (!available) {
      alert('🔒 Complete the prerequisites before unlocking this lesson.');
      return;
    }

    if (!user?.username || !lesson?.id) {
      alert('❌ Lesson is not ready yet. Please reload the page.');
      return;
    }

    try {
      await api.bkt.markLessonComplete(user.username, lesson.id);
      const updatedCompleted = Array.from(new Set([...progress.completed_lessons, lesson.id]));
      setProgress((prev) => ({ ...prev, completed_lessons: updatedCompleted }));
      setCompleted(true);

      const targetLesson = allLessons.find((item) => {
        if (updatedCompleted.includes(item.id)) return false;
        return isLessonAvailable(item, updatedCompleted);
      });

      if (targetLesson) {
        setTimeout(() => router.push(`/lessons/${targetLesson.id}`), 450);
      } else {
        setTimeout(() => router.push('/lessons'), 450);
      }
    } catch (error) {
      console.error('Failed to mark lesson complete:', error);
      alert('❌ Failed to mark lesson complete.');
    }
  };

  if (loading) {
    return (
      <div className="page-layout">
        <Sidebar user={user} />
        <main className="main-content">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="text-4xl mb-4 animate-pulse">🕉️</div>
              <p className="text-gray-500 dark:text-gray-400">Loading lesson...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="page-layout">
        <Sidebar user={user} />
        <main className="main-content">
          <div className="text-center py-12">
            <h2 className="text-xl font-semibold text-gray-600 dark:text-gray-400">Lesson not found</h2>
            <button
              onClick={() => router.push('/lessons')}
              className="mt-4 text-terracotta hover:underline"
            >
              Back to lessons
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="page-layout">
      <Sidebar user={user} />
      <main className="main-content mx-auto max-w-4xl">
        <button
          onClick={() => router.push('/lessons')}
          className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-terracotta transition-colors hover:text-terracotta-dark"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Lessons
        </button>

        <motion.article
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
        >
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <span className={`rounded-full px-2 py-1 text-xs font-medium ${
              lesson.level === 'beginner'
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                : lesson.level === 'intermediate'
                  ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
                  : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
            }`}>
              {lesson.level}
            </span>

            <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="h-3.5 w-3.5" />
              {lesson.estimated_time || 20} min
            </span>

            <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Star className="h-3.5 w-3.5" />
              {lesson.difficulty || 1}/5
            </span>

            {completed ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
                <CheckCircle className="h-3.5 w-3.5" />
                Completed
              </span>
            ) : available ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                <Unlock className="h-3.5 w-3.5" />
                Available
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                <Lock className="h-3.5 w-3.5" />
                Locked
              </span>
            )}
          </div>

          <h1 className="mb-3 text-3xl font-bold text-gray-800 dark:text-gray-200">{lesson.title}</h1>
          <p className="mb-6 text-base text-gray-600 dark:text-gray-300">{lesson.description}</p>

          {lesson.prerequisites && lesson.prerequisites.length > 0 && (
            <div className="mb-6 rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300">
                Prerequisites
              </h3>
              <div className="flex flex-wrap gap-2">
                {lesson.prerequisites.map((prereq) => {
                  const prereqLesson = allLessons.find((item) => item.id === prereq);
                  const isDone = progress.completed_lessons.includes(prereq);

                  return (
                    <span
                      key={prereq}
                      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${
                        isDone
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                          : 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {isDone ? <CheckCircle className="h-3.5 w-3.5" /> : <Lock className="h-3.5 w-3.5" />}
                      {prereqLesson?.title || prereq}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {lesson.badge && completed && (
            <div className="mb-6 rounded-xl border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-900 dark:bg-yellow-900/20">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{lesson.badge.icon}</span>
                  <div>
                    <h4 className="font-semibold text-yellow-700 dark:text-yellow-300">{lesson.badge.name}</h4>
                    <p className="text-sm text-yellow-600 dark:text-yellow-400">{lesson.badge.description}</p>
                  </div>
                </div>
                <Award className="h-8 w-8 text-yellow-500" />
              </div>
            </div>
          )}

          <div className="space-y-6">
            {lesson.sections?.map((section, index) => (
              <div key={`${section.title || 'section'}-${index}`} className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50">
                <div className="mb-3 flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-terracotta" />
                  <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-200">
                    {section.title || `Section ${index + 1}`}
                  </h3>
                </div>

                {section.content && (
                  <p className="whitespace-pre-wrap text-sm leading-7 text-gray-600 dark:text-gray-300">
                    {section.content}
                  </p>
                )}

                {section.words && section.words.length > 0 && (
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {section.words.map((word, wordIndex) => (
                      <div key={`${word.sanskrit || 'word'}-${wordIndex}`} className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                        <div className="flex items-center justify-between gap-2">
                          <div className="text-lg font-semibold text-terracotta">{word.sanskrit || '—'}</div>
                          {word.sanskrit && (
                            <AudioPronounceButton text={word.sanskrit} size={16} title={`Pronounce: ${word.sanskrit}`} />
                          )}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">{word.transliteration || '—'}</div>
                        <div className="mt-1 text-sm text-gray-700 dark:text-gray-200">{word.english || '—'}</div>
                        {word.fun_fact && (
                          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">💡 {word.fun_fact}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {section.questions && section.questions.length > 0 && (
                  <div className="mt-4 space-y-4">
                    {section.questions.length > 1 && (
                      <div className="mb-2 flex flex-wrap gap-2">
                        {section.questions.map((question, questionIndex) => {
                          const qid = String(question.id ?? `${index}-${questionIndex}`);
                          const selected = answers[qid];
                          const isCurrent = currentQuestion && qid === String(currentQuestion.id ?? `${index}-${questionIndex}`);

                          return (
                            <button
                              key={qid}
                              type="button"
                              onClick={() => goToQuestion(quizQuestions.findIndex((item) => String(item.id ?? '') === qid))}
                              className={`h-8 min-w-[2rem] rounded-full border px-2 text-xs font-medium ${
                                selected !== undefined
                                  ? 'border-green-500 bg-green-100 text-green-700 dark:border-green-400 dark:bg-green-900/20 dark:text-green-300'
                                  : isCurrent
                                    ? 'border-terracotta bg-terracotta/10 text-terracotta dark:bg-terracotta/20'
                                    : 'border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300'
                              }`}
                            >
                              {questionIndex + 1}
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {section.questions.map((question, questionIndex) => {
                      const qid = String(question.id ?? `${index}-${questionIndex}`);
                      const selected = answers[qid];
                      const isCorrect = selected === question.correct;
                      const showFeedback = typeof selected === 'number';
                      const isCurrentQuestion = currentQuestion && qid === String(currentQuestion.id ?? `${index}-${questionIndex}`);

                      if (!isCurrentQuestion && (section.questions?.length ?? 0) > 1) return null;

                      return (
                        <div key={qid} className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                          <p className="mb-3 font-medium text-gray-800 dark:text-gray-100">
                            {questionIndex + 1}. {question.question}
                          </p>
                          <div className="space-y-2">
                            {question.options?.map((option, optionIndex) => {
                              const selectedThis = selected === optionIndex;
                              const isTheCorrectOption = question.correct === optionIndex;

                              return (
                                <button
                                  key={`${qid}-${optionIndex}`}
                                  type="button"
                                  onClick={() => handleAnswer(qid, optionIndex)}
                                  className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm transition ${
                                    selectedThis && isTheCorrectOption
                                      ? 'border-green-500 bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                                      : selectedThis && !isTheCorrectOption
                                        ? 'border-red-500 bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
                                        : 'border-gray-200 bg-gray-50 text-gray-700 hover:border-terracotta/50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200'
                                  }`}
                                >
                                  <span className="flex h-5 w-5 items-center justify-center rounded-full border border-current text-xs">
                                    {selectedThis ? <Circle className="h-3 w-3 fill-current" /> : <Circle className="h-3 w-3" />}
                                  </span>
                                  <span>{option}</span>
                                </button>
                              );
                            })}
                          </div>

                          {showFeedback && (
                            <div className={`mt-3 rounded-lg px-3 py-2 text-sm ${
                              isCorrect
                                ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300'
                                : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
                            }`}>
                              {isCorrect ? '✅ Correct' : '❌ Incorrect'}
                              {question.explanation && ` — ${question.explanation}`}
                            </div>
                          )}

                          {(section.questions?.length ?? 0) > 1 && (
                            <div className="mt-4 flex justify-between gap-3">
                              <button
                                type="button"
                                onClick={() => goToQuestion(Math.max(0, quizQuestions.findIndex((item) => String(item.id ?? '') === qid) - 1))}
                                className="rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:border-terracotta/50 hover:text-terracotta dark:border-gray-700 dark:text-gray-300"
                              >
                                Previous
                              </button>
                              <button
                                type="button"
                                onClick={() => goToQuestion(Math.min(quizQuestions.length - 1, quizQuestions.findIndex((item) => String(item.id ?? '') === qid) + 1))}
                                className="rounded-lg bg-terracotta px-3 py-2 text-sm font-medium text-white hover:bg-terracotta-dark"
                              >
                                Next
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>

          {quizQuestions.length > 0 && (
            <div className="mt-6 rounded-2xl border border-terracotta/20 bg-orange-50 p-4 dark:bg-orange-900/10">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-terracotta">
                  <Sparkles className="h-4 w-4" />
                  <span className="font-semibold">Quiz progress</span>
                </div>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
                  {answeredCount}/{quizQuestions.length} answered
                </span>
              </div>
              <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-white/70 dark:bg-gray-700">
                <div
                  className="h-full rounded-full bg-terracotta transition-all duration-500"
                  style={{ width: `${(answeredCount / Math.max(quizQuestions.length, 1)) * 100}%` }}
                />
              </div>
              <div className="mt-3 text-sm text-gray-700 dark:text-gray-200">
                Score: <span className="font-semibold">{score}%</span>
                {quizQuestions.length > 0 && (
                  <span className="ml-2 text-gray-500 dark:text-gray-400">
                    ({correctCount}/{quizQuestions.length} correct)
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={submitQuiz}
                disabled={quizSubmitting || quizSubmitted || answeredCount !== quizQuestions.length}
                className="mt-4 flex items-center gap-2 rounded-lg bg-terracotta px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-terracotta-dark disabled:cursor-not-allowed disabled:opacity-50"
              >
                <CheckCircle className="h-4 w-4" />
                {quizSubmitting ? 'Saving Quiz...' : quizSubmitted ? 'Quiz Saved' : 'Submit Quiz'}
              </button>
            </div>
          )}

          <div className="mt-8 space-y-3">
            {!completed && available && (
              <button
                onClick={markComplete}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-terracotta px-4 py-3 font-medium text-white transition-colors hover:bg-terracotta-dark"
              >
                <CheckCircle className="h-5 w-5" />
                Mark Lesson as Complete
              </button>
            )}

            {completed && nextLesson && (
              <button
                onClick={() => router.push(`/lessons/${nextLesson.id}`)}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-4 py-3 font-medium text-white transition-colors hover:bg-emerald-600"
              >
                <TrendingUp className="h-5 w-5" />
                Continue to Next Lesson: {nextLesson.title}
                <ArrowRight className="h-4 w-4" />
              </button>
            )}

            {!available && (
              <div className="flex w-full items-center justify-center gap-2 rounded-xl bg-gray-100 px-4 py-3 font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                <Lock className="h-5 w-5" />
                Complete prerequisites to unlock this lesson
              </div>
            )}

            {completed && !nextLesson && (
              <div className="flex w-full items-center justify-center gap-2 rounded-xl bg-green-100 px-4 py-3 font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
                <Award className="h-5 w-5" />
                You have completed all available lessons.
              </div>
            )}
          </div>
        </motion.article>
      </main>
    </div>
  );
}