# Logging and Error Handling Guide

## Overview
This document describes the comprehensive logging and error handling implemented across the Distribution Management System.

## Recent Fixes

### 1. ✅ NotificationContext API Error (FIXED)
**Error**: `TypeError: api.get is not a function`

**Root Cause**: NotificationContext was importing the default `api` object but trying to call methods like `api.get()` which don't exist. The api.js exports specific API modules (authAPI, devicesAPI, etc.) not generic HTTP methods.

**Solution**: 
- Changed import from `import api from '../services/api'` to `import { notificationsAPI } from '../services/api'`
- Updated all API calls to use the proper API module methods:
  - `api.get('/notifications/latest?limit=5')` → `notificationsAPI.getLatestNotifications(5)`
  - `api.patch('/notifications/${id}/read')` → `notificationsAPI.markAsRead(id)`
  - `api.patch('/notifications/read-all')` → `notificationsAPI.markAllAsRead()`
  - `api.delete('/notifications/${id}')` → `notificationsAPI.deleteNotification(id)`

### 2. ✅ Barcode Scanner Error (FIXED)
**Error**: `NotFoundException: No MultiFormat Readers were able to detect the code`

**Root Cause**: The html5-qrcode library continuously fires error callbacks while scanning when no code is detected. These are expected during normal operation but were being logged as errors.

**Solution**:
- Added error filtering in `onScanError` to suppress common/expected scanning errors
- Only logs critical errors that don't include "NotFoundException" or "No MultiFormat Readers"
- Added better parsing logic to handle various barcode formats
- If no patterns match, uses the entire scanned text as serial number
- Added try-catch in scan success handler with user-friendly warnings
- Set `verbose: false` in scanner config to suppress library's internal logging

### 3. ✅ Comprehensive Logging Added
Added detailed logging to all critical components with consistent prefixes:

#### Logging Format
All logs follow the format: `[ComponentName] Action description`

Example:
```javascript
console.log('[authAPI] Login attempt for:', email);
console.error('[devicesAPI] Failed to create device:', error.message);
```

## Logging Coverage

### API Service (`frontend/src/services/api.js`)

#### apiRequest Helper
- Logs every API request with method, endpoint, and auth status
- Logs response status and success/failure
- Logs full error details including stack traces

#### Auth API (`authAPI`)
- ✅ `login()` - Logs attempts, success, and failures with email
- ✅ `logout()` - Logs logout attempts and completion
- ✅ `getCurrentUser()` - Logs user fetch attempts
- ✅ `changePassword()` - Logs password change attempts

#### Devices API (`devicesAPI`)
- ✅ `getDevices()` - Logs params and result count
- ✅ `createDevice()` - Logs device data and creation result
- ✅ `trackDeviceBySerial()` - Logs serial number tracking

#### Notifications API (`notificationsAPI`)
- ✅ `getNotifications()` - Logs query params
- ✅ `getUnreadCount()` - Logs count result
- ✅ `getLatestNotifications()` - Logs limit and result count
- ✅ `markAsRead()` - Logs notification ID
- ✅ `markAllAsRead()` - Logs mass read operation
- ✅ `deleteNotification()` - Logs deletion attempts

### Context Providers

#### AuthContext (`frontend/src/context/AuthContext.jsx`)
- ✅ Initialization - Logs stored user validation
- ✅ `login()` - Logs attempts, success, errors with details
- ✅ `logout()` - Logs user email and session clearing
- ✅ Token validation - Logs validation success/failure

#### NotificationContext (`frontend/src/context/NotificationContext.jsx`)
- ✅ `fetchLatestNotifications()` - Logs fetching and result count
- ✅ `markAsRead()` - Logs notification ID and success
- ✅ `markAllAsRead()` - Logs mass operation
- ✅ `removeNotification()` - Logs deletion with ID

### Components

#### Navbar (`frontend/src/components/layout/Navbar.jsx`)
- ✅ Notification fetching - Logs when user logs in
- ✅ `handleLogout()` - Logs logout action
- ✅ `handleSearch()` - Logs search query
- ✅ `handleNotificationClick()` - Logs clicked notification ID
- ✅ `handleMarkAllAsRead()` - Logs mass read action

#### RegisterDevice (`frontend/src/pages/RegisterDevice.jsx`)
- ✅ Scanner initialization - Logs setup and errors
- ✅ `onScanSuccess()` - Logs scanned data and extracted fields
- ✅ `onScanError()` - Filters and logs only critical errors
- ✅ `openCameraScanner()` - Logs scanner opening
- ✅ `closeCameraScanner()` - Logs cleanup with error handling
- ✅ `handleChange()` - Logs form field changes
- ✅ `handleSubmit()` - Logs submission with full device data

## Exception Handling

### All API Functions
Every API function now follows this pattern:
```javascript
methodName: async (params) => {
  console.log('[apiName] Action description', params);
  try {
    const response = await apiRequest(...);
    console.log('[apiName] Success message');
    return response;
  } catch (error) {
    console.error('[apiName] Error description:', error.message);
    throw error;
  }
}
```

### Component Functions
All component functions with side effects have try-catch blocks:
```javascript
const handleAction = async () => {
  console.log('[Component] Starting action');
  try {
    await performAction();
    console.log('[Component] Action successful');
  } catch (error) {
    console.error('[Component] Action failed:', error);
    console.error('[Component] Error details:', {
      message: error.message,
      stack: error.stack
    });
  }
};
```

## Debugging Tips

### How to Debug API Issues

1. **Open Browser Console** (F12)
2. **Filter logs** by component:
   - Type `[authAPI]` to see authentication logs
   - Type `[devicesAPI]` to see device operation logs
   - Type `[notificationsAPI]` to see notification logs

3. **Check the sequence**:
   ```
   [API] Making request: { method: 'GET', endpoint: '/notifications/latest?limit=5' }
   [notificationsAPI] Getting latest notifications, limit: 5
   [API] Response received: { status: 200, ok: true }
   [notificationsAPI] Successfully fetched 5 notifications
   [NotificationContext] Successfully loaded 5 notifications
   ```

4. **Look for error details**:
   ```
   [authAPI] Login failed: Invalid credentials
   [API] Request error: { endpoint: '/auth/login', error: 'Invalid credentials' }
   ```

### How to Debug Scanner Issues

1. **Scanner won't start**:
   ```
   Look for: [RegisterDevice] Failed to initialize scanner
   Check: Camera permissions in browser
   ```

2. **Scanner not detecting codes**:
   ```
   Expected: (no logs - errors are suppressed)
   If seeing: NotFoundException errors in UI - check html5-qrcode version
   ```

3. **Scanner detected but parsing failed**:
   ```
   [RegisterDevice] Barcode/QR scan successful
   [RegisterDevice] Scanned text: ABC123XYZ
   [RegisterDevice] No patterns matched, using text as serial number
   ```

### Common Error Patterns

#### API Token Issues
```
[API] Request failed: { status: 401, error: 'Invalid token' }
[AuthContext] Token validation failed, clearing storage
```
**Solution**: Re-login to get fresh token

#### Network Issues
```
[API] Request error: { error: 'Failed to fetch' }
```
**Solution**: Check backend is running, verify API URL in .env

#### Permission Issues
```
[authAPI] Login successful
[devicesAPI] Failed to create device: Permission denied
```
**Solution**: Check user role has required permissions

## Error Logging Structure

### Log Levels

1. **`console.log()`** - Normal operations, success messages
   ```javascript
   console.log('[Component] Action completed successfully');
   ```

2. **`console.warn()`** - Non-critical issues, degraded functionality
   ```javascript
   console.warn('[Component] Feature unavailable, using fallback');
   ```

3. **`console.error()`** - Errors that prevent operation
   ```javascript
   console.error('[Component] Operation failed:', error.message);
   console.error('[Component] Error details:', { message, stack });
   ```

### Error Context

Always log error context to aid debugging:
```javascript
catch (error) {
  console.error('[Component] Operation failed:', error.message);
  console.error('[Component] Error details:', {
    message: error.message,
    stack: error.stack,
    userId: user?.id,
    timestamp: new Date().toISOString()
  });
}
```

## Future Enhancements

### Recommended Additions

1. **Centralized Logger Service**
   ```javascript
   // services/logger.js
   export const logger = {
     info: (component, message, data) => {...},
     warn: (component, message, data) => {...},
     error: (component, message, error, data) => {...}
   };
   ```

2. **Error Reporting Service**
   - Integrate with Sentry, LogRocket, or similar
   - Automatically capture and report errors
   - Include user context and breadcrumbs

3. **Performance Logging**
   - Log API response times
   - Log component render times
   - Identify performance bottlenecks

4. **Log Levels by Environment**
   ```javascript
   const isDevelopment = import.meta.env.DEV;
   if (isDevelopment) {
     console.log('[Verbose] Detailed debug info');
   }
   ```

5. **Structured Logging**
   ```javascript
   logger.log({
     level: 'info',
     component: 'authAPI',
     action: 'login',
     user: email,
     timestamp: Date.now(),
     success: true
   });
   ```

## Testing the Fixes

### Test Notifications
1. Open Console (F12)
2. Login to the application
3. Look for logs:
   ```
   [authAPI] Login successful
   [Navbar] User logged in, fetching notifications
   [notificationsAPI] Getting latest notifications, limit: 5
   [NotificationContext] Successfully loaded X notifications
   ```

### Test Barcode Scanner
1. Open Console (F12)
2. Go to Register Device page
3. Click "Scan" button
4. Point camera at code:
   ```
   [RegisterDevice] Opening camera scanner
   [RegisterDevice] Initializing camera scanner
   [RegisterDevice] Camera scanner initialized successfully
   [RegisterDevice] Barcode/QR scan successful
   [RegisterDevice] Scanned text: ABC123
   [RegisterDevice] Extracted serial number: ABC123
   ```

### Test Error Handling
1. Turn off backend
2. Try to login:
   ```
   [authAPI] Login attempt for: user@example.com
   [API] Request error: { error: 'Failed to fetch' }
   [authAPI] Login failed: Failed to fetch
   ```

## Summary

✅ **Fixed Issues**:
- NotificationContext API calls now use correct API modules
- Barcode scanner errors properly suppressed
- All major components have comprehensive logging
- All API calls have exception handling

✅ **Enhanced**:
- Consistent logging format across codebase
- Detailed error context for debugging
- User-friendly error messages
- Non-intrusive error handling

✅ **Best Practices**:
- Log actions before they happen
- Log results after completion
- Log errors with full context
- Use component prefixes for filtering
- Don't log sensitive data (passwords, tokens)

---

**For Support**: Check console logs with component filters to identify issues quickly!
