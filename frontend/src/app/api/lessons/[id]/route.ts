import { NextResponse } from 'next/server';
import { getNormalizedLessons } from '@/lib/serverData';

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const lessons = getNormalizedLessons();
  const lesson = lessons.find((l) => String(l.id) === String(id));
  if (!lesson) {
    return NextResponse.json({ success: false, message: 'Lesson not found' }, { status: 404 });
  }
  return NextResponse.json({ success: true, data: lesson });
}
