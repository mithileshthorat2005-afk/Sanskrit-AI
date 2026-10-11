import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function POST(req: Request) {
  try {
    const { username, password, role } = await req.json();
    if (!username || !password) {
      return NextResponse.json({ detail: 'Username and password required' }, { status: 400 });
    }
    const success = serverData.signupUser(username, password, role || 'student');
    if (!success) {
      return NextResponse.json({ detail: 'Username already exists' }, { status: 400 });
    }
    return NextResponse.json({ message: 'Account created successfully' });
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || 'Signup failed' }, { status: 400 });
  }
}
