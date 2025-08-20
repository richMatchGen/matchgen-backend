// Dashboard Component - Match Overview with Navigation to GenPosts
// This component displays all matches and allows users to select any match for post generation

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Dashboard = () => {
  const navigate = useNavigate();
  
  // State management with proper initialization
  const [matches, setMatches] = useState([]);
  const [clubData, setClubData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState('all'); // all, upcoming, past, today

  // API configuration
  const api = axios.create({
    baseURL: process.env.REACT_APP_API_URL || 'https://matchgen-backend-production.up.railway.app',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      'Content-Type': 'application/json'
    }
  });

  // Memoized fetch functions to prevent infinite loops
  const fetchClubData = useCallback(async () => {
    if (isLoading) return; // Prevent concurrent requests
    
    setIsLoading(true);
    try {
      const response = await api.get('/api/users/my-club/');
      setClubData(response.data);
      setError(null);
    } catch (error) {
      if (error.response?.status === 429) {
        console.warn('Rate limited - waiting before retry');
        return; // Don't set error for rate limiting
      }
      setError('User might not have a club yet.');
    } finally {
      setIsLoading(false);
    }
  }, [api, isLoading]);

  const fetchMatches = useCallback(async () => {
    try {
      const response = await api.get('/api/content/matches/');
      setMatches(response.data);
    } catch (error) {
      console.error('Error fetching matches:', error);
    }
  }, [api]);

  // Load data on component mount
  useEffect(() => {
    fetchClubData();
    fetchMatches();
  }, [fetchClubData, fetchMatches]);

  // Handle match selection - navigate to GenPosts
  const handleMatchSelect = (match) => {
    navigate(`/gen/posts/${match.id}`);
  };

  // Filter matches based on selected filter
  const getFilteredMatches = () => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    switch (selectedFilter) {
      case 'upcoming':
        return matches.filter(match => new Date(match.date) > today);
      case 'past':
        return matches.filter(match => new Date(match.date) < today);
      case 'today':
        const matchDate = new Date();
        return matches.filter(match => {
          const matchDay = new Date(match.date);
          return matchDay.toDateString() === today.toDateString();
        });
      default:
        return matches;
    }
  };

  // Get match status
  const getMatchStatus = (matchDate) => {
    const today = new Date();
    const match = new Date(matchDate);
    
    if (match.toDateString() === today.toDateString()) {
      return { status: 'today', label: 'Today', color: 'bg-green-100 text-green-800' };
    } else if (match > today) {
      return { status: 'upcoming', label: 'Upcoming', color: 'bg-blue-100 text-blue-800' };
    } else {
      return { status: 'past', label: 'Past', color: 'bg-gray-100 text-gray-800' };
    }
  };

  // Format match date
  const formatMatchDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Error Loading Dashboard</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const filteredMatches = getFilteredMatches();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-gray-600 mt-1">Manage your matches and generate social media posts</p>
            </div>
            {clubData && (
              <div className="text-right">
                <p className="text-sm text-gray-500">Welcome to</p>
                <p className="font-semibold text-gray-900">{clubData.name}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Total Matches</p>
                <p className="text-2xl font-semibold text-gray-900">{matches.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Upcoming</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {matches.filter(match => new Date(match.date) > new Date()).length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Today</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {matches.filter(match => {
                    const today = new Date();
                    const matchDate = new Date(match.date);
                    return matchDate.toDateString() === today.toDateString();
                  }).length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Generate Posts</p>
                <p className="text-2xl font-semibold text-gray-900">Ready</p>
              </div>
            </div>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Matches</h2>
            <div className="flex space-x-2">
              {[
                { key: 'all', label: 'All Matches' },
                { key: 'upcoming', label: 'Upcoming' },
                { key: 'today', label: 'Today' },
                { key: 'past', label: 'Past' }
              ].map((filter) => (
                <button
                  key={filter.key}
                  onClick={() => setSelectedFilter(filter.key)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    selectedFilter === filter.key
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          {/* Matches Grid */}
          {filteredMatches.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">⚽</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No matches found</h3>
              <p className="text-gray-500">
                {selectedFilter === 'all' 
                  ? 'No matches have been added yet.' 
                  : `No ${selectedFilter} matches found.`
                }
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredMatches.map((match) => {
                const status = getMatchStatus(match.date);
                return (
                  <div
                    key={match.id}
                    onClick={() => handleMatchSelect(match)}
                    className="bg-white border border-gray-200 rounded-lg p-6 cursor-pointer hover:border-blue-300 hover:shadow-md transition-all duration-200 group"
                  >
                    {/* Match Header */}
                    <div className="flex items-center justify-between mb-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.color}`}>
                        {status.label}
                      </span>
                      <div className="text-gray-400 group-hover:text-blue-500 transition-colors">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>

                    {/* Match Details */}
                    <div className="mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {match.club_name} vs {match.opponent}
                      </h3>
                      <p className="text-gray-600 text-sm mb-2">
                        {formatMatchDate(match.date)}
                      </p>
                      <p className="text-gray-500 text-sm">
                        📍 {match.venue}
                      </p>
                    </div>

                    {/* Action Button */}
                    <div className="pt-4 border-t border-gray-100">
                      <button className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 transition-colors text-sm font-medium">
                        Generate Posts
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => navigate('/content/matches/create')}
              className="flex items-center p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
            >
              <div className="p-2 bg-blue-100 rounded-lg mr-4">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
              <div className="text-left">
                <h3 className="font-medium text-gray-900">Add New Match</h3>
                <p className="text-sm text-gray-500">Create a new match fixture</p>
              </div>
            </button>

            <button
              onClick={() => navigate('/content/players')}
              className="flex items-center p-4 border border-gray-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition-colors"
            >
              <div className="p-2 bg-green-100 rounded-lg mr-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div className="text-left">
                <h3 className="font-medium text-gray-900">Manage Players</h3>
                <p className="text-sm text-gray-500">Add and edit player profiles</p>
              </div>
            </button>

            <button
              onClick={() => navigate('/graphicpack/packs')}
              className="flex items-center p-4 border border-gray-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors"
            >
              <div className="p-2 bg-purple-100 rounded-lg mr-4">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="text-left">
                <h3 className="font-medium text-gray-900">Graphic Packs</h3>
                <p className="text-sm text-gray-500">Choose your design style</p>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
