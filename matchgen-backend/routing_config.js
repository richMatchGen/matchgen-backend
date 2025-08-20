// Routing Configuration for MatchGen Frontend
// This file shows how to set up routes for the Dashboard and GenPosts components

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Import components
import Dashboard from './components/Dashboard';
import GenPosts from './components/GenPosts';
import Login from './components/Login';
import Register from './components/Register';
import Header from './components/Header';
import ProtectedRoute from './components/ProtectedRoute';

// Main App Router
const AppRouter = () => {
  return (
    <Router>
      <div className="App">
        <Header />
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* Protected Routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          
          {/* GenPosts Routes */}
          <Route path="/gen/posts" element={
            <ProtectedRoute>
              <GenPosts />
            </ProtectedRoute>
          } />
          
          <Route path="/gen/posts/:matchId" element={
            <ProtectedRoute>
              <GenPosts />
            </ProtectedRoute>
          } />
          
          {/* Other protected routes */}
          <Route path="/content/matches" element={
            <ProtectedRoute>
              <MatchManagement />
            </ProtectedRoute>
          } />
          
          <Route path="/content/players" element={
            <ProtectedRoute>
              <PlayerManagement />
            </ProtectedRoute>
          } />
          
          <Route path="/graphicpack/packs" element={
            <ProtectedRoute>
              <GraphicPackManagement />
            </ProtectedRoute>
          } />
          
          {/* Catch all route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

// Navigation Helper Functions
export const navigationHelpers = {
  // Navigate to dashboard
  goToDashboard: (navigate) => navigate('/'),
  
  // Navigate to GenPosts for a specific match
  goToGenPosts: (navigate, matchId) => {
    if (matchId) {
      navigate(`/gen/posts/${matchId}`);
    } else {
      navigate('/gen/posts');
    }
  },
  
  // Navigate to match management
  goToMatches: (navigate) => navigate('/content/matches'),
  
  // Navigate to player management
  goToPlayers: (navigate) => navigate('/content/players'),
  
  // Navigate to graphic pack management
  goToGraphicPacks: (navigate) => navigate('/graphicpack/packs'),
  
  // Navigate to login
  goToLogin: (navigate) => navigate('/login'),
  
  // Navigate to register
  goToRegister: (navigate) => navigate('/register'),
};

// URL Constants
export const URLS = {
  DASHBOARD: '/',
  GEN_POSTS: '/gen/posts',
  GEN_POSTS_WITH_MATCH: (matchId) => `/gen/posts/${matchId}`,
  MATCHES: '/content/matches',
  PLAYERS: '/content/players',
  GRAPHIC_PACKS: '/graphicpack/packs',
  LOGIN: '/login',
  REGISTER: '/register',
};

// Breadcrumb Configuration
export const breadcrumbConfig = {
  '/': { label: 'Dashboard', icon: '🏠' },
  '/gen/posts': { label: 'Generate Posts', icon: '📱' },
  '/content/matches': { label: 'Matches', icon: '⚽' },
  '/content/players': { label: 'Players', icon: '👥' },
  '/graphicpack/packs': { label: 'Graphic Packs', icon: '🎨' },
};

export default AppRouter;

// Example usage in components:

/*
// In Dashboard component:
import { useNavigate } from 'react-router-dom';
import { navigationHelpers } from './routing_config';

const Dashboard = () => {
  const navigate = useNavigate();
  
  const handleMatchSelect = (match) => {
    navigationHelpers.goToGenPosts(navigate, match.id);
  };
  
  return (
    // ... component JSX
  );
};

// In GenPosts component:
import { useParams, useNavigate } from 'react-router-dom';
import { navigationHelpers } from './routing_config';

const GenPosts = () => {
  const { matchId } = useParams();
  const navigate = useNavigate();
  
  const handleBackToDashboard = () => {
    navigationHelpers.goToDashboard(navigate);
  };
  
  return (
    // ... component JSX
  );
};

// In Header component:
import { useNavigate, useLocation } from 'react-router-dom';
import { navigationHelpers, breadcrumbConfig } from './routing_config';

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const currentBreadcrumb = breadcrumbConfig[location.pathname] || { label: 'Unknown', icon: '❓' };
  
  return (
    <header>
      <nav>
        <button onClick={() => navigationHelpers.goToDashboard(navigate)}>
          Dashboard
        </button>
        <button onClick={() => navigationHelpers.goToGenPosts(navigate)}>
          Generate Posts
        </button>
        {/* ... other navigation items */}
      </nav>
      <div className="breadcrumb">
        {currentBreadcrumb.icon} {currentBreadcrumb.label}
      </div>
    </header>
  );
};
*/
