import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for stored user session and validate with backend
    const initAuth = async () => {
      console.log('[AuthContext] Initializing authentication');
      const storedUser = localStorage.getItem('dms_user');
      if (storedUser) {
        try {
          const userData = JSON.parse(storedUser);
          console.log('[AuthContext] Found stored user, validating token');
          // Validate token with backend
          const response = await authAPI.getCurrentUser();
          if (response.success) {
            const user = response.data;
            // Add avatar initials
            user.avatar = user.name.split(' ').map(n => n[0]).join('').toUpperCase();
            setUser(user);
            console.log('[AuthContext] User authenticated:', user.email);
          } else {
            // Invalid token, clear storage
            console.warn('[AuthContext] Token validation failed, clearing storage');
            localStorage.removeItem('dms_user');
          }
        } catch (error) {
          console.error('[AuthContext] Auth validation error:', error);
          console.error('[AuthContext] Error details:', {
            message: error.message,
            stack: error.stack
          });
          localStorage.removeItem('dms_user');
        }
      } else {
        console.log('[AuthContext] No stored user found');
      }
      setLoading(false);
      console.log('[AuthContext] Authentication initialization complete');
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    console.log('[AuthContext] Login attempt for:', email);
    try {
      const response = await authAPI.login(email, password);
      
      if (response.success) {
        const { user: userData, access_token } = response.data;
        
        // Add avatar initials
        userData.avatar = userData.name.split(' ').map(n => n[0]).join('').toUpperCase();
        userData.token = access_token;
        
        // Store user with token
        localStorage.setItem('dms_user', JSON.stringify(userData));
        setUser(userData);
        
        console.log('[AuthContext] Login successful for:', email);
        return { success: true, user: userData };
      }
      
      console.warn('[AuthContext] Login failed: Invalid credentials');
      return { success: false, error: 'Invalid credentials' };
    } catch (error) {
      console.error('[AuthContext] Login error:', error);
      console.error('[AuthContext] Error details:', {
        message: error.message,
        stack: error.stack,
        email
      });
      return { success: false, error: error.message || 'Login failed' };
    }
  };

  const logout = async () => {
    console.log('[AuthContext] Logging out user:', user?.email);
    try {
      await authAPI.logout();
      console.log('[AuthContext] Logout API call successful');
    } catch (error) {
      console.error('[AuthContext] Logout error:', error);
      console.error('[AuthContext] Error details:', {
        message: error.message,
        stack: error.stack
      });
    } finally {
      setUser(null);
      localStorage.removeItem('dms_user');
      console.log('[AuthContext] User session cleared');
    }
  };

  const hasRole = (roles) => {
    if (!user) return false;
    if (Array.isArray(roles)) {
      return roles.includes(user.role);
    }
    return user.role === roles;
  };

  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, loading, hasRole, isAuthenticated }}>
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
