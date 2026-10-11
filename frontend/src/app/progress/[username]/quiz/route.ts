import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function POST(req: Request, { params }: { params: Promise<{ username: string }> }) {
  const { username } = await params;
  const body = await req.json();
  const { lesson_id, answers } = body;
  if (!lesson_id || !answers) {
    return NextResponse.json({ detail: 'lesson_id and answers required' }, { status: 400 });
  }
  const result = serverData.submitQuiz(username, lesson_id, answers);
  return NextResponse.json(result);
}
