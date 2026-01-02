# Quick Start Guide - Distribution Management System

## 🚀 Starting the Application

### Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```
Backend runs on: http://localhost:8000

### Frontend
```bash
cd frontend
npm run dev
```
Frontend runs on: http://localhost:5173

### OR Use PowerShell Scripts (from root directory)
```powershell
# Start both backend and frontend
.\start.ps1

# Stop both services
.\stop.ps1
```

## 📊 Seed Comprehensive Data

### Method 1: Using PowerShell
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/seed-comprehensive" -Method Post
```

### Method 2: Using curl
```bash
curl -X POST http://localhost:8000/seed-comprehensive
```

### Method 3: Using Swagger UI
1. Navigate to http://localhost:8000/docs
2. Find `/seed-comprehensive` endpoint
3. Click "Try it out"
4. Click "Execute"

## 🔐 Test User Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@dms.com | admin123 |
| Manager 1 | manager1@dms.com | manager123 |
| Manager 2 | manager2@dms.com | manager123 |
| Manager 3 | manager3@dms.com | manager123 |
| Distributor 1 | distributor1@dms.com | dist123 |
| Distributor 2-5 | distributor2-5@dms.com | dist123 |
| Sub-Distributor 1-10 | subdist1-10@dms.com | subdist123 |
| Operator 1-20 | operator1-20@dms.com | oper123 |

## 🎨 Testing Theme & Settings

1. Login with any user
2. Navigate to **Settings** page
3. Try changing:
   - **Theme**: Light / Dark / System
   - **Compact Mode**: ON / OFF
   - **Email Notifications**: ON / OFF
   - **Push Notifications**: ON / OFF
4. Click **Save Changes**
5. Refresh the page to see persistence
6. Login with a different user to see independent settings

## 🔔 Testing Notifications

1. Login with any user
2. Click the **bell icon** in the top navbar
3. View latest 5 notifications for that user
4. Click a notification to mark it as read
5. Click **Mark All as Read** to clear all
6. Try different users to see role-specific notifications:
   - **Admin**: System-wide notifications
   - **Manager**: Approval requests, defect assignments
   - **Distributor**: Distribution updates, device assignments
   - **Operator**: Device assignments, defect updates

## 📱 Testing Mobile Responsiveness

1. Open browser DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Select device: iPhone, iPad, or custom size
4. Test navigation, tables, forms, modals
5. Tables should switch to card view on mobile
6. All touch targets should be at least 44px

## 🧪 Testing Permission Changes

### Distribution Creation (Admin/Manager Only)
1. Login as **distributor1@dms.com**
2. Should NOT see "Create Distribution" in sidebar
3. Navigating to /distributions/create should show "Unauthorized"
4. Login as **manager1@dms.com**
5. SHOULD see "Create Distribution" option
6. Can successfully create distributions

### Device Approval (Admin/Manager Only)
1. Login as **distributor1@dms.com**
2. Should NOT see "Approvals" in sidebar
3. Login as **manager1@dms.com**
4. SHOULD see "Approvals" in sidebar
5. Can approve/reject pending items

### User Management (Admin Only)
1. Login as **manager1@dms.com**
2. Navigate to Users page
3. Should NOT see "Add User" button
4. Login as **admin@dms.com**
5. SHOULD see "Add User" button
6. Can create users of any role

## 📊 Data Overview (After Seeding)

- **39 Users**: 1 Admin, 3 Managers, 5 Distributors, 10 Sub-Distributors, 20 Operators
- **200 Devices**: Various types (ONU, ONT, Router, Modem) from multiple manufacturers
- **50 Distributions**: Across the user hierarchy with different statuses
- **30 Defect Reports**: With varying severity and status
- **25 Return Requests**: In different stages of approval
- **300+ Notifications**: 5-10 per user, role-specific

## 🔧 Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is already in use
netstat -ano | findstr :8000

# Install dependencies
cd backend
pip install -r requirements.txt
```

### Frontend won't start
```bash
# Check if port 5173 is already in use
netstat -ano | findstr :5173

# Install dependencies
cd frontend
npm install
```

### Database connection error
- Verify MongoDB connection string in `backend/app/config.py`
- Ensure MongoDB Atlas cluster is running
- Check network connectivity

### No data showing after seeding
- Verify seed endpoint returned success
- Check backend console for errors
- Try seeding again (will skip if data exists)
- To re-seed: clear the database first

### Notifications not loading
- Check browser console for errors
- Verify backend API is running
- Check authentication token is valid
- Try logging out and logging back in

### Theme not persisting
- Check if "Save Changes" was clicked
- Verify backend API call succeeded (check Network tab)
- Clear browser cache and try again

## 🌟 Key Features to Demonstrate

1. **Role-Based Access Control**: Different menus and permissions per role
2. **Theme System**: Light/Dark mode with persistence
3. **Compact Mode**: Denser UI layout option
4. **Mobile Responsive**: Tables become cards, touch-friendly
5. **Real-time Notifications**: Latest 5 updates per user
6. **Comprehensive Dashboard**: Role-specific metrics and charts
7. **Device Tracking**: Full lifecycle from purchase to distribution
8. **Approval Workflow**: Multi-level approvals for distributions and returns
9. **Defect Management**: Report, track, and resolve device issues
10. **User Management**: Admin controls for user accounts

## 📖 Additional Resources

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc (Alternative API docs)
- **Full Summary**: See `COMPREHENSIVE_UPDATE_SUMMARY.md`
- **Integration Guide**: See `INTEGRATION_COMPLETE.md`

## 🎯 Quick Test Checklist

- [ ] Start backend and frontend
- [ ] Seed comprehensive data
- [ ] Login as admin
- [ ] Check dashboard statistics
- [ ] View devices list (200 devices)
- [ ] View distributions (50 distributions)
- [ ] Check notifications (5-10 for admin)
- [ ] Change theme to dark mode
- [ ] Enable compact mode
- [ ] Save settings
- [ ] Refresh page (settings persist)
- [ ] Login as manager
- [ ] Approve a pending distribution
- [ ] Login as operator
- [ ] View assigned devices
- [ ] Create a defect report
- [ ] Test on mobile device size

## 💡 Tips

- Use **admin@dms.com** for full system access
- Use **manager1@dms.com** to test approval workflows
- Use **distributor1@dms.com** to test distribution receiving
- Use **operator1@dms.com** to test field operations
- Check notifications regularly for activity updates
- Use dark mode to reduce eye strain
- Enable compact mode on smaller screens for more content
- All test passwords are simple for easy testing (not for production!)

---

**Need Help?** Check the console logs (F12) for detailed error messages.
