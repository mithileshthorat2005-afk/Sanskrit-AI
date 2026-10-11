/**
 * Sanskrit Grammar Engine
 * -----------------------------------------
 * Deterministic and Paninian-grounded morphological analyzer,
 * clause-level syntactic validator, and correction synthesizer.
 */

import fs from 'fs';
import path from 'path';
import sanscript from '@indic-transliteration/sanscript';

export interface GrammarIssue {
  rule_id: string;
  category: 'subject_verb_agreement' | 'vibhakti_case' | 'verb_form' | 'noun_form' | 'punctuation' | 'syntax';
  severity: 'error' | 'warning' | 'info';
  text: string;
  message: string;
  suggestion: string;
  rule_explanation: string;
  source: 'rule_engine' | 'paninian' | 'ai_assisted';
  confidence: number | null;
}

export interface WordAnalysis {
  text: string;
  transliteration: string;
  meaning: string;
  lemma: string;
  part_of_speech: 'noun' | 'pronoun' | 'verb' | 'indeclinable' | 'adjective' | 'unknown';
  gender: string | null;
  number: 'singular' | 'dual' | 'plural' | null;
  case: 'nominative' | 'accusative' | 'instrumental' | 'dative' | 'ablative' | 'genitive' | 'locative' | 'vocative' | null;
  person: 'first' | 'second' | 'third' | null;
  lakara: 'लट्' | 'लङ्' | 'लृट्' | 'लोट्' | 'विधिलिङ्' | null;
  pada: 'parasmaipada' | 'atmanepada' | null;
  grammar_status: 'valid' | 'invalid' | 'uncertain' | 'not_evaluated';
  analysis_confidence: number | null;
  notes?: string;
}

export interface ClauseAnalysis {
  clause_text: string;
  subject?: string;
  subject_token?: WordAnalysis;
  verb?: string;
  verb_token?: WordAnalysis;
  status: 'valid' | 'error' | 'uncertain';
  notes?: string;
}

export interface GrammarAnalysisResult {
  status: 'success' | 'error';
  analysis_method: 'rule_based' | 'ai_assisted' | 'hybrid';
  score: {
    value: number;
    label: string;
    method: 'rule_based_deduction' | 'ai_normalized';
    reliable: boolean;
  };
  summary: {
    confirmed_errors: number;
    warnings: number;
    information_items: number;
    clause_count: number;
  };
  original_sentence: string;
  corrected_sentence: string;
  correction_status: 'no_correction_needed' | 'suggested' | 'uncertain';
  correction_summary: string;
  issues: GrammarIssue[];
  words: WordAnalysis[];
  clauses: ClauseAnalysis[];
  translation?: string;
  limitations: string[];
  ai_verified?: boolean;
}

// ─────────────────────────────────────────────────────────────
// 1. Curated Lexicons and Morphological Dictionaries
// ─────────────────────────────────────────────────────────────

// Pronoun database with full grammatical annotations
const PRONOUN_MAP: Record<string, Partial<WordAnalysis>> = {
  // First person (अस्मद्)
  'अहम्': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'singular', case: 'nominative', meaning: 'I' },
  'अहं': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'singular', case: 'nominative', meaning: 'I' },
  'आवाम्': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'dual', case: 'nominative', meaning: 'we two' },
  'वयम्': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'plural', case: 'nominative', meaning: 'we' },
  'वयं': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'plural', case: 'nominative', meaning: 'we' },
  'माम्': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'singular', case: 'accusative', meaning: 'me' },
  'मां': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'singular', case: 'accusative', meaning: 'me' },
  'मया': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'singular', case: 'instrumental', meaning: 'by me' },
  'मह्यम्': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'singular', case: 'dative', meaning: 'for me' },
  'मम': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'singular', case: 'genitive', meaning: 'my / mine' },
  'मयि': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'singular', case: 'locative', meaning: 'in me' },
  'अस्माकम्': { lemma: 'अस्मद्', part_of_speech: 'pronoun', person: 'first', number: 'plural', case: 'genitive', meaning: 'our / ours' },

  // Second person (युष्मद्)
  'त्वम्': { lemma: 'युष्मद्', part_of_speech: 'pronoun', person: 'second', number: 'singular', case: 'nominative', meaning: 'you' },
  'त्वं': { lemma: 'युष्मद्', part_of_speech: 'pronoun', person: 'second', number: 'singular', case: 'nominative', meaning: 'you' },
  'युवाम्': { lemma: 'युष्मद्', part_of_speech: 'pronoun', person: 'second', number: 'dual', case: 'nominative', meaning: 'you two' },
  'यूयम्': { lemma: 'युष्मद्', part_of_speech: 'pronoun', person: 'second', number: 'plural', case: 'nominative', meaning: 'you all' },
  'त्वाम्': { lemma: 'युष्मद्', part_of_speech: 'pronoun', person: 'second', number: 'singular', case: 'accusative', meaning: 'you' },
  'त्वया': { lemma: 'युष्मद्', part_of_speech: 'pronoun', person: 'second', number: 'singular', case: 'instrumental', meaning: 'by you' },
  'तुभ्यम्': { lemma: 'युष्मद्', part_of_speech: 'pronoun', person: 'second', number: 'singular', case: 'dative', meaning: 'for you' },
  'तव': { lemma: 'युष्मद्', part_of_speech: 'pronoun', person: 'second', number: 'singular', case: 'genitive', meaning: 'your / yours' },
  'त्वयि': { lemma: 'युष्मद्', part_of_speech: 'pronoun', person: 'second', number: 'singular', case: 'locative', meaning: 'in you' },

  // Third person (तद् - masculine)
  'सः': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'nominative', meaning: 'he / that' },
  'तौ': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'dual', gender: 'masculine', case: 'nominative', meaning: 'those two' },
  'ते': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'plural', gender: 'masculine', case: 'nominative', meaning: 'they' },
  'तम्': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'accusative', meaning: 'him' },
  'तं': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'accusative', meaning: 'him' },
  'तेन': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'instrumental', meaning: 'by him' },
  'तस्मै': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'dative', meaning: 'for him' },
  'तस्य': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'genitive', meaning: 'his' },
  'तस्मिन्': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'locative', meaning: 'in him' },

  // Third person (तद् - feminine)
  'सा': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'feminine', case: 'nominative', meaning: 'she' },
  'ताः': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'plural', gender: 'feminine', case: 'nominative', meaning: 'they (fem)' },
  'ताम्': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'feminine', case: 'accusative', meaning: 'her' },
  'तया': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'feminine', case: 'instrumental', meaning: 'by her' },
  'तस्याः': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'feminine', case: 'genitive', meaning: 'her' },

  // Third person (तद् - neuter)
  'तत्': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'neuter', case: 'nominative', meaning: 'it / that' },
  'तानि': { lemma: 'तद्', part_of_speech: 'pronoun', person: 'third', number: 'plural', gender: 'neuter', case: 'nominative', meaning: 'those (neut)' },

  // Demonstrative (एतद्)
  'एषः': { lemma: 'एतद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'nominative', meaning: 'this (masc)' },
  'एषा': { lemma: 'एतद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'feminine', case: 'nominative', meaning: 'this (fem)' },
  'एतत्': { lemma: 'एतद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'neuter', case: 'nominative', meaning: 'this (neut)' },
  'एते': { lemma: 'एतद्', part_of_speech: 'pronoun', person: 'third', number: 'plural', gender: 'masculine', case: 'nominative', meaning: 'these' },

  // Relative (यद्)
  'यः': { lemma: 'यद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'nominative', meaning: 'who / which' },
  'या': { lemma: 'यद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'feminine', case: 'nominative', meaning: 'who / which (fem)' },
  'यत्': { lemma: 'यद्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'neuter', case: 'nominative', meaning: 'which / what' },
  'ये': { lemma: 'यद्', part_of_speech: 'pronoun', person: 'third', number: 'plural', gender: 'masculine', case: 'nominative', meaning: 'who / those who' },

  // Interrogative (किम्)
  'कः': { lemma: 'किम्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'masculine', case: 'nominative', meaning: 'who?' },
  'का': { lemma: 'किम्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'feminine', case: 'nominative', meaning: 'who? (fem)' },
  'किम्': { lemma: 'किम्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'neuter', case: 'nominative', meaning: 'what?' },
  'किं': { lemma: 'किम्', part_of_speech: 'pronoun', person: 'third', number: 'singular', gender: 'neuter', case: 'nominative', meaning: 'what?' },
};

// Indeclinables / Avyayas with syntactic role
const INDECLINABLES_MAP: Record<string, { meaning: string; role: 'clause_marker' | 'conjunction' | 'adverb' | 'governing_particle' }> = {
  'यदा': { meaning: 'when', role: 'clause_marker' },
  'तदा': { meaning: 'then', role: 'clause_marker' },
  'यदि': { meaning: 'if', role: 'clause_marker' },
  'तर्हि': { meaning: 'then', role: 'clause_marker' },
  'चेत्': { meaning: 'if / provided that', role: 'clause_marker' },
  'यथा': { meaning: 'as / just as', role: 'clause_marker' },
  'तथा': { meaning: 'so / in that way', role: 'clause_marker' },
  'यावत्': { meaning: 'as long as', role: 'clause_marker' },
  'तावत्': { meaning: 'so long', role: 'clause_marker' },
  'यतः': { meaning: 'since / because', role: 'clause_marker' },
  'ततः': { meaning: 'therefore / thence', role: 'clause_marker' },
  'च': { meaning: 'and', role: 'conjunction' },
  'वा': { meaning: 'or', role: 'conjunction' },
  'अपि': { meaning: 'also / even', role: 'adverb' },
  'एव': { meaning: 'only / indeed', role: 'adverb' },
  'न': { meaning: 'not / no', role: 'adverb' },
  'मा': { meaning: 'do not (prohibitive)', role: 'adverb' },
  'अद्य': { meaning: 'today', role: 'adverb' },
  'श्वः': { meaning: 'tomorrow', role: 'adverb' },
  'ह्यः': { meaning: 'yesterday', role: 'adverb' },
  'अत्र': { meaning: 'here', role: 'adverb' },
  'तत्र': { meaning: 'there', role: 'adverb' },
  'कुत्र': { meaning: 'where?', role: 'adverb' },
  'सर्वत्र': { meaning: 'everywhere', role: 'adverb' },
  'कदा': { meaning: 'when?', role: 'adverb' },
  'कथम्': { meaning: 'how?', role: 'adverb' },
  'कथं': { meaning: 'how?', role: 'adverb' },
  'सह': { meaning: 'along with (governs instrumental)', role: 'governing_particle' },
  'साकम्': { meaning: 'together with', role: 'governing_particle' },
  'विना': { meaning: 'without', role: 'governing_particle' },
  'प्रति': { meaning: 'towards (governs accusative)', role: 'governing_particle' },
  'नमः': { meaning: 'salutation / reverence (governs dative)', role: 'governing_particle' },
  'अलम्': { meaning: 'enough / sufficient', role: 'governing_particle' },
  'इति': { meaning: 'thus / quote marker', role: 'adverb' },
  'उच्चैः': { meaning: 'loudly', role: 'adverb' },
  'शनैः': { meaning: 'slowly', role: 'adverb' },
  'पुनः': { meaning: 'again', role: 'adverb' },
  'सदा': { meaning: 'always', role: 'adverb' },
  'सर्वदा': { meaning: 'always / constantly', role: 'adverb' },
  'इदानीम्': { meaning: 'now', role: 'adverb' },
  'अधुना': { meaning: 'now', role: 'adverb' },
};

// Common verb roots (Dhatus) and their standard English translations
const DHATU_REGISTRY: Record<string, { dev: string; meaning: string; present_stem: string }> = {
  'paṭh': { dev: 'पठ्', meaning: 'read / recite', present_stem: 'पठ' },
  'likh': { dev: 'लिख्', meaning: 'write', present_stem: 'लिख' },
  'khād': { dev: 'खाद्', meaning: 'eat', present_stem: 'खाद' },
  'pā': { dev: 'पा / पिब्', meaning: 'drink', present_stem: 'पिब' },
  'gam': { dev: 'गम्', meaning: 'go', present_stem: 'गच्छ' },
  'ā-gam': { dev: 'आ+गम्', meaning: 'come', present_stem: 'आगच्छ' },
  'vad': { dev: 'वद्', meaning: 'speak / say', present_stem: 'वद' },
  'has': { dev: 'हस्', meaning: 'laugh / smile', present_stem: 'हस' },
  'dhāv': { dev: 'धाव्', meaning: 'run', present_stem: 'धाव' },
  'khel': { dev: 'खेल्', meaning: 'play', present_stem: 'खेल' },
  'krīḍ': { dev: 'क्रीड्', meaning: 'play', present_stem: 'क्रीड' },
  'dṛś': { dev: 'दृश् / पश्य्', meaning: 'see / look', present_stem: 'पश्य' },
  'bhū': { dev: 'भू', meaning: 'be / become', present_stem: 'भव' },
  'as': { dev: 'अस्', meaning: 'be / exist', present_stem: 'अस्' },
  'kṛ': { dev: 'कृ', meaning: 'do / make', present_stem: 'करो' },
  'dā': { dev: 'दा', meaning: 'give', present_stem: 'ददा' },
  'pac': { dev: 'पच्', meaning: 'cook', present_stem: 'पच' },
  'śru': { dev: 'श्रु', meaning: 'hear / listen', present_stem: 'शृणो' },
  'sthā': { dev: 'स्था / तिष्ठ्', meaning: 'stand / remain', present_stem: 'तिष्ठ' },
  'nī': { dev: 'नी', meaning: 'lead / carry', present_stem: 'नय' },
  'mil': { dev: 'मिल्', meaning: 'meet', present_stem: 'मिल' },
  'labh': { dev: 'लभ्', meaning: 'obtain / receive', present_stem: 'लभ' },
};

// Known explicit verbal conjugations (for high-fidelity resolution)
const KNOWN_VERBS: Record<string, { lemma: string; lakara: 'लट्' | 'लङ्' | 'लृट्' | 'लोट्' | 'विधिलिङ्'; person: 'first' | 'second' | 'third'; number: 'singular' | 'dual' | 'plural'; meaning: string; pada: 'parasmaipada' | 'atmanepada' }> = {
  // पठ् (paṭh)
  'पठति': { lemma: 'पठ्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'reads / is reading', pada: 'parasmaipada' },
  'पठतः': { lemma: 'पठ्', lakara: 'लट्', person: 'third', number: 'dual', meaning: 'they two read', pada: 'parasmaipada' },
  'पठन्ति': { lemma: 'पठ्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they read', pada: 'parasmaipada' },
  'पठसि': { lemma: 'पठ्', lakara: 'लट्', person: 'second', number: 'singular', meaning: 'you read', pada: 'parasmaipada' },
  'पठथः': { lemma: 'पठ्', lakara: 'लट्', person: 'second', number: 'dual', meaning: 'you two read', pada: 'parasmaipada' },
  'पठथ': { lemma: 'पठ्', lakara: 'लट्', person: 'second', number: 'plural', meaning: 'you all read', pada: 'parasmaipada' },
  'पठामि': { lemma: 'पठ्', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I read', pada: 'parasmaipada' },
  'पठावः': { lemma: 'पठ्', lakara: 'लट्', person: 'first', number: 'dual', meaning: 'we two read', pada: 'parasmaipada' },
  'पठामः': { lemma: 'पठ्', lakara: 'लट्', person: 'first', number: 'plural', meaning: 'we read', pada: 'parasmaipada' },

  // लिख् (likh)
  'लिखति': { lemma: 'लिख्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'writes', pada: 'parasmaipada' },
  'लिखन्ति': { lemma: 'लिख्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they write', pada: 'parasmaipada' },
  'लिखसि': { lemma: 'लिख्', lakara: 'लट्', person: 'second', number: 'singular', meaning: 'you write', pada: 'parasmaipada' },
  'लिखामि': { lemma: 'लिख्', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I write', pada: 'parasmaipada' },
  'लिखामः': { lemma: 'लिख्', lakara: 'लट्', person: 'first', number: 'plural', meaning: 'we write', pada: 'parasmaipada' },

  // गम् (gam)
  'गच्छति': { lemma: 'गम्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'goes', pada: 'parasmaipada' },
  'गच्छतः': { lemma: 'गम्', lakara: 'लट्', person: 'third', number: 'dual', meaning: 'they two go', pada: 'parasmaipada' },
  'गच्छन्ति': { lemma: 'गम्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they go', pada: 'parasmaipada' },
  'गच्छसि': { lemma: 'गम्', lakara: 'लट्', person: 'second', number: 'singular', meaning: 'you go', pada: 'parasmaipada' },
  'गच्छथ': { lemma: 'गम्', lakara: 'लट्', person: 'second', number: 'plural', meaning: 'you all go', pada: 'parasmaipada' },
  'गच्छामि': { lemma: 'गम्', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I go', pada: 'parasmaipada' },
  'गच्छावः': { lemma: 'गम्', lakara: 'लट्', person: 'first', number: 'dual', meaning: 'we two go', pada: 'parasmaipada' },
  'गच्छामः': { lemma: 'गम्', lakara: 'लट्', person: 'first', number: 'plural', meaning: 'we go', pada: 'parasmaipada' },

  // आ + गम् (ā-gam)
  'आगच्छति': { lemma: 'आ+गम्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'comes', pada: 'parasmaipada' },
  'आगच्छन्ति': { lemma: 'आ+गम्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they come', pada: 'parasmaipada' },
  'आगच्छामि': { lemma: 'आ+गम्', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I come', pada: 'parasmaipada' },

  // खाद् (khād)
  'खादति': { lemma: 'खाद्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'eats', pada: 'parasmaipada' },
  'खादन्ति': { lemma: 'खाद्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they eat', pada: 'parasmaipada' },
  'खादसि': { lemma: 'खाद्', lakara: 'लट्', person: 'second', number: 'singular', meaning: 'you eat', pada: 'parasmaipada' },
  'खादामि': { lemma: 'खाद्', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I eat', pada: 'parasmaipada' },
  'खादामः': { lemma: 'खाद्', lakara: 'लट्', person: 'first', number: 'plural', meaning: 'we eat', pada: 'parasmaipada' },

  // पा (pā)
  'पिबति': { lemma: 'पा', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'drinks', pada: 'parasmaipada' },
  'पिबन्ति': { lemma: 'पा', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they drink', pada: 'parasmaipada' },
  'पिबसि': { lemma: 'पा', lakara: 'लट्', person: 'second', number: 'singular', meaning: 'you drink', pada: 'parasmaipada' },
  'पिबामि': { lemma: 'पा', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I drink', pada: 'parasmaipada' },

  // अस् (as)
  'अस्ति': { lemma: 'अस्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'is / exists', pada: 'parasmaipada' },
  'स्तः': { lemma: 'अस्', lakara: 'लट्', person: 'third', number: 'dual', meaning: 'they two are', pada: 'parasmaipada' },
  'सन्ति': { lemma: 'अस्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they are', pada: 'parasmaipada' },
  'असि': { lemma: 'अस्', lakara: 'लट्', person: 'second', number: 'singular', meaning: 'you are', pada: 'parasmaipada' },
  'स्थः': { lemma: 'अस्', lakara: 'लट्', person: 'second', number: 'dual', meaning: 'you two are', pada: 'parasmaipada' },
  'स्थ': { lemma: 'अस्', lakara: 'लट्', person: 'second', number: 'plural', meaning: 'you all are', pada: 'parasmaipada' },
  'अस्मि': { lemma: 'अस्', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I am', pada: 'parasmaipada' },
  'स्वः': { lemma: 'अस्', lakara: 'लट्', person: 'first', number: 'dual', meaning: 'we two are', pada: 'parasmaipada' },
  'स्मः': { lemma: 'अस्', lakara: 'लट्', person: 'first', number: 'plural', meaning: 'we are', pada: 'parasmaipada' },

  // कृ (kṛ)
  'करोति': { lemma: 'कृ', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'does / performs', pada: 'parasmaipada' },
  'कुर्वन्ति': { lemma: 'कृ', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they do', pada: 'parasmaipada' },
  'करोषि': { lemma: 'कृ', lakara: 'लट्', person: 'second', number: 'singular', meaning: 'you do', pada: 'parasmaipada' },
  'करोमि': { lemma: 'कृ', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I do', pada: 'parasmaipada' },
  'कुर्मः': { lemma: 'कृ', lakara: 'लट्', person: 'first', number: 'plural', meaning: 'we do', pada: 'parasmaipada' },

  // भू (bhū)
  'भवति': { lemma: 'भू', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'becomes / is', pada: 'parasmaipada' },
  'भवन्ति': { lemma: 'भू', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they become', pada: 'parasmaipada' },
  'भवसि': { lemma: 'भू', lakara: 'लट्', person: 'second', number: 'singular', meaning: 'you become', pada: 'parasmaipada' },
  'भवामि': { lemma: 'भू', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I become', pada: 'parasmaipada' },
  'भविष्यसि': { lemma: 'भू', lakara: 'लृट्', person: 'second', number: 'singular', meaning: 'you will become', pada: 'parasmaipada' },
  'भविष्यति': { lemma: 'भू', lakara: 'लृट्', person: 'third', number: 'singular', meaning: 'will become', pada: 'parasmaipada' },

  // खेल् / क्रीड्
  'खेलति': { lemma: 'खेल्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'plays', pada: 'parasmaipada' },
  'खेलन्ति': { lemma: 'खेल्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they play', pada: 'parasmaipada' },
  'खेलामि': { lemma: 'खेल्', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I play', pada: 'parasmaipada' },
  'क्रीडति': { lemma: 'क्रीड्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'plays', pada: 'parasmaipada' },
  'क्रीडामि': { lemma: 'क्रीड्', lakara: 'लट्', person: 'first', number: 'singular', meaning: 'I play', pada: 'parasmaipada' },
  'क्रीडामः': { lemma: 'क्रीड्', lakara: 'लट्', person: 'first', number: 'plural', meaning: 'we play', pada: 'parasmaipada' },

  // दा (dā)
  'ददाति': { lemma: 'दा', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'gives', pada: 'parasmaipada' },
  'ददति': { lemma: 'दा', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they give', pada: 'parasmaipada' },

  // पच् (pac)
  'पचति': { lemma: 'पच्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'cooks', pada: 'parasmaipada' },
  'पचन्ति': { lemma: 'पच्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they cook', pada: 'parasmaipada' },

  // वद् (vad)
  'वदति': { lemma: 'वद्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'speaks', pada: 'parasmaipada' },
  'वदन्ति': { lemma: 'वद्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they speak', pada: 'parasmaipada' },

  // लभ् (labh)
  'लभते': { lemma: 'लभ्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'obtains / gains', pada: 'atmanepada' },
  'लभन्ते': { lemma: 'लभ्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they obtain', pada: 'atmanepada' },

  // मिल् (mil)
  'मिलति': { lemma: 'मिल्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'meets', pada: 'parasmaipada' },
  'मिलन्ति': { lemma: 'मिल्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they meet', pada: 'parasmaipada' },

  // उपविशति
  'उपविशति': { lemma: 'उप+विश्', lakara: 'लट्', person: 'third', number: 'singular', meaning: 'sits down', pada: 'parasmaipada' },
  'उपविशन्ति': { lemma: 'उप+विश्', lakara: 'लट्', person: 'third', number: 'plural', meaning: 'they sit down', pada: 'parasmaipada' },
};

// Declension ending patterns (sorted by longest ending first)
const NOUN_DECLENSION_PATTERNS: Array<{ ending: string; gender: string; case: WordAnalysis['case']; number: 'singular' | 'dual' | 'plural' }> = [
  // Plural
  { ending: 'ेभ्यः', gender: 'masculine', case: 'dative', number: 'plural' as const },
  { ending: 'ेभ्यः', gender: 'neuter', case: 'dative', number: 'plural' as const },
  { ending: 'ानाम्', gender: 'masculine', case: 'genitive', number: 'plural' as const },
  { ending: 'ानाम्', gender: 'neuter', case: 'genitive', number: 'plural' as const },
  { ending: 'ानां', gender: 'masculine', case: 'genitive', number: 'plural' as const },
  { ending: 'ानां', gender: 'neuter', case: 'genitive', number: 'plural' as const },
  { ending: 'ेषु', gender: 'masculine', case: 'locative', number: 'plural' as const },
  { ending: 'ेषु', gender: 'neuter', case: 'locative', number: 'plural' as const },
  { ending: 'ान्', gender: 'masculine', case: 'accusative', number: 'plural' as const },
  { ending: 'ानि', gender: 'neuter', case: 'nominative', number: 'plural' as const },
  { ending: 'ैः', gender: 'masculine', case: 'instrumental', number: 'plural' as const },
  { ending: 'ैः', gender: 'neuter', case: 'instrumental', number: 'plural' as const },
  { ending: 'ाः', gender: 'masculine', case: 'nominative', number: 'plural' as const },
  { ending: 'ाः', gender: 'feminine', case: 'nominative', number: 'plural' as const },

  // Dual
  { ending: 'ाभ्याम्', gender: 'masculine', case: 'instrumental', number: 'dual' as const },
  { ending: 'ाभ्यां', gender: 'masculine', case: 'instrumental', number: 'dual' as const },
  { ending: 'योः', gender: 'masculine', case: 'genitive', number: 'dual' as const },
  { ending: 'ौ', gender: 'masculine', case: 'nominative', number: 'dual' as const },

  // Singular
  { ending: 'ेण', gender: 'masculine', case: 'instrumental', number: 'singular' as const },
  { ending: 'ाय', gender: 'masculine', case: 'dative', number: 'singular' as const },
  { ending: 'ात्', gender: 'masculine', case: 'ablative', number: 'singular' as const },
  { ending: 'स्य', gender: 'masculine', case: 'genitive', number: 'singular' as const },
  { ending: 'े', gender: 'masculine', case: 'locative', number: 'singular' as const },
  { ending: 'े', gender: 'neuter', case: 'locative', number: 'singular' as const },
  { ending: 'ायाम्', gender: 'feminine', case: 'locative', number: 'singular' as const },
  { ending: 'ायां', gender: 'feminine', case: 'locative', number: 'singular' as const },
  { ending: 'ायाः', gender: 'feminine', case: 'genitive', number: 'singular' as const },
  { ending: 'ायै', gender: 'feminine', case: 'dative', number: 'singular' as const },
  { ending: 'ाम्', gender: 'feminine', case: 'accusative', number: 'singular' as const },
  { ending: 'ां', gender: 'feminine', case: 'accusative', number: 'singular' as const },
  { ending: 'या', gender: 'feminine', case: 'instrumental', number: 'singular' as const },
  { ending: 'ा', gender: 'feminine', case: 'nominative', number: 'singular' as const },
  { ending: 'म्', gender: 'neuter', case: 'nominative', number: 'singular' as const },
  { ending: 'ं', gender: 'neuter', case: 'nominative', number: 'singular' as const },
  { ending: 'म्', gender: 'masculine', case: 'accusative', number: 'singular' as const },
  { ending: 'ं', gender: 'masculine', case: 'accusative', number: 'singular' as const },
  { ending: 'ः', gender: 'masculine', case: 'nominative', number: 'singular' as const },
];

// Lexical noun dictionary for meanings
const NOUN_MEANINGS: Record<string, { stem: string; meaning: string; gender: string }> = {
  'राम': { stem: 'राम', meaning: 'Rama (proper noun)', gender: 'masculine' },
  'सीता': { stem: 'सीता', meaning: 'Sita (proper noun)', gender: 'feminine' },
  'बालक': { stem: 'बालक', meaning: 'boy', gender: 'masculine' },
  'बालिका': { stem: 'बालिका', meaning: 'girl', gender: 'feminine' },
  'छात्र': { stem: 'छात्र', meaning: 'student / pupil', gender: 'masculine' },
  'छात्रा': { stem: 'छात्रा', meaning: 'female student', gender: 'feminine' },
  'शिक्षक': { stem: 'शिक्षक', meaning: 'teacher / instructor', gender: 'masculine' },
  'विद्यालय': { stem: 'विद्यालय', meaning: 'school / academy', gender: 'masculine' },
  'गृह': { stem: 'गृह', meaning: 'house / home', gender: 'neuter' },
  'वन': { stem: 'वन', meaning: 'forest / woods', gender: 'neuter' },
  'उद्यान': { stem: 'उद्यान', meaning: 'garden / park', gender: 'neuter' },
  'पुस्तक': { stem: 'पुस्तक', meaning: 'book', gender: 'neuter' },
  'फल': { stem: 'फल', meaning: 'fruit', gender: 'neuter' },
  'जल': { stem: 'जल', meaning: 'water', gender: 'neuter' },
  'भोजन': { stem: 'भोजन', meaning: 'food / meal', gender: 'neuter' },
  'माता': { stem: 'मातृ', meaning: 'mother', gender: 'feminine' },
  'पिता': { stem: 'पितृ', meaning: 'father', gender: 'masculine' },
  'मित्र': { stem: 'मित्र', meaning: 'friend', gender: 'neuter' },
  'ज्ञान': { stem: 'ज्ञान', meaning: 'knowledge / wisdom', gender: 'neuter' },
  'कक्षा': { stem: 'कक्षा', meaning: 'classroom', gender: 'feminine' },
  'परिश्रम': { stem: 'परिश्रम', meaning: 'hard work / diligence', gender: 'masculine' },
  'सत्य': { stem: 'सत्य', meaning: 'truth', gender: 'neuter' },
  'विश्वास': { stem: 'विश्वास', meaning: 'trust / faith', gender: 'masculine' },
  'विश्राम': { stem: 'विश्राम', meaning: 'rest / relaxation', gender: 'masculine' },
  'गृहकार्य': { stem: 'गृहकार्य', meaning: 'homework', gender: 'neuter' },
  'पाठ': { stem: 'पाठ', meaning: 'lesson / text', gender: 'masculine' },
  'सूर्य': { stem: 'सूर्य', meaning: 'sun', gender: 'masculine' },
  'चन्द्र': { stem: 'चन्द्र', meaning: 'moon', gender: 'masculine' },
  'वृक्ष': { stem: 'वृक्ष', meaning: 'tree', gender: 'masculine' },
  'नदी': { stem: 'नदी', meaning: 'river', gender: 'feminine' },
  'सफल': { stem: 'सफल', meaning: 'successful', gender: 'masculine' },
};

// ─────────────────────────────────────────────────────────────
// 2. Transliteration & Cleaning Helpers
// ─────────────────────────────────────────────────────────────

export function getTransliteration(devanagari: string): string {
  try {
    return sanscript.t(devanagari, 'devanagari', 'iast');
  } catch {
    return devanagari;
  }
}

function cleanToken(token: string): string {
  return token.replace(/[।॥|.,!?;:()\[\]{}"'“”‘’]/g, '').trim();
}

// ─────────────────────────────────────────────────────────────
// 3. Morphological Word Analyzer
// ─────────────────────────────────────────────────────────────

export function analyzeToken(rawToken: string): WordAnalysis {
  const token = cleanToken(rawToken);
  const translit = getTransliteration(token);

  if (!token) {
    return {
      text: rawToken,
      transliteration: '',
      meaning: '',
      lemma: '',
      part_of_speech: 'unknown',
      gender: null,
      number: null,
      case: null,
      person: null,
      lakara: null,
      pada: null,
      grammar_status: 'not_evaluated',
      analysis_confidence: 0,
    };
  }

  // 1. Check Pronouns
  if (PRONOUN_MAP[token]) {
    const p = PRONOUN_MAP[token];
    return {
      text: token,
      transliteration: translit,
      meaning: p.meaning || '',
      lemma: p.lemma || token,
      part_of_speech: 'pronoun',
      gender: p.gender || null,
      number: p.number || null,
      case: p.case || null,
      person: p.person || null,
      lakara: null,
      pada: null,
      grammar_status: 'valid',
      analysis_confidence: 1.0,
      notes: `${p.person || ''} person ${p.number || ''} ${p.case || ''} pronoun`,
    };
  }

  // 2. Check Indeclinables (Avyayas)
  if (INDECLINABLES_MAP[token]) {
    const ind = INDECLINABLES_MAP[token];
    return {
      text: token,
      transliteration: translit,
      meaning: ind.meaning,
      lemma: token,
      part_of_speech: 'indeclinable',
      gender: null,
      number: null,
      case: null,
      person: null,
      lakara: null,
      pada: null,
      grammar_status: 'valid',
      analysis_confidence: 1.0,
      notes: `Avyaya (${ind.role.replace('_', ' ')})`,
    };
  }

  // 3. Check Known Verbs
  if (KNOWN_VERBS[token]) {
    const v = KNOWN_VERBS[token];
    return {
      text: token,
      transliteration: translit,
      meaning: v.meaning,
      lemma: v.lemma,
      part_of_speech: 'verb',
      gender: null,
      number: v.number,
      case: null,
      person: v.person,
      lakara: v.lakara,
      pada: v.pada,
      grammar_status: 'valid',
      analysis_confidence: 1.0,
      notes: `Root ${v.lemma}, ${v.lakara} (Present), ${v.person} person ${v.number}`,
    };
  }

  // 4. Check known noun stems first (prevents collisions like रामः matching -ामः verb suffix)
  for (const nd of NOUN_DECLENSION_PATTERNS) {
    if (token.endsWith(nd.ending) && token.length >= nd.ending.length) {
      const baseStem = token.slice(0, token.length - nd.ending.length);
      const meaningInfo = NOUN_MEANINGS[baseStem] || NOUN_MEANINGS[baseStem + 'ा'] || NOUN_MEANINGS[baseStem + 'म्'];
      if (meaningInfo) {
        if (meaningInfo.gender && nd.gender !== meaningInfo.gender) {
          continue;
        }
        return {
          text: token,
          transliteration: translit,
          meaning: meaningInfo.meaning,
          lemma: meaningInfo.stem,
          part_of_speech: 'noun',
          gender: nd.gender,
          number: nd.number,
          case: nd.case,
          person: 'third',
          lakara: null,
          pada: null,
          grammar_status: 'valid',
          analysis_confidence: 0.98,
          notes: `${nd.gender} ${nd.case} case ${nd.number}`,
        };
      }
    }
  }

  // 5. Special irregular nominals (माता, पिता, etc.)
  if (token === 'माता') {
    return {
      text: token,
      transliteration: translit,
      meaning: 'mother',
      lemma: 'मातृ',
      part_of_speech: 'noun',
      gender: 'feminine',
      number: 'singular',
      case: 'nominative',
      person: 'third',
      lakara: null,
      pada: null,
      grammar_status: 'valid',
      analysis_confidence: 1.0,
      notes: 'ṛ-stem feminine nominative singular',
    };
  }
  if (token === 'पिता') {
    return {
      text: token,
      transliteration: translit,
      meaning: 'father',
      lemma: 'पितृ',
      part_of_speech: 'noun',
      gender: 'masculine',
      number: 'singular',
      case: 'nominative',
      person: 'third',
      lakara: null,
      pada: null,
      grammar_status: 'valid',
      analysis_confidence: 1.0,
      notes: 'ṛ-stem masculine nominative singular',
    };
  }

  // 6. Rule-based Verb Conjugation Suffix Parser (tiṅanta)
  const verbSuffixes: Array<{ suffix: string; person: 'first' | 'second' | 'third'; number: 'singular' | 'dual' | 'plural'; lakara: 'लट्' | 'लङ्' | 'लृट्' | 'लोट्' | 'विधिलिङ्' }> = [
    // Present (लट्)
    { suffix: 'न्ति', person: 'third', number: 'plural', lakara: 'लट्' },
    { suffix: 'न्ते', person: 'third', number: 'plural', lakara: 'लट्' },
    { suffix: 'तः', person: 'third', number: 'dual', lakara: 'लट्' },
    { suffix: 'ते', person: 'third', number: 'singular', lakara: 'लट्' },
    { suffix: 'ति', person: 'third', number: 'singular', lakara: 'लट्' },
    { suffix: 'थः', person: 'second', number: 'dual', lakara: 'लट्' },
    { suffix: 'थ', person: 'second', number: 'plural', lakara: 'लट्' },
    { suffix: 'सि', person: 'second', number: 'singular', lakara: 'लट्' },
    { suffix: 'से', person: 'second', number: 'singular', lakara: 'लट्' },
    { suffix: 'ामः', person: 'first', number: 'plural', lakara: 'लट्' },
    { suffix: 'ावः', person: 'first', number: 'dual', lakara: 'लट्' },
    { suffix: 'ामि', person: 'first', number: 'singular', lakara: 'लट्' },
    { suffix: 'े', person: 'first', number: 'singular', lakara: 'लट्' },
    // Future (लृट्)
    { suffix: 'िष्यन्ति', person: 'third', number: 'plural', lakara: 'लृट्' },
    { suffix: 'िष्यति', person: 'third', number: 'singular', lakara: 'लृट्' },
    { suffix: 'िष्यसि', person: 'second', number: 'singular', lakara: 'लृट्' },
    { suffix: 'िष्यामि', person: 'first', number: 'singular', lakara: 'लृट्' },
  ];

  for (const vs of verbSuffixes) {
    if (token.endsWith(vs.suffix) && token.length > vs.suffix.length) {
      const stem = token.slice(0, -vs.suffix.length);
      // Verify stem is not an a-stem noun like 'राम'
      if (NOUN_MEANINGS[stem] || stem.length < 2) continue;

      const isKnownDhatu = Object.values(DHATU_REGISTRY).some(
        (d) => d.present_stem === stem || d.dev === stem || stem.startsWith(d.present_stem)
      );

      return {
        text: token,
        transliteration: translit,
        meaning: isKnownDhatu ? `Verb form of root ${stem}` : 'Lexical meaning not in current database',
        lemma: stem,
        part_of_speech: isKnownDhatu ? 'verb' : 'unknown',
        gender: null,
        number: vs.number,
        case: null,
        person: vs.person,
        lakara: vs.lakara,
        pada: 'parasmaipada',
        grammar_status: isKnownDhatu ? 'valid' : 'uncertain',
        analysis_confidence: isKnownDhatu ? 0.9 : 0.3,
        notes: isKnownDhatu
          ? `Inflected finite verb (${vs.lakara}, ${vs.person} person ${vs.number})`
          : `Unrecognized verb stem '${stem}' with suffix -${vs.suffix}`,
      };
    }
  }

  // 6. Noun Declension Analysis (subanta)
  for (const nd of NOUN_DECLENSION_PATTERNS) {
    if (token.endsWith(nd.ending) && token.length >= nd.ending.length) {
      const baseStem = token.slice(0, token.length - nd.ending.length);
      const meaningInfo = NOUN_MEANINGS[baseStem] || NOUN_MEANINGS[baseStem + 'ा'] || NOUN_MEANINGS[baseStem + 'म्'];

      return {
        text: token,
        transliteration: translit,
        meaning: meaningInfo ? meaningInfo.meaning : `Noun (${baseStem})`,
        lemma: meaningInfo ? meaningInfo.stem : baseStem || token,
        part_of_speech: 'noun',
        gender: nd.gender,
        number: nd.number,
        case: nd.case,
        person: 'third',
        lakara: null,
        pada: null,
        grammar_status: 'valid',
        analysis_confidence: meaningInfo ? 0.95 : 0.75,
        notes: `${nd.gender} ${nd.case} case ${nd.number}`,
      };
    }
  }

  // 7. Unknown or Unindexed word
  return {
    text: token,
    transliteration: translit,
    meaning: 'Lexical meaning not in current database',
    lemma: token,
    part_of_speech: 'unknown',
    gender: null,
    number: null,
    case: null,
    person: null,
    lakara: null,
    pada: null,
    grammar_status: 'uncertain',
    analysis_confidence: 0.3,
    notes: 'Unrecognized morphological form',
  };
}

// ─────────────────────────────────────────────────────────────
// 4. Clause Identification & Multi-Clause Segmentation
// ─────────────────────────────────────────────────────────────

interface RawClause {
  tokens: string[];
  clauseType: 'main' | 'subordinate_temporal' | 'subordinate_conditional' | 'coordinate';
}

function segmentIntoClauses(tokens: string[]): RawClause[] {
  const clauses: RawClause[] = [];
  let current: string[] = [];
  let currentType: RawClause['clauseType'] = 'main';

  for (let i = 0; i < tokens.length; i++) {
    const raw = tokens[i];
    const cleaned = cleanToken(raw);

    // Check for clause boundary markers
    if (cleaned === 'यदा') {
      if (current.length > 0) clauses.push({ tokens: current, clauseType: currentType });
      current = [raw];
      currentType = 'subordinate_temporal';
      continue;
    } else if (cleaned === 'तदा') {
      if (current.length > 0) clauses.push({ tokens: current, clauseType: currentType });
      current = [raw];
      currentType = 'main';
      continue;
    } else if (cleaned === 'यदि') {
      if (current.length > 0) clauses.push({ tokens: current, clauseType: currentType });
      current = [raw];
      currentType = 'subordinate_conditional';
      continue;
    } else if (cleaned === 'तर्हि' || cleaned === 'चेत्') {
      if (current.length > 0) clauses.push({ tokens: current, clauseType: currentType });
      current = [raw];
      currentType = 'main';
      continue;
    }

    current.push(raw);
  }

  if (current.length > 0) {
    clauses.push({ tokens: current, clauseType: currentType });
  }

  return clauses.length > 0 ? clauses : [{ tokens, clauseType: 'main' }];
}

// ─────────────────────────────────────────────────────────────
// 5. Syntactic Validation Engine
// ─────────────────────────────────────────────────────────────

export function checkSanskritSentence(rawSentence: string): GrammarAnalysisResult {
  const trimmed = rawSentence.trim();
  const limitations: string[] = [];

  if (!trimmed) {
    return {
      status: 'error',
      analysis_method: 'rule_based',
      score: { value: 0, label: 'Unable to determine reliably', method: 'rule_based_deduction', reliable: false },
      summary: { confirmed_errors: 0, warnings: 0, information_items: 0, clause_count: 0 },
      original_sentence: '',
      corrected_sentence: '',
      correction_status: 'uncertain',
      correction_summary: 'No input text provided.',
      issues: [],
      words: [],
      clauses: [],
      limitations: ['Empty input'],
    };
  }

  // Tokenize preserving words
  const rawTokens = trimmed.split(/\s+/).filter((t) => t.trim().length > 0);
  const words: WordAnalysis[] = rawTokens.map(analyzeToken);

  const issues: GrammarIssue[] = [];
  const clauseAnalyses: ClauseAnalysis[] = [];

  // Punctuation verification (separated from grammatical errors)
  const hasValidPunctuation = trimmed.endsWith('।') || trimmed.endsWith('॥');
  if (!hasValidPunctuation) {
    issues.push({
      rule_id: 'PUNCTUATION_PURNA_VIRAMA',
      category: 'punctuation',
      severity: 'info',
      text: rawTokens[rawTokens.length - 1] || '',
      message: 'Sentence is missing closing Purna Virama (।).',
      suggestion: trimmed + '।',
      rule_explanation: 'Standard Classical Sanskrit prose concludes with a Purna Virama (।) or double virama (॥).',
      source: 'rule_engine',
      confidence: 1.0,
    });
  }

  // Segment sentence into clauses
  const rawClauses = segmentIntoClauses(rawTokens);
  let correctedTokens = [...rawTokens];

  let tokenOffset = 0;
  for (const rc of rawClauses) {
    const clauseWords = rc.tokens.map(analyzeToken);
    const clauseText = rc.tokens.join(' ');

    // Find candidate subject (nominative noun or pronoun)
    const subjects = clauseWords.filter(
      (w) => (w.part_of_speech === 'pronoun' || w.part_of_speech === 'noun') && w.case === 'nominative'
    );
    // Find candidate finite verbs
    const verbs = clauseWords.filter((w) => w.part_of_speech === 'verb');

    let clauseStatus: ClauseAnalysis['status'] = 'valid';
    let clauseNotes = '';

    if (subjects.length > 0 && verbs.length > 0) {
      // Pick dominant subject and verb for this clause
      let subject = subjects[0];
      const verb = verbs[0];

      // If there's a 1st or 2nd person verb, and the only candidate "subject" found is a 3rd-person noun:
      if (verb && (verb.person === 'first' || verb.person === 'second') && subject && subject.part_of_speech === 'noun') {
        // Check if this is a predicate complement (e.g. सफलः भविष्यसि, मित्रम् अस्मि) or correlative clause
        if (verb.lemma === 'भू' || verb.lemma === 'अस्' || rc.clauseType === 'main' || rc.clauseType === 'subordinate_conditional') {
          subject.notes = `${subject.gender || ''} nominative singular (predicate complement)`;
          subject = {
            text: verb.person === 'second' ? '(त्वम्)' : '(अहम्)',
            transliteration: verb.person === 'second' ? 'tvam' : 'aham',
            meaning: verb.person === 'second' ? 'you (implied)' : 'I (implied)',
            lemma: verb.person === 'second' ? 'युष्मद्' : 'अस्मद्',
            part_of_speech: 'pronoun',
            gender: null,
            number: verb.number || 'singular',
            case: 'nominative',
            person: verb.person,
            lakara: null,
            pada: null,
            grammar_status: 'valid',
            analysis_confidence: 1.0,
            notes: 'Implied subject from verb inflection',
          };
        }
      }

      // Disambiguate neuter nouns that may function as accusative objects
      for (let ci = 0; ci < clauseWords.length; ci++) {
        const cw = clauseWords[ci];
        const globalIdx = tokenOffset + ci;
        if (cw.text !== subject.text && cw.part_of_speech === 'noun' && cw.gender === 'neuter') {
          // If the clause already has an explicit subject, a neuter noun with a transitive verb is accusative object
          cw.case = 'accusative';
          cw.notes = `neuter accusative case ${cw.number || 'singular'} (direct object)`;
          if (words[globalIdx]) {
            words[globalIdx].case = 'accusative';
            words[globalIdx].notes = `neuter accusative case ${cw.number || 'singular'} (direct object)`;
          }
        }
      }

      // Check Person & Number Agreement (पुरुष & वचन)
      const subjectPerson = subject.person || (subject.part_of_speech === 'noun' ? 'third' : null);
      const verbPerson = verb.person;
      const subjectNumber = subject.number;
      const verbNumber = verb.number;

      const personMismatch = subjectPerson && verbPerson && subjectPerson !== verbPerson;
      const numberMismatch = subjectNumber && verbNumber && subjectNumber !== verbNumber;

      if (personMismatch && numberMismatch) {
        // Grouped violation: single subject-verb pair has both person and number mismatch
        clauseStatus = 'error';
        const expectedVerbText = getCorrectVerbForm(verb, subjectPerson, subjectNumber);

        issues.push({
          rule_id: 'AGREEMENT_PERSON_AND_NUMBER_MISMATCH',
          category: 'subject_verb_agreement',
          severity: 'error',
          text: `${subject.text} ${verb.text}`,
          message: `Subject '${subject.text}' (${subjectPerson} person, ${subjectNumber}) does not agree with verb '${verb.text}' (${verbPerson} person, ${verbNumber}).`,
          suggestion: `${subject.text} ${expectedVerbText}`,
          rule_explanation: `In Sanskrit grammar, the finite verb must agree with its subject in both person (puruṣa) and number (vacana). '${subject.text}' is ${subjectPerson} person ${subjectNumber}, requiring the verb form '${expectedVerbText}' (person: ${subjectPerson} vs ${verbPerson}; number: ${subjectNumber} vs ${verbNumber}).`,
          source: 'rule_engine',
          confidence: 0.98,
        });

        clauseNotes = `Agreement mismatch: ${subject.text} (${subjectPerson}, ${subjectNumber}) vs ${verb.text} (${verbPerson}, ${verbNumber})`;

        const verbIndex = correctedTokens.findIndex((t) => cleanToken(t) === verb.text);
        if (verbIndex !== -1) {
          const punctMatch = correctedTokens[verbIndex].match(/[।॥.,!?]$/);
          correctedTokens[verbIndex] = expectedVerbText + (punctMatch ? punctMatch[0] : '');
        }
      } else if (personMismatch) {
        // Person mismatch only
        clauseStatus = 'error';
        const expectedVerbText = getCorrectVerbForm(verb, subjectPerson, subject.number || 'singular');

        issues.push({
          rule_id: 'AGREEMENT_PERSON_MISMATCH',
          category: 'subject_verb_agreement',
          severity: 'error',
          text: `${subject.text} ${verb.text}`,
          message: `Subject '${subject.text}' (${subjectPerson} person) does not agree with verb '${verb.text}' (${verbPerson} person).`,
          suggestion: `${subject.text} ${expectedVerbText}`,
          rule_explanation: `In Paninian grammar, the finite verb's tiṅ-pratyaya must agree with the agent (kartā) in person (puruṣa). '${subject.text}' is ${subjectPerson} person, so the verb must be ${subjectPerson} person (${expectedVerbText}).`,
          source: 'rule_engine',
          confidence: 0.98,
        });

        clauseNotes = `Person mismatch: ${subject.text} (${subjectPerson}) vs ${verb.text} (${verbPerson})`;

        const verbIndex = correctedTokens.findIndex((t) => cleanToken(t) === verb.text);
        if (verbIndex !== -1) {
          const punctMatch = correctedTokens[verbIndex].match(/[।॥.,!?]$/);
          correctedTokens[verbIndex] = expectedVerbText + (punctMatch ? punctMatch[0] : '');
        }
      } else if (numberMismatch) {
        // Number mismatch only
        clauseStatus = 'error';
        const expectedVerbText = getCorrectVerbForm(verb, subjectPerson || 'third', subjectNumber);

        issues.push({
          rule_id: 'AGREEMENT_NUMBER_MISMATCH',
          category: 'subject_verb_agreement',
          severity: 'error',
          text: `${subject.text} ${verb.text}`,
          message: `Subject '${subject.text}' (${subjectNumber}) does not agree with verb '${verb.text}' (${verbNumber}).`,
          suggestion: `${subject.text} ${expectedVerbText}`,
          rule_explanation: `The finite verb must agree in number (vacana) with its nominative subject. '${subject.text}' is ${subjectNumber}, requiring the verb to be ${subjectNumber} (${expectedVerbText}).`,
          source: 'rule_engine',
          confidence: 0.98,
        });

        if (clauseNotes) clauseNotes += '; ';
        clauseNotes += `Number mismatch: ${subject.text} (${subjectNumber}) vs ${verb.text} (${verbNumber})`;

        const verbIndex = correctedTokens.findIndex((t) => cleanToken(t) === verb.text);
        if (verbIndex !== -1) {
          const punctMatch = correctedTokens[verbIndex].match(/[।॥.,!?]$/);
          correctedTokens[verbIndex] = expectedVerbText + (punctMatch ? punctMatch[0] : '');
        }
      }

      // Check Karaka / Dvitiya destination rule (गम् धातु + destination in accusative)
      const isMotionVerb = verb.lemma === 'गम्' || verb.lemma === 'आ+गम्' || verb.meaning.includes('go');
      if (isMotionVerb) {
        for (const w of clauseWords) {
          if (w.text !== subject.text && (w.lemma === 'विद्यालय' || w.text.includes('विद्यालय'))) {
            const cleanedW = cleanToken(w.text);
            const isAlreadyAccusative = cleanedW === 'विद्यालयम्' || cleanedW === 'विद्यालयं' || w.case === 'accusative';
            if (!isAlreadyAccusative && (cleanedW === 'विद्यालयः' || w.case === 'nominative')) {
              clauseStatus = 'error';
              issues.push({
                rule_id: 'KARAKA_MOTION_DESTINATION',
                category: 'vibhakti_case',
                severity: 'error',
                text: w.text,
                message: `Destination of motion '${w.text}' must be in Accusative case (द्वितीया विभक्ति - कर्म कारक).`,
                suggestion: 'विद्यालयम्',
                rule_explanation: 'According to Pāṇini sūtra 2.3.2 (कर्मणि द्वितीया) and motion destination rules, the destination reached by verbs of motion takes the accusative case (विद्यालयम् or विद्यालयं).',
                source: 'rule_engine',
                confidence: 0.95,
              });

              // Replace in corrected tokens
              const wIdx = correctedTokens.findIndex((t) => cleanToken(t) === w.text);
              if (wIdx !== -1) {
                const punctMatch = correctedTokens[wIdx].match(/[।॥.,!?]$/);
                correctedTokens[wIdx] = 'विद्यालयम्' + (punctMatch ? punctMatch[0] : '');
              }
            }
          }
        }
      }

      clauseAnalyses.push({
        clause_text: clauseText,
        subject: subject.text,
        subject_token: subject,
        verb: verb.text,
        verb_token: verb,
        status: clauseStatus,
        notes: clauseNotes || 'Subject and verb agree in person and number.',
      });
    } else {
      // Verbless or incomplete clause
      clauseAnalyses.push({
        clause_text: clauseText,
        subject: subjects[0]?.text,
        verb: verbs[0]?.text,
        status: 'valid',
        notes: 'Nominal or subordinate phrase',
      });
    }
    tokenOffset += rc.tokens.length;
  }

  // Filter out any no-op issues where suggestion equals original text
  const validIssues = issues.filter((issue) => {
    if (issue.category === 'punctuation') return true;
    if (issue.text && issue.suggestion && cleanToken(issue.text) === cleanToken(issue.suggestion)) {
      return false;
    }
    return true;
  });

  // Synthesize corrected sentence
  let correctedSentence = correctedTokens.join(' ');
  if (!correctedSentence.endsWith('।') && !correctedSentence.endsWith('॥')) {
    correctedSentence += '।';
  }

  // Count errors vs warnings
  const confirmedErrors = validIssues.filter((i) => i.severity === 'error').length;
  const warnings = validIssues.filter((i) => i.severity === 'warning').length;
  const infos = validIssues.filter((i) => i.severity === 'info').length;

  // Unknown tokens check
  const unknownTokens = words.filter((w) => w.grammar_status === 'uncertain' || w.part_of_speech === 'unknown');
  if (unknownTokens.length > 0) {
    limitations.push(`${unknownTokens.length} token(s) (${unknownTokens.map((u) => u.text).join(', ')}) not fully recognized in lexicon.`);
  }

  // Calculate defensible score:
  // Base 100
  // -25 per confirmed grammatical error
  // -10 per warning
  // -5 for missing punctuation
  let scoreValue = 100;
  scoreValue -= confirmedErrors * 25;
  scoreValue -= warnings * 10;
  if (!hasValidPunctuation) {
    scoreValue -= 5;
  }
  scoreValue = Math.max(0, Math.min(100, scoreValue));

  // Determine reliability and label
  let reliable = true;
  let scoreLabel = 'High correctness';

  if (unknownTokens.length >= Math.ceil(words.length / 2)) {
    reliable = false;
    scoreLabel = 'Unable to determine reliably';
  } else if (scoreValue >= 95) {
    scoreLabel = 'High correctness';
  } else if (scoreValue >= 75) {
    scoreLabel = 'Moderate correctness';
  } else if (scoreValue >= 45) {
    scoreLabel = 'Needs improvement';
  } else {
    scoreLabel = 'Significant errors';
  }

  let actualWordModifications = 0;
  for (let i = 0; i < rawTokens.length; i++) {
    if (cleanToken(rawTokens[i]) !== cleanToken(correctedTokens[i])) {
      actualWordModifications++;
    }
  }

  const isAlreadyCorrect = confirmedErrors === 0 && actualWordModifications === 0;
  const correctionStatus = isAlreadyCorrect
    ? (hasValidPunctuation ? 'no_correction_needed' : 'suggested')
    : confirmedErrors > 0 ? 'suggested' : 'uncertain';
  const correctionSummary = isAlreadyCorrect
    ? (hasValidPunctuation
        ? 'Sentence structure is grammatically sound. No grammatical alterations required.'
        : 'Sentence conforms to Sanskrit grammatical standards. Added closing Purna Virama (।).')
    : `Applied ${confirmedErrors} grammatical correction(s) to align subject-verb concord and case inflections.`;

  return {
    status: 'success',
    analysis_method: 'rule_based',
    score: {
      value: scoreValue,
      label: scoreLabel,
      method: 'rule_based_deduction',
      reliable,
    },
    summary: {
      confirmed_errors: confirmedErrors,
      warnings,
      information_items: infos,
      clause_count: rawClauses.length,
    },
    original_sentence: rawSentence,
    corrected_sentence: isAlreadyCorrect && hasValidPunctuation ? trimmed : correctedSentence,
    correction_status: correctionStatus,
    correction_summary: correctionSummary,
    issues: validIssues,
    words,
    clauses: clauseAnalyses,
    translation: synthesizeSentenceTranslation(words),
    limitations,
  };
}

// ─────────────────────────────────────────────────────────────
// 6. Helper: Conjugate Verb for Subject Person & Number
// ─────────────────────────────────────────────────────────────

function getCorrectVerbForm(verb: WordAnalysis, targetPerson: 'first' | 'second' | 'third', targetNumber: 'singular' | 'dual' | 'plural'): string {
  const root = verb.lemma || 'पठ्';

  // Table of common paradigms (लट् Parasmaipada)
  const paradigmTable: Record<string, Record<string, Record<string, string>>> = {
    'पठ्': {
      first: { singular: 'पठामि', dual: 'पठावः', plural: 'पठामः' },
      second: { singular: 'पठसि', dual: 'पठथः', plural: 'पठथ' },
      third: { singular: 'पठति', dual: 'पठतः', plural: 'पठन्ति' },
    },
    'गम्': {
      first: { singular: 'गच्छामि', dual: 'गच्छावः', plural: 'गच्छामः' },
      second: { singular: 'गच्छसि', dual: 'गच्छथः', plural: 'गच्छथ' },
      third: { singular: 'गच्छति', dual: 'गच्छतः', plural: 'गच्छन्ति' },
    },
    'खाद्': {
      first: { singular: 'खादामि', dual: 'खादावः', plural: 'खादामः' },
      second: { singular: 'खादसि', dual: 'खादथः', plural: 'खादथ' },
      third: { singular: 'खादति', dual: 'खादतः', plural: 'खादन्ति' },
    },
    'पा': {
      first: { singular: 'पिबामि', dual: 'पिबावः', plural: 'पिबामः' },
      second: { singular: 'पिबसि', dual: 'पिबथः', plural: 'पिबथ' },
      third: { singular: 'पिबति', dual: 'पिबतः', plural: 'पिबन्ति' },
    },
    'अस्': {
      first: { singular: 'अस्मि', dual: 'स्वः', plural: 'स्मः' },
      second: { singular: 'असि', dual: 'स्थः', plural: 'स्थ' },
      third: { singular: 'अस्ति', dual: 'स्तः', plural: 'सन्ति' },
    },
    'कृ': {
      first: { singular: 'करोमि', dual: 'कुर्वः', plural: 'कुर्मः' },
      second: { singular: 'करोषि', dual: 'कुरुथः', plural: 'कुरुथ' },
      third: { singular: 'करोति', dual: 'कुरुतः', plural: 'कुर्वन्ति' },
    },
    'खेल्': {
      first: { singular: 'खेलामि', dual: 'खेलावः', plural: 'खेलामः' },
      second: { singular: 'खेलसि', dual: 'खेलथः', plural: 'खेलथ' },
      third: { singular: 'खेलति', dual: 'खेलतः', plural: 'खेलन्ति' },
    },
    'क्रीड्': {
      first: { singular: 'क्रीडामि', dual: 'क्रीडावः', plural: 'क्रीडामः' },
      second: { singular: 'क्रीडसि', dual: 'क्रीडथः', plural: 'क्रीडथ' },
      third: { singular: 'क्रीडति', dual: 'क्रीडतः', plural: 'क्रीडन्ति' },
    },
    'भू': {
      first: { singular: 'भवामि', dual: 'भवावः', plural: 'भवामः' },
      second: { singular: 'भवसि', dual: 'भवथः', plural: 'भवथ' },
      third: { singular: 'भवति', dual: 'भवतः', plural: 'भवन्ति' },
    },
    'लिख्': {
      first: { singular: 'लिखामि', dual: 'लिखावः', plural: 'लिखामः' },
      second: { singular: 'लिखसि', dual: 'लिखथः', plural: 'लिखथ' },
      third: { singular: 'लिखति', dual: 'लिखतः', plural: 'लिखन्ति' },
    },
  };

  if (paradigmTable[root] && paradigmTable[root][targetPerson] && paradigmTable[root][targetPerson][targetNumber]) {
    return paradigmTable[root][targetPerson][targetNumber];
  }

  // Fallback heuristic: strip existing ending, attach proper tiṅ suffix
  let stem = verb.text.replace(/(ामि|ावः|ामः|सि|थः|थ|ति|तः|न्ति|ते|न्ते)$/, '');
  if (targetPerson === 'first') {
    if (targetNumber === 'singular') return stem + 'ामि';
    if (targetNumber === 'dual') return stem + 'ावः';
    return stem + 'ामः';
  } else if (targetPerson === 'second') {
    if (targetNumber === 'singular') return stem + 'सि';
    if (targetNumber === 'dual') return stem + 'थः';
    return stem + 'थ';
  } else {
    if (targetNumber === 'singular') return stem + 'ति';
    if (targetNumber === 'dual') return stem + 'तः';
    return stem + 'न्ति';
  }
}

// ─────────────────────────────────────────────────────────────
// 7. English Translation Synthesizer
// ─────────────────────────────────────────────────────────────

function synthesizeSentenceTranslation(words: WordAnalysis[]): string {
  const parts: string[] = [];
  for (const w of words) {
    if (w.meaning && !w.meaning.startsWith('Lexical meaning')) {
      parts.push(w.meaning);
    }
  }
  return parts.length > 0 ? parts.join(' ') : 'Translation for this construction is unavailable';
}
