# System Testing Checklist

## Prerequisites
- [ ] Backend is running on http://localhost:8000
- [ ] Frontend is running on http://localhost:5173
- [ ] Comprehensive data has been seeded
- [ ] MongoDB connection is active

## 1. Authentication & Authorization

### Login Tests
- [ ] Login as admin@dms.com / admin123
- [ ] Login as manager1@dms.com / manager123
- [ ] Login as distributor1@dms.com / dist123
- [ ] Login as subdist1@dms.com / subdist123
- [ ] Login as operator1@dms.com / oper123
- [ ] Invalid credentials show error
- [ ] Token persists after page refresh

### Permission Tests
- [ ] **Admin** can see all menu items
- [ ] **Manager** can see Approvals
- [ ] **Distributor** cannot see "Create Distribution"
- [ ] **Distributor** cannot see "Approvals"
- [ ] **Operator** has limited menu options
- [ ] Unauthorized page access redirects to /unauthorized

## 2. Dashboard

### Admin Dashboard
- [ ] Shows total users count
- [ ] Shows total devices count (should be ~200)
- [ ] Shows total distributions (should be ~50)
- [ ] Shows pending approvals count
- [ ] Recent activities displayed
- [ ] Charts/graphs render correctly

### Manager Dashboard
- [ ] Shows manager-specific metrics
- [ ] Shows pending items for approval
- [ ] Shows devices under management
- [ ] Recent activities displayed

### Distributor Dashboard
- [ ] Shows devices in inventory
- [ ] Shows distributions sent/received
- [ ] Shows current location devices
- [ ] No admin/manager only data visible

### Operator Dashboard
- [ ] Shows assigned devices
- [ ] Shows active distributions
- [ ] Shows defect reports count
- [ ] Basic metrics only

## 3. Devices Management

### Device List
- [ ] Shows ~200 devices after seeding
- [ ] Pagination works (navigate through pages)
- [ ] Search by device ID works
- [ ] Filter by type (ONU, ONT, Router, Modem)
- [ ] Filter by status (available, distributed, in_use, defective)
- [ ] Filter by manufacturer
- [ ] Table displays all columns correctly
- [ ] Mobile view shows card layout

### Device Details
- [ ] Click on device shows detail view
- [ ] All device information displayed
- [ ] Current holder information shown
- [ ] Location tracking visible
- [ ] Device history/timeline shown

### Device Registration (Admin/Manager)
- [ ] Can register new device
- [ ] Form validation works
- [ ] Serial number uniqueness enforced
- [ ] MAC address format validated
- [ ] Success notification shown

## 4. Distributions

### Distribution List
- [ ] Shows ~50 distributions after seeding
- [ ] Different statuses displayed (pending, approved, in_transit, delivered, rejected)
- [ ] Filter by status works
- [ ] Filter by date range works
- [ ] Search by distribution ID works
- [ ] Mobile responsive

### Create Distribution (Admin/Manager Only)
- [ ] Admin can access create distribution
- [ ] Manager can access create distribution
- [ ] Distributor CANNOT access (redirects to unauthorized)
- [ ] Can select devices from dropdown
- [ ] Can select recipient user
- [ ] Can add notes
- [ ] Form submission works
- [ ] Success notification shown

### Distribution Details
- [ ] Click distribution shows details
- [ ] Device list displayed
- [ ] From/To user info shown
- [ ] Status timeline visible
- [ ] Approval information shown (if approved)

## 5. Approvals (Admin/Manager Only)

### Approval Access
- [ ] Admin can access Approvals page
- [ ] Manager can access Approvals page
- [ ] Distributor CANNOT access (menu item not visible)
- [ ] Sub-distributor CANNOT access
- [ ] Operator CANNOT access

### Approval List
- [ ] Shows pending distributions
- [ ] Shows pending returns
- [ ] Filter by type (distribution/return)
- [ ] Shows requester information
- [ ] Shows requested date

### Approval Actions
- [ ] Can approve distribution
- [ ] Can reject distribution with reason
- [ ] Can approve return request
- [ ] Can reject return request
- [ ] Status updates immediately
- [ ] Notification sent to requester

## 6. Defect Reports

### Defect List
- [ ] Shows ~30 defect reports after seeding
- [ ] Filter by severity (low, medium, high, critical)
- [ ] Filter by status (open, in_progress, resolved, closed)
- [ ] Search by report ID or device
- [ ] Mobile responsive

### Create Defect Report
- [ ] Can select device from dropdown
- [ ] Can select defect type
- [ ] Can set severity level
- [ ] Can add description
- [ ] Can upload images (if implemented)
- [ ] Form submission works
- [ ] Notification sent to manager

### Defect Details
- [ ] Shows device information
- [ ] Shows reported by user
- [ ] Shows severity and type
- [ ] Shows description
- [ ] Shows status updates
- [ ] Shows assigned technician (if any)
- [ ] Shows resolution (if resolved)

## 7. Returns

### Return List
- [ ] Shows ~25 return requests after seeding
- [ ] Filter by status (pending, approved, rejected, completed)
- [ ] Filter by condition (good, fair, poor, defective)
- [ ] Search by return ID or device
- [ ] Mobile responsive

### Create Return Request
- [ ] Can select device to return
- [ ] Can select reason
- [ ] Can specify condition
- [ ] Can add notes
- [ ] Form submission works
- [ ] Goes to pending status
- [ ] Manager receives notification

### Return Details
- [ ] Shows device information
- [ ] Shows initiated by user
- [ ] Shows reason and condition
- [ ] Shows approval status
- [ ] Shows approved by (if approved)
- [ ] Shows approval date

## 8. Notifications

### Notification Display
- [ ] Click bell icon shows dropdown
- [ ] Shows latest 5 notifications
- [ ] Unread count badge shows correct number
- [ ] Each notification shows:
  - [ ] Title
  - [ ] Message
  - [ ] Timestamp (relative, e.g., "2 hours ago")
  - [ ] Type indicator (info, success, warning, error)

### Notification Actions
- [ ] Click notification marks as read
- [ ] Unread count decreases
- [ ] "Mark All as Read" works
- [ ] All notifications marked as read
- [ ] Unread count goes to 0

### Notification Content (Role-Specific)
- [ ] **Admin**: System-wide notifications
- [ ] **Manager**: Approval requests, assignments
- [ ] **Distributor**: Distribution updates
- [ ] **Operator**: Device assignments, defect updates
- [ ] No notifications from other users' activities

## 9. Settings & Theme

### Settings Page Access
- [ ] All users can access Settings
- [ ] Settings page loads without errors
- [ ] Current user preferences displayed

### Theme Management
- [ ] Current theme highlighted (Light/Dark/System)
- [ ] Click "Light" applies light theme immediately
- [ ] Click "Dark" applies dark theme immediately
- [ ] Click "System" follows system preference
- [ ] Document root class changes (add/remove 'dark')
- [ ] Background colors change
- [ ] Text colors change
- [ ] Component colors adapt

### Compact Mode
- [ ] Toggle Compact Mode on
- [ ] UI becomes denser (smaller fonts, less padding)
- [ ] Document root gets 'compact' class
- [ ] Toggle off returns to normal
- [ ] Class removed from document

### Notification Preferences
- [ ] Email notifications toggle works
- [ ] Push notifications toggle works
- [ ] State updates immediately

### Save Settings
- [ ] Click "Save Changes" button
- [ ] Loading state shows ("Saving...")
- [ ] Success notification appears
- [ ] Button returns to normal ("Save Changes")

### Settings Persistence
- [ ] Refresh page
- [ ] Theme persists (still dark if dark was saved)
- [ ] Compact mode persists
- [ ] Notification preferences persist
- [ ] Login with different user
- [ ] Different user has independent settings
- [ ] Switch back to first user
- [ ] Original settings still there

## 10. User Management (Admin Only)

### User List
- [ ] Shows ~39 users after seeding
- [ ] Filter by role works
- [ ] Filter by status (active/inactive)
- [ ] Search by name or email
- [ ] Shows all user information

### Create User (Admin Only)
- [ ] Admin sees "Add User" button
- [ ] Manager does NOT see "Add User" button
- [ ] Can create user with all fields
- [ ] Email uniqueness validated
- [ ] Password strength enforced
- [ ] Success notification shown

### Edit User
- [ ] Admin can edit any user
- [ ] Manager can edit limited fields
- [ ] User can edit own profile
- [ ] Cannot edit email (or validation required)
- [ ] Status change works (active/inactive)

## 11. Reports (If Implemented)

### Report Generation
- [ ] Can select report type
- [ ] Can select date range
- [ ] Can filter by location/user/device
- [ ] Report generates successfully
- [ ] Data displayed correctly

### Export Functionality
- [ ] Export to PDF works
- [ ] Export to CSV works
- [ ] Export to Excel works
- [ ] Downloaded file contains correct data

## 12. Mobile Responsiveness

### Mobile Navigation
- [ ] Hamburger menu icon visible on mobile
- [ ] Sidebar slides in/out smoothly
- [ ] Close button works
- [ ] Overlay closes sidebar when clicked

### Mobile Tables
- [ ] Device list shows cards on mobile
- [ ] Distribution list shows cards
- [ ] Defect list shows cards
- [ ] Cards display all important info
- [ ] Cards are touchable and responsive

### Mobile Forms
- [ ] Form fields are large enough to tap (44px)
- [ ] Dropdowns work on mobile
- [ ] Date pickers work on mobile
- [ ] Text areas expand properly
- [ ] Submit buttons are accessible

### Mobile Modals
- [ ] Modals are fullscreen or near-fullscreen
- [ ] Close button is easy to reach
- [ ] Content scrolls if needed
- [ ] Forms in modals work correctly

## 13. Performance & UX

### Load Times
- [ ] Dashboard loads in < 2 seconds
- [ ] Device list loads in < 3 seconds
- [ ] Notifications load quickly
- [ ] No excessive API calls

### Loading States
- [ ] Loading spinners show during data fetch
- [ ] Skeleton screens (if implemented)
- [ ] Disabled buttons during submission
- [ ] No content flash before loading

### Error Handling
- [ ] Invalid API calls show error messages
- [ ] Network errors handled gracefully
- [ ] Form validation errors clear
- [ ] 404 page for invalid routes
- [ ] Unauthorized page for forbidden access

### Notifications & Feedback
- [ ] Success toasts appear and disappear
- [ ] Error toasts stay longer or require dismissal
- [ ] Form submission feedback immediate
- [ ] Loading states clear

## 14. Data Integrity

### Seeded Data Verification
- [ ] Exactly 39 users created
- [ ] Exactly 200 devices created
- [ ] Exactly 50 distributions created
- [ ] Exactly 30 defects created
- [ ] Exactly 25 returns created
- [ ] ~300+ notifications created (5-10 per user)

### Relationships
- [ ] Devices show correct current holder
- [ ] Distributions link to correct users
- [ ] Defects link to correct devices
- [ ] Returns link to correct devices
- [ ] Notifications belong to correct users

### Status Consistency
- [ ] Device status matches distribution status
- [ ] Approved distributions show approval info
- [ ] Rejected items show rejection reason
- [ ] Completed returns marked as completed

## 15. Security

### Authentication
- [ ] Cannot access protected routes without login
- [ ] Token expiration handled
- [ ] Logout clears session
- [ ] Login required message shown

### Authorization
- [ ] Role-based menus enforced
- [ ] API calls validate permissions
- [ ] Direct URL access blocked for unauthorized pages
- [ ] Error messages don't reveal sensitive info

### Data Protection
- [ ] Passwords not visible in API responses
- [ ] User can only see their own notifications
- [ ] User can only edit allowed fields
- [ ] Admin restrictions enforced

## Test Results Summary

**Date:** _________________

**Tester:** _________________

**Total Tests:** 300+

**Passed:** _______

**Failed:** _______

**Blocked:** _______

**Notes:**
_______________________________________________________________________________
_______________________________________________________________________________
_______________________________________________________________________________

---

## Critical Issues Found

| Issue # | Description | Severity | Status |
|---------|-------------|----------|--------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

## Sign-off

- [ ] All critical tests passed
- [ ] All blocker issues resolved
- [ ] System ready for demo/deployment

**Approved by:** _________________

**Date:** _________________
