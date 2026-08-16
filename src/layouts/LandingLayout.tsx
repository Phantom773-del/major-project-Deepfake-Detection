import React from 'react';
import { Outlet } from 'react-router-dom';
import { LandingNavbar } from '../components/layout/Navbar';
import { Footer } from '../components/layout/Footer';

export const LandingLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-forensic flex flex-col">
      <LandingNavbar />
      <main className="flex-1 flex flex-col pt-20">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
};
