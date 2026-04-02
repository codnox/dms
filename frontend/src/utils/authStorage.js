const AUTH_USER_KEY = 'dms_user';

const hasWindow = () => typeof window !== 'undefined';

const parseUser = (raw) => {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (error) {
    console.error('[authStorage] Failed to parse stored user:', error);
    return null;
  }
};

export const getStoredUser = () => {
  if (!hasWindow()) return null;

  const sessionValue = sessionStorage.getItem(AUTH_USER_KEY);
  const sessionUser = parseUser(sessionValue);
  if (sessionUser) return sessionUser;

  // Backward-compatible migration from legacy localStorage token storage.
  const legacyValue = localStorage.getItem(AUTH_USER_KEY);
  const legacyUser = parseUser(legacyValue);
  if (legacyUser) {
    sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(legacyUser));
  }
  localStorage.removeItem(AUTH_USER_KEY);
  return legacyUser;
};

export const saveStoredUser = (user) => {
  if (!hasWindow()) return;
  sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  localStorage.removeItem(AUTH_USER_KEY);
};

export const clearStoredUser = () => {
  if (!hasWindow()) return;
  sessionStorage.removeItem(AUTH_USER_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
};

export const updateStoredUser = (updates) => {
  const current = getStoredUser() || {};
  const merged = { ...current, ...updates };
  saveStoredUser(merged);
  return merged;
};

export const getAuthToken = () => {
  const user = getStoredUser();
  return user?.token || null;
};
