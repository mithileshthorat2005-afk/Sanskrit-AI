import { NextResponse } from 'next/server';
import { getNormalizedLessons } from '@/lib/serverData';

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const level = searchParams.get('level');
  let lessons = getNormalizedLessons();
  if (level) {
    lessons = lessons.filter((l) => l.level === level);
  }
  return NextResponse.json({ success: true, data: lessons, count: lessons.length });
}
