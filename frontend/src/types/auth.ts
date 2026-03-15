export interface User {
  id: string;
  email: string;
  username: string;
  role: 'admin' | 'user';
  status: string;
  lastLoginAt: string | null;
  createdAt: string;
}

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}
