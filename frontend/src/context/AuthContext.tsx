import React, { createContext, useContext, useState, useEffect } from 'react';
import apiClient from '@/services/api';
import { UserProfile } from '@/types';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('ar_access_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchCurrentUser = async () => {
    try {
      const response = await apiClient.get<UserProfile>('/auth/me');
      setUser(response.data);
    } catch {
      localStorage.removeItem('ar_access_token');
      localStorage.removeItem('ar_refresh_token');
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    } else {
      setIsLoading(false);
    }

    const handleAuthExpired = () => {
      setToken(null);
      setUser(null);
    };

    window.addEventListener('ar_auth_expired', handleAuthExpired);
    return () => window.removeEventListener('ar_auth_expired', handleAuthExpired);
  }, [token]);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await apiClient.post<{ access_token: string; refresh_token: string }>('/auth/login', {
        username,
        password,
      });

      const { access_token, refresh_token } = response.data;
      localStorage.setItem('ar_access_token', access_token);
      localStorage.setItem('ar_refresh_token', refresh_token);
      setToken(access_token);

      // Fetch user profile immediately
      const profileResponse = await apiClient.get<UserProfile>('/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      setUser(profileResponse.data);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('ar_access_token');
    localStorage.removeItem('ar_refresh_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
