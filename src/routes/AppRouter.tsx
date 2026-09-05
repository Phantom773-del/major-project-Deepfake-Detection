import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LandingLayout } from '../layouts/LandingLayout';
import { AppLayout } from '../layouts/AppLayout';
import { LandingPage } from '../pages/LandingPage';
import { LoginPage } from '../pages/LoginPage';
import { SignUpPage } from '../pages/SignUpPage';
import { ForgotPasswordPage } from '../pages/ForgotPasswordPage';
import { ResetPasswordPage } from '../pages/ResetPasswordPage';
import { DashboardPage } from '../pages/DashboardPage';
import { UploadPage } from '../pages/UploadPage';
import { AnalysisPage } from '../pages/AnalysisPage';
import { ReportPage } from '../pages/ReportPage';
import { AnalyticsPage } from '../pages/AnalyticsPage';
import { ScanHistoryPage } from '../pages/ScanHistoryPage';
import { SettingsPage } from '../pages/SettingsPage';
import { ProfilePage } from '../pages/ProfilePage';
import { useAuth } from '../contexts/AuthContext';
import { ProtectedRoute } from '../components/common/ProtectedRoute';

export const AppRouter: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Landing Layout Routes */}
      <Route element={<LandingLayout />}>
        <Route path="/" element={isAuthenticated ? <LandingPage /> : <Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      {/* App Layout Routes - Protected */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/report/:id" element={<ReportPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/scan-history" element={<ScanHistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
