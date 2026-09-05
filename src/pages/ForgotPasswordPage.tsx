import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, Mail, ArrowRight, ArrowLeft, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Dynamically use the current host's IP so it works from PC and mobile
      const serverBase = `${window.location.protocol}//${window.location.hostname}:8000`;
      const response = await fetch(`${serverBase}/api/v1/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      
      const data = await response.json();

      if (response.ok && data.success) {
        setIsLoading(false);
        setIsSubmitted(true);
        toast.success('Password reset email sent! Check your inbox.');
      } else {
        setIsLoading(false);
        toast.error(data.message || 'Failed to send reset email. Please try again.');
      }
    } catch (error: any) {
      setIsLoading(false);
      toast.error('Could not connect to server. Make sure the server is running on port 8000.');
      console.error('Forgot password error:', error);
    }
  };


  return (
    <div className="flex-1 flex flex-col justify-center items-center relative overflow-hidden bg-transparent px-4 py-8">
      {/* Background gradients */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute top-[20%] left-[10%] w-96 h-96 rounded-full bg-cyan-600/10 blur-[100px]" />
        <div className="absolute bottom-[20%] right-[10%] w-96 h-96 rounded-full bg-purple-600/10 blur-[100px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="glass-card p-8 md:p-10 border border-slate-800/60 rounded-3xl backdrop-blur-xl shadow-2xl relative overflow-hidden">
          {/* subtle top highlight */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />

          {/* Logo */}
          <div className="flex justify-center mb-6">
            <Link to="/" className="group relative">
              <div className="absolute inset-0 bg-cyan-500/20 blur-xl rounded-full group-hover:bg-cyan-500/30 transition-colors" />
              <div className="relative w-14 h-14 rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 flex items-center justify-center">
                <Shield className="w-7 h-7 text-cyan-400" />
              </div>
            </Link>
          </div>

          {!isSubmitted ? (
            <>
              <div className="text-center mb-6">
                <h1 className="text-2xl md:text-3xl font-black text-white mb-2">Reset Password</h1>
                <p className="text-slate-400 text-xs md:text-sm">
                  Enter your registered email address and we'll send you a password reset link.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300 ml-1">Email Address *</label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                      <Mail className="h-4 w-4 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
                    </div>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 text-white placeholder-slate-500 text-sm outline-none transition-all"
                      placeholder="name@email.com"
                    />
                  </div>
                </div>

                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-blue-600 via-cyan-600 to-blue-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-bold text-sm shadow-lg shadow-blue-500/20 transition-all disabled:opacity-70 disabled:cursor-not-allowed mt-4"
                >
                  {isLoading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      Send Reset Link
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </motion.button>
              </form>
            </>
          ) : (
            <div className="text-center py-4 space-y-4">
              <div className="flex justify-center">
                <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-white">Check Your Inbox</h2>
              <p className="text-slate-400 text-sm leading-relaxed">
                We've sent a password reset link to{' '}
                <span className="text-cyan-400 font-semibold">{email}</span>. Please check your email to proceed.
              </p>
              <button
                type="button"
                onClick={() => setIsSubmitted(false)}
                className="text-xs text-slate-500 hover:text-slate-400 underline"
              >
                Didn't receive the email? Try again
              </button>
            </div>
          )}

          <div className="mt-8 text-center border-t border-slate-800/80 pt-6">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Login
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
