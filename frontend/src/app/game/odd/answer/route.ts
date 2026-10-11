import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function POST(req: Request) {
  try {
    const { question_data, user_choice } = await req.json();
    const result = serverData.oddCheckAnswer(question_data, Number(user_choice));
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || 'Odd answer check failed' }, { status: 500 });
  }
}
