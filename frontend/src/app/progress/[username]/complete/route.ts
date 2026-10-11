import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function POST(req: Request, { params }: { params: Promise<{ username: string }> }) {
  const { username } = await params;
  const body = await req.json();
  const lessonId = body.lesson_id;
  if (!lessonId) {
    return NextResponse.json({ detail: 'lesson_id is required' }, { status: 400 });
  }
  const result = serverData.completeLesson(username, lessonId);
  return NextResponse.json(result);
}
