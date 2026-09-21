import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { ShieldCheck, Sparkles, ArrowRight, Lock, User } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState('operator');
  const [password, setPassword] = useState('operator123');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(username, password);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Authentication failed. Check credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = async (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
    setIsSubmitting(true);
    try {
      await login(u, p);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Authentication failed. Check credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090a0f] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Ambient background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[550px] h-[350px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[350px] h-[250px] bg-emerald-600/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/30 bg-blue-950/40 text-blue-400 text-xs font-medium mb-4 shadow-sm">
            <Sparkles className="w-3.5 h-3.5 animate-pulse text-blue-400" />
            <span>Autonomous Invoice-to-Cash</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            AI Accounts Receivable
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Sign in to access your financial operations terminal
          </p>
        </div>

        <Card className="border-[#232634] bg-[#12131a]/95 backdrop-blur-md shadow-2xl">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">Staff Authentication</CardTitle>
            <CardDescription>Enter your operator or administrator credentials</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 p-3 rounded-md bg-red-950/50 border border-red-800/60 text-red-300 text-xs flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1">
                <Input
                  label="Username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="operator or admin"
                  required
                />
              </div>

              <div className="space-y-1">
                <Input
                  label="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>

              <Button
                type="submit"
                variant="primary"
                className="w-full mt-2"
                isLoading={isSubmitting}
              >
                <span>Authenticate Session</span>
                <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </form>

            {/* Quick Demo Credential Autofill */}
            <div className="mt-6 pt-5 border-t border-[#1e212f]">
              <p className="text-xs text-slate-400 mb-2.5 font-medium flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-slate-500" />
                <span>Quick Demo Access:</span>
              </p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleQuickLogin('operator', 'operator123')}
                  className="flex items-center justify-between p-2 rounded-md bg-[#161823] hover:bg-[#1f2231] border border-[#232638] text-xs text-left text-slate-300 hover:text-white transition-all group"
                >
                  <div>
                    <div className="font-medium text-slate-200 group-hover:text-blue-400">AR Operator</div>
                    <div className="text-[10px] text-slate-500">Click to enter as Operator</div>
                  </div>
                  <User className="w-3.5 h-3.5 text-slate-500 group-hover:text-blue-400" />
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin('admin', 'admin123')}
                  className="flex items-center justify-between p-2 rounded-md bg-[#161823] hover:bg-[#1f2231] border border-[#232638] text-xs text-left text-slate-300 hover:text-white transition-all group"
                >
                  <div>
                    <div className="font-medium text-slate-200 group-hover:text-emerald-400">Administrator</div>
                    <div className="text-[10px] text-slate-500">Click to enter as Admin</div>
                  </div>
                  <ShieldCheck className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400" />
                </button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Security watermark */}
        <div className="text-center mt-6 text-[11px] text-slate-600 flex items-center justify-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Zero-trust gateway with constant-time cryptographic verification</span>
        </div>
      </div>
    </div>
  );
};
