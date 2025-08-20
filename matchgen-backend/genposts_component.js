// GenPosts Component - Comprehensive Social Media Post Generator
// This component allows users to select a specific match and generate all types of social media posts

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

const GenPosts = () => {
  const { matchId } = useParams(); // Get match ID from URL params
  const navigate = useNavigate();
  
  // State management with proper initialization
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [matches, setMatches] = useState([]);
  const [clubData, setClubData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [generatedPosts, setGeneratedPosts] = useState({});
  const [selectedPack, setSelectedPack] = useState(null);
  const [graphicPacks, setGraphicPacks] = useState([]);

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
      
      // If matchId is provided, find and set the selected match
      if (matchId) {
        const match = response.data.find(m => m.id === parseInt(matchId));
        if (match) {
          setSelectedMatch(match);
        }
      }
    } catch (error) {
      console.error('Error fetching matches:', error);
    }
  }, [api, matchId]);

  const fetchGraphicPacks = useCallback(async () => {
    try {
      const response = await api.get('/api/graphicpack/packs/');
      setGraphicPacks(response.data);
    } catch (error) {
      console.error('Error fetching graphic packs:', error);
    }
  }, [api]);

  // Load data on component mount
  useEffect(() => {
    fetchClubData();
    fetchMatches();
    fetchGraphicPacks();
  }, [fetchClubData, fetchMatches, fetchGraphicPacks]);

  // Handle match selection
  const handleMatchSelect = (match) => {
    setSelectedMatch(match);
    // Update URL without page reload
    navigate(`/gen/posts/${match.id}`, { replace: true });
  };

  // Handle graphic pack selection
  const handlePackSelect = async (packId) => {
    try {
      await api.post('/api/graphicpack/select/', { pack_id: packId });
      setSelectedPack(graphicPacks.find(pack => pack.id === packId));
    } catch (error) {
      console.error('Error selecting graphic pack:', error);
    }
  };

  // Generate specific post type
  const generatePost = async (contentType, additionalData = {}) => {
    if (!selectedMatch) {
      alert('Please select a match first');
      return;
    }

    setIsGenerating(true);
    try {
      const response = await api.post('/api/graphicpack/generate/', {
        content_type: contentType,
        match_id: selectedMatch.id,
        ...additionalData
      });

      setGeneratedPosts(prev => ({
        ...prev,
        [contentType]: response.data
      }));

      return response.data;
    } catch (error) {
      console.error(`Error generating ${contentType}:`, error);
      alert(`Error generating ${contentType}: ${error.response?.data?.error || error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // Generate all post types for the selected match
  const generateAllPosts = async () => {
    if (!selectedMatch) {
      alert('Please select a match first');
      return;
    }

    setIsGenerating(true);
    const postTypes = [
      'matchday',
      'startingXI', 
      'upcomingFixture',
      'goal',
      'sub',
      'halftime',
      'fulltime'
    ];

    const results = {};
    
    for (const postType of postTypes) {
      try {
        const result = await generatePost(postType);
        results[postType] = result;
      } catch (error) {
        results[postType] = { error: error.message };
      }
    }

    setGeneratedPosts(results);
    setIsGenerating(false);
  };

  // Post type configurations
  const postTypes = [
    {
      id: 'matchday',
      name: 'Matchday Post',
      description: 'Pre-match announcement and team lineup',
      icon: '⚽',
      color: 'bg-blue-500'
    },
    {
      id: 'startingXI',
      name: 'Starting XI',
      description: 'Team starting lineup graphic',
      icon: '👥',
      color: 'bg-green-500'
    },
    {
      id: 'upcomingFixture',
      name: 'Upcoming Fixture',
      description: 'Next match preview',
      icon: '📅',
      color: 'bg-purple-500'
    },
    {
      id: 'goal',
      name: 'Goal Celebration',
      description: 'Goal scorer celebration graphic',
      icon: '🎯',
      color: 'bg-yellow-500',
      requiresInput: true,
      inputLabel: 'Scorer Name',
      inputPlaceholder: 'Enter scorer name'
    },
    {
      id: 'sub',
      name: 'Substitution',
      description: 'Player substitution announcement',
      icon: '🔄',
      color: 'bg-orange-500',
      requiresInput: true,
      inputLabel: 'Substitution Details',
      inputPlaceholder: 'Player In / Player Out'
    },
    {
      id: 'halftime',
      name: 'Halftime Score',
      description: 'Half-time score update',
      icon: '⏸️',
      color: 'bg-indigo-500',
      requiresInput: true,
      inputLabel: 'Halftime Score',
      inputPlaceholder: 'e.g., 1-0'
    },
    {
      id: 'fulltime',
      name: 'Full-time Result',
      description: 'Final match result',
      icon: '🏁',
      color: 'bg-red-500',
      requiresInput: true,
      inputLabel: 'Final Score',
      inputPlaceholder: 'e.g., 2-1'
    }
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Error Loading Data</h2>
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Social Media Posts</h1>
              <p className="text-gray-600 mt-1">Generate graphics for your matches</p>
            </div>
            {clubData && (
              <div className="text-right">
                <p className="text-sm text-gray-500">Club</p>
                <p className="font-semibold text-gray-900">{clubData.name}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Match Selection */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Select Match</h2>
          
          {selectedMatch ? (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-blue-900">
                    {selectedMatch.club_name} vs {selectedMatch.opponent}
                  </h3>
                  <p className="text-blue-700">
                    {new Date(selectedMatch.date).toLocaleDateString()} • {selectedMatch.venue}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedMatch(null)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  Change Match
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {matches.map((match) => (
                <div
                  key={match.id}
                  onClick={() => handleMatchSelect(match)}
                  className="border border-gray-200 rounded-lg p-4 cursor-pointer hover:border-blue-300 hover:bg-blue-50 transition-colors"
                >
                  <h3 className="font-semibold text-gray-900">
                    {match.club_name} vs {match.opponent}
                  </h3>
                  <p className="text-gray-600 text-sm">
                    {new Date(match.date).toLocaleDateString()}
                  </p>
                  <p className="text-gray-500 text-sm">{match.venue}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Graphic Pack Selection */}
        {selectedMatch && (
          <div className="bg-white rounded-lg shadow-sm border p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Graphic Pack</h2>
            
            {selectedPack ? (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-green-900">{selectedPack.name}</h3>
                    <p className="text-green-700">{selectedPack.description}</p>
                  </div>
                  <button
                    onClick={() => setSelectedPack(null)}
                    className="text-green-600 hover:text-green-800"
                  >
                    Change Pack
                  </button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {graphicPacks.map((pack) => (
                  <div
                    key={pack.id}
                    onClick={() => handlePackSelect(pack.id)}
                    className="border border-gray-200 rounded-lg p-4 cursor-pointer hover:border-green-300 hover:bg-green-50 transition-colors"
                  >
                    <h3 className="font-semibold text-gray-900">{pack.name}</h3>
                    <p className="text-gray-600 text-sm">{pack.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Post Generation */}
        {selectedMatch && selectedPack && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900">Generate Posts</h2>
              <button
                onClick={generateAllPosts}
                disabled={isGenerating}
                className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGenerating ? 'Generating...' : 'Generate All Posts'}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {postTypes.map((postType) => (
                <PostTypeCard
                  key={postType.id}
                  postType={postType}
                  onGenerate={generatePost}
                  isGenerating={isGenerating}
                  generatedPost={generatedPosts[postType.id]}
                />
              ))}
            </div>
          </div>
        )}

        {/* Generated Posts Display */}
        {Object.keys(generatedPosts).length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border p-6 mt-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Generated Posts</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(generatedPosts).map(([type, post]) => (
                <GeneratedPostCard key={type} type={type} post={post} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Post Type Card Component
const PostTypeCard = ({ postType, onGenerate, isGenerating, generatedPost }) => {
  const [inputValue, setInputValue] = useState('');
  const [showInput, setShowInput] = useState(false);

  const handleGenerate = () => {
    if (postType.requiresInput) {
      if (!showInput) {
        setShowInput(true);
        return;
      }
      if (!inputValue.trim()) {
        alert('Please enter the required information');
        return;
      }
    }

    const additionalData = postType.requiresInput ? { [postType.inputLabel.toLowerCase().replace(/\s+/g, '_')]: inputValue } : {};
    onGenerate(postType.id, additionalData);
    setShowInput(false);
    setInputValue('');
  };

  return (
    <div className={`border border-gray-200 rounded-lg p-4 ${generatedPost ? 'bg-green-50 border-green-200' : ''}`}>
      <div className="flex items-center mb-3">
        <span className="text-2xl mr-3">{postType.icon}</span>
        <div>
          <h3 className="font-semibold text-gray-900">{postType.name}</h3>
          <p className="text-gray-600 text-sm">{postType.description}</p>
        </div>
      </div>

      {showInput && postType.requiresInput && (
        <div className="mb-3">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {postType.inputLabel}
          </label>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={postType.inputPlaceholder}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      )}

      <button
        onClick={handleGenerate}
        disabled={isGenerating}
        className={`w-full ${postType.color} text-white px-4 py-2 rounded-md hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {generatedPost ? 'Regenerate' : 'Generate'}
      </button>

      {generatedPost && (
        <div className="mt-3 text-sm text-green-700">
          ✓ Generated successfully
        </div>
      )}
    </div>
  );
};

// Generated Post Card Component
const GeneratedPostCard = ({ type, post }) => {
  if (post.error) {
    return (
      <div className="border border-red-200 rounded-lg p-4 bg-red-50">
        <h3 className="font-semibold text-red-900 capitalize">{type.replace(/([A-Z])/g, ' $1')}</h3>
        <p className="text-red-700 text-sm mt-1">Error: {post.error}</p>
      </div>
    );
  }

  return (
    <div className="border border-green-200 rounded-lg p-4 bg-green-50">
      <h3 className="font-semibold text-green-900 capitalize">{type.replace(/([A-Z])/g, ' $1')}</h3>
      {post.image_url && (
        <div className="mt-3">
          <img 
            src={post.image_url} 
            alt={`Generated ${type} post`}
            className="w-full h-32 object-cover rounded-md"
          />
          <div className="mt-2 flex space-x-2">
            <a
              href={post.image_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              View Full Size
            </a>
            <a
              href={post.image_url}
              download
              className="text-green-600 hover:text-green-800 text-sm"
            >
              Download
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

export default GenPosts;
