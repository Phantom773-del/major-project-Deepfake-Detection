import React, { createContext, useContext, useState, useEffect } from 'react';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider, githubProvider } from '../services/firebase';

interface UserProfile {
  name: string;
  email: string;
  phone?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: UserProfile | null;
  login: (email: string, password: string) => boolean;
  socialLogin: (provider: string) => Promise<void>;
  signup: (name: string, email: string, phone: string, password: string) => boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return localStorage.getItem('phantom_is_authenticated') === 'true';
  });

  const [user, setUser] = useState<UserProfile | null>(() => {
    const savedUser = localStorage.getItem('phantom_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  useEffect(() => {
    localStorage.setItem('phantom_is_authenticated', isAuthenticated ? 'true' : 'false');
    if (user) {
      localStorage.setItem('phantom_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('phantom_user');
    }
  }, [isAuthenticated, user]);

  const signup = (name: string, email: string, phone: string, password: string) => {
    // Store registered user in localStorage
    const newUser = { name, email, phone };
    localStorage.setItem('phantom_registered_user', JSON.stringify({ ...newUser, password }));
    return true;
  };

  const login = (email: string, password: string) => {
    const registeredUserRaw = localStorage.getItem('phantom_registered_user');
    
    if (registeredUserRaw) {
      const registeredUser = JSON.parse(registeredUserRaw);
      // Validate against registered user
      if (email === registeredUser.email && password === registeredUser.password) {
        setUser({
          name: registeredUser.name || 'User',
          email: email,
          phone: registeredUser.phone || '',
        });
        setIsAuthenticated(true);
        return true;
      }
    } else {
      // Mock validation if no user is registered (for testing purposes)
      if (email === 'sreeraksha452@gmail.com' && password === 'password123') {
        setUser({
          name: 'Sreeraksha',
          email: email,
        });
        setIsAuthenticated(true);
        return true;
      }
    }
    
    return false; // Authentication failed
  };

  const socialLogin = async (providerName: string) => {
    try {
      const provider = providerName === 'Google' ? googleProvider : githubProvider;
      const result = await signInWithPopup(auth, provider);
      const fbUser = result.user;
      
      setUser({
        name: fbUser.displayName || `${providerName} User`,
        email: fbUser.email || `user@${providerName.toLowerCase()}.com`,
        phone: fbUser.phoneNumber || undefined,
      });
      setIsAuthenticated(true);
    } catch (error: any) {
      console.error(`${providerName} login error:`, error);
      throw error;
    }
  };

  const logout = () => {
    setIsAuthenticated(false);
    setUser(null);
    localStorage.removeItem('phantom_is_authenticated');
    localStorage.removeItem('phantom_user');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, socialLogin, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
