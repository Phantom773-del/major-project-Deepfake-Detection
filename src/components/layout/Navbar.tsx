import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Menu, X, ChevronRight } from 'lucide-react';

const navLinks: { label: string; href: string }[] = [];

export const LandingNavbar: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <motion.nav
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'navbar py-3 shadow-2xl' : 'py-5 bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="relative">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-lg group-hover:shadow-blue-500/40 transition-shadow">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div className="absolute -inset-1 bg-cyan-400/20 rounded-lg blur opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div>
            <span className="text-white font-bold text-sm tracking-wide">PHANTOM</span>
            <span className="gradient-text font-bold text-sm tracking-wide ml-1">PHOENIX</span>
          </div>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              to={link.href}
              className={`text-sm font-medium transition-colors hover:text-cyan-400 ${
                location.pathname === link.href ? 'text-cyan-400' : 'text-slate-400'
              }`}
            >
              {link.label}
            </Link>
          ))}
          <Link
            to="/login"
            className={`text-sm font-medium transition-colors hover:text-cyan-400 ${
              location.pathname === '/login' ? 'text-cyan-400' : 'text-slate-400'
            }`}
          >
            Login
          </Link>
          <Link
            to="/signup"
            className={`text-sm font-medium transition-colors hover:text-cyan-400 ${
              location.pathname === '/signup' ? 'text-cyan-400' : 'text-slate-400'
            }`}
          >
            Sign Up
          </Link>
          <Link to="/upload" className="btn-primary text-sm px-5 py-2.5 rounded-lg flex items-center gap-2">
            Start Analysis
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Mobile Menu Button */}
        <button
          className="md:hidden text-slate-400 hover:text-white"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden navbar border-t border-slate-800 mt-2"
          >
            <div className="px-4 py-4 flex flex-col gap-4">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  to={link.href}
                  className="text-slate-300 hover:text-cyan-400 transition-colors py-2"
                  onClick={() => setMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              <Link
                to="/login"
                className="text-slate-300 hover:text-cyan-400 transition-colors py-2"
                onClick={() => setMenuOpen(false)}
              >
                Login
              </Link>
              <Link
                to="/signup"
                className="text-slate-300 hover:text-cyan-400 transition-colors py-2"
                onClick={() => setMenuOpen(false)}
              >
                Sign Up
              </Link>
              <Link
                to="/upload"
                className="btn-primary text-sm text-center py-3 rounded-lg"
                onClick={() => setMenuOpen(false)}
              >
                Start Analysis
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
};
