/**
 * API Service - Centralized API calls to FastAPI backend
 */
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Get authentication token from localStorage
 */
const getToken = () => {
  return localStorage.getItem('authToken');
};

/**
 * Set authentication token in localStorage
 */
const setToken = (token) => {
  localStorage.setItem('authToken', token);
};

/**
 * Remove authentication token from localStorage
 */
const removeToken = () => {
  localStorage.removeItem('authToken');
};

/**
 * Make API request with authentication
 */
const apiRequest = async (endpoint, options = {}) => {
  const token = getToken();
  const url = `${API_BASE_URL}${endpoint}`;

  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);

    // Handle non-JSON responses
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return null;
    }

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `HTTP error! status: ${response.status}`);
    }

    return data;
  } catch (error) {
    console.error('API request error:', error);
    throw error;
  }
};

// ==================== AUTHENTICATION ====================

export const authAPI = {
  /**
   * Register a new user
   */
  register: async (userData) => {
    return apiRequest('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },

  /**
   * Login user
   */
  login: async (email, password) => {
    const response = await apiRequest('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (response && response.access_token) {
      setToken(response.access_token);
    }

    return response;
  },

  /**
   * Get current user info
   */
  getCurrentUser: async () => {
    return apiRequest('/api/auth/me');
  },

  /**
   * Logout user - calls backend and clears local storage
   */
  logout: async () => {
    try {
      // Call backend logout endpoint
      await apiRequest('/api/auth/logout', { method: 'POST' });
    } catch (error) {
      console.log('Logout API call failed (token may be expired):', error.message);
    } finally {
      // Always clear local tokens regardless of API success
      removeToken();
      localStorage.removeItem('token');
    }
  },
};

// ==================== USERS ====================

export const userAPI = {
  /**
   * Get current user profile
   */
  getProfile: async () => {
    return apiRequest('/api/users/me');
  },

  /**
   * Update user profile
   */
  updateProfile: async (userData) => {
    return apiRequest('/api/users/me', {
      method: 'PUT',
      body: JSON.stringify(userData),
    });
  },

  /**
   * Get user settings
   */
  getSettings: async () => {
    return apiRequest('/api/users/me/settings');
  },

  /**
   * Update user settings
   */
  updateSettings: async (settings) => {
    return apiRequest('/api/users/me/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  },

  /**
   * Change password
   */
  changePassword: async (currentPassword, newPassword) => {
    return apiRequest('/api/users/me/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },

  /**
   * Delete account
   */
  deleteAccount: async () => {
    return apiRequest('/api/users/me', {
      method: 'DELETE',
    });
  },
};

// ==================== COURSES ====================

export const courseAPI = {
  /**
   * Get all courses
   */
  getAll: async () => {
    return apiRequest('/api/courses');
  },

  /**
   * Get course by ID
   */
  getById: async (courseId) => {
    return apiRequest(`/api/courses/${courseId}`);
  },

  /**
   * Create new course
   */
  create: async (courseData) => {
    return apiRequest('/api/courses', {
      method: 'POST',
      body: JSON.stringify(courseData),
    });
  },

  /**
   * Update course
   */
  update: async (courseId, courseData) => {
    return apiRequest(`/api/courses/${courseId}`, {
      method: 'PUT',
      body: JSON.stringify(courseData),
    });
  },

  /**
   * Delete course
   */
  delete: async (courseId) => {
    return apiRequest(`/api/courses/${courseId}`, {
      method: 'DELETE',
    });
  },
};

// ==================== LESSONS ====================

export const lessonAPI = {
  /**
   * Get lessons for a course
   */
  getByCourse: async (courseId) => {
    return apiRequest(`/api/courses/${courseId}/lessons`);
  },

  /**
   * Get lesson by ID
   */
  getById: async (lessonId) => {
    return apiRequest(`/api/courses/lessons/${lessonId}`);
  },

  /**
   * Create new lesson
   */
  create: async (lessonData) => {
    return apiRequest('/api/courses/lessons', {
      method: 'POST',
      body: JSON.stringify(lessonData),
    });
  },

  /**
   * Update lesson
   */
  update: async (lessonId, lessonData) => {
    return apiRequest(`/api/courses/lessons/${lessonId}`, {
      method: 'PUT',
      body: JSON.stringify(lessonData),
    });
  },

  /**
   * Delete lesson
   */
  delete: async (lessonId) => {
    return apiRequest(`/api/courses/lessons/${lessonId}`, {
      method: 'DELETE',
    });
  },
};

// ==================== PROGRESS ====================

export const progressAPI = {
  /**
   * Get dashboard statistics
   */
  getDashboardStats: async () => {
    return apiRequest('/api/progress/dashboard');
  },

  /**
   * Get user progress for lessons
   */
  getLessonProgress: async () => {
    return apiRequest('/api/progress/lessons');
  },

  /**
   * Create or update lesson progress
   */
  updateLessonProgress: async (progressData) => {
    return apiRequest('/api/progress/lessons', {
      method: 'POST',
      body: JSON.stringify(progressData),
    });
  },

  /**
   * Update specific progress record
   */
  updateProgress: async (progressId, progressData) => {
    return apiRequest(`/api/progress/lessons/${progressId}`, {
      method: 'PUT',
      body: JSON.stringify(progressData),
    });
  },

  /**
   * Get practice sessions
   */
  getPracticeSessions: async (practiceType = null) => {
    const endpoint = practiceType
      ? `/api/progress/practice?practice_type=${practiceType}`
      : '/api/progress/practice';
    return apiRequest(endpoint);
  },

  /**
   * Create practice session
   */
  createPracticeSession: async (sessionData) => {
    return apiRequest('/api/progress/practice', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    });
  },

  /**
   * Get achievements
   */
  getAchievements: async () => {
    return apiRequest('/api/progress/achievements');
  },

  /**
   * Create achievement
   */
  createAchievement: async (title, description, icon) => {
    return apiRequest('/api/progress/achievements', {
      method: 'POST',
      body: JSON.stringify({ title, description, icon }),
    });
  },

  /**
   * Get module progress
   */
  getModuleProgress: async () => {
    return apiRequest('/api/progress/modules');
  },

  /**
   * Get specific module progress
   */
  getModuleProgressByName: async (moduleName) => {
    return apiRequest(`/api/progress/modules/${moduleName}`);
  },

  /**
   * Update module progress
   */
  updateModuleProgress: async (moduleId, progressData) => {
    return apiRequest(`/api/progress/modules/${moduleId}`, {
      method: 'PUT',
      body: JSON.stringify(progressData),
    });
  },

  /**
   * Export progress report as PDF
   */
  exportPDF: async () => {
    const token = getToken();
    const response = await fetch(`${API_BASE_URL}/api/progress/export/pdf`, {
      method: 'GET',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Download the PDF
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `progress_report_${new Date().toISOString().slice(0, 10)}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();

    return true;
  },
};

// ==================== ACCENT / PRONUNCIATION ====================

export const accentAPI = {
  /**
   * Analyze user's pronunciation from audio file
   * @param {File} audioFile - The audio file to analyze
   * @param {string} targetAccent - The target accent (e.g., 'british')
   * @param {string} targetText - The expected sentence the user should have said
   */
  analyzeAudio: async (audioFile, targetAccent = 'british', targetText = 'The quick brown fox jumps over the lazy dog.') => {
    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('target_accent', targetAccent);
    formData.append('target_text', targetText);

    const token = getToken();
    const response = await fetch(`${API_BASE_URL}/api/accent/analyze`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  /**
   * Get user's accent analysis sessions
   */
  getSessions: async () => {
    return apiRequest('/api/accent/sessions');
  },

  /**
   * Get session by ID
   */
  getSessionById: async (sessionId) => {
    return apiRequest(`/api/accent/sessions/${sessionId}`);
  },

  /**
   * Get audio URL for playback
   */
  getAudioUrl: (sessionId, audioType) => {
    return `${API_BASE_URL}/api/accent/audio/public/${sessionId}/${audioType}`;
  },

  /**
   * Compare user audio with native speaker
   */
  compareAudio: async (sessionId) => {
    return apiRequest(`/api/accent/compare/${sessionId}`, {
      method: 'POST',
    });
  },

  /**
   * Get practice sentences organized by category
   */
  getSentences: async () => {
    return apiRequest('/api/accent/sentences');
  },

  /**
   * Get phonetic information for a single word
   * Returns IPA, syllables, respelling
   */
  getWordPhonetics: async (word) => {
    return apiRequest(`/api/accent/phonetics/word/${encodeURIComponent(word)}`);
  },

  /**
   * Get phonetic information for all words in a sentence
   */
  getSentencePhonetics: async (sentence) => {
    const formData = new FormData();
    formData.append('sentence', sentence);

    const token = getToken();
    const response = await fetch(`${API_BASE_URL}/api/accent/phonetics/sentence`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  /**
   * Streaming analysis - returns results progressively via Server-Sent Events
   * @param {File} audioFile - The audio file to analyze
   * @param {string} targetAccent - The target accent (e.g., 'british')
   * @param {string} targetText - The expected sentence
   * @param {Function} onProgress - Callback for progress updates
   * @returns {Promise} - Resolves when complete
   */
  analyzeAudioStream: async (audioFile, targetAccent = 'british', targetText = '', onProgress) => {
    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('target_accent', targetAccent);
    formData.append('target_text', targetText);

    const token = getToken();

    return new Promise((resolve, reject) => {
      fetch(`${API_BASE_URL}/api/accent/analyze-stream`, {
        method: 'POST',
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: formData,
      }).then(response => {
        if (!response.ok) {
          reject(new Error(`HTTP error! status: ${response.status}`));
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        const processStream = () => {
          reader.read().then(({ done, value }) => {
            if (done) {
              return;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));

                  if (onProgress) {
                    onProgress(data);
                  }

                  if (data.stage === 'complete') {
                    resolve(data.data);
                  } else if (data.stage === 'error') {
                    reject(new Error(data.message));
                  }
                } catch (e) {
                  console.error('SSE parse error:', e);
                }
              }
            }

            processStream();
          }).catch(reject);
        };

        processStream();
      }).catch(reject);
    });
  },
};

// ==================== GRAMMAR CHECKING ====================

export const grammarAPI = {
  /**
   * Full grammar analysis - checks grammar, spelling, style, and provides corrections
   */
  fullCheck: async (text) => {
    return apiRequest('/api/grammar/check', {
      method: 'POST',
      body: JSON.stringify({ text, check_type: 'full' }),
    });
  },

  /**
   * Quick grammar check - returns only essential errors (optimized for real-time)
   */
  quickCheck: async (text) => {
    return apiRequest('/api/grammar/quick-check', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },

  /**
   * Get word alternatives/synonyms
   */
  getAlternatives: async (text) => {
    return apiRequest('/api/grammar/alternatives', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },

  /**
   * Grammar-only check (LanguageTool)
   */
  grammarOnly: async (text) => {
    return apiRequest('/api/grammar/check', {
      method: 'POST',
      body: JSON.stringify({ text, check_type: 'grammar' }),
    });
  },

  /**
   * Advanced correction with T5
   */
  advancedCorrection: async (text) => {
    return apiRequest('/api/grammar/check', {
      method: 'POST',
      body: JSON.stringify({ text, check_type: 'correction' }),
    });
  },

  /**
   * NLP analysis (missing parts, complexity)
   */
  nlpAnalysis: async (text) => {
    return apiRequest('/api/grammar/check', {
      method: 'POST',
      body: JSON.stringify({ text, check_type: 'nlp' }),
    });
  },
};

// Export token management functions
export { getToken, setToken, removeToken };

