import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function POST(req: Request) {
  try {
    const { current_position, asked_word, user_answer } = await req.json();
    const result = serverData.snakeLadderTurn(
      Number(current_position || 1),
      asked_word || '',
      user_answer || ''
    );
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || 'Game turn failed' }, { status: 500 });
  }
}
