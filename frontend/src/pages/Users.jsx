import { useState, useEffect } from 'react';
import DataTable from '../components/ui/DataTable';
import Card from '../components/ui/Card';
import Modal from '../components/ui/Modal';
import Button from '../components/ui/Button';
import StatusBadge from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { usersAPI, adminUpdateCredentials } from '../services/api';
import { 
  UserPlus, Edit, Trash2, Eye, Shield, Mail, Phone, 
  Building, MapPin, Calendar, Users as UsersIcon, Loader2, Lock
} from 'lucide-react';

// Roles each creator can assign
const ALLOWED_ROLES_BY_CREATOR = {
  admin:           ['admin', 'manager', 'staff', 'sub_distributor', 'cluster', 'operator'],
  manager:         ['staff', 'sub_distributor', 'cluster', 'operator'],
  sub_distributor: ['cluster'],
  cluster:         ['operator'],
};

const ROLE_LABELS = {
  admin: 'Admin',
  manager: 'Manager',
  staff: 'Staff',
  sub_distributor: 'Sub Distributor',
  cluster: 'Cluster',
  operator: 'Operator',
};

const getRoleColor = (role) => {
  switch (role) {
    case 'admin':           return 'bg-red-100 text-red-800';
    case 'manager':         return 'bg-purple-100 text-purple-800';
    case 'staff':           return 'bg-blue-100 text-blue-800';
    case 'sub_distributor': return 'bg-indigo-100 text-indigo-800';
    case 'cluster':         return 'bg-teal-100 text-teal-800';
    case 'operator':        return 'bg-green-100 text-green-800';
    default:                return 'bg-gray-100 text-gray-800';
  }
};

const emptyForm = {
  name: '',
  email: '',
  password: '',
  role: 'operator',
  phone: '',
  department: '',
  location: '',
};

const Users = () => {
  const { user: currentUser, hasRole } = useAuth();
  const { showToast } = useNotifications();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const [selectedUser, setSelectedUser] = useState(null);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [detailUser, setDetailUser] = useState(null);
  const [detailForm, setDetailForm] = useState({});
  const [newPassword, setNewPassword] = useState('');
  const [savingDetail, setSavingDetail] = useState(false);

  const [formData, setFormData] = useState(emptyForm);

  // Which roles the current user can create
  const creatableRoles = ALLOWED_ROLES_BY_CREATOR[currentUser?.role] || [];
  const canCreateUsers = creatableRoles.length > 0;

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await usersAPI.getUsers();
      setUsers(response.data || []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      showToast('Failed to load users', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // When add modal opens, default role to first available
  const openAddModal = () => {
    setFormData({ ...emptyForm, role: creatableRoles[0] || 'operator' });
    setShowAddModal(true);
  };

  const columns = [
    {
      key: 'name',
      label: 'User',
      render: (value, row) => (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
            <span className="font-medium text-gray-600">
              {value.split(' ').map(n => n[0]).join('')}
            </span>
          </div>
          <div>
            <p className="font-medium text-gray-800">{value}</p>
            <p className="text-sm text-gray-500">{row.email}</p>
          </div>
        </div>
      )
    },
    {
      key: 'role',
      label: 'Role',
      render: (value) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${getRoleColor(value)}`}>
          {ROLE_LABELS[value] || value}
        </span>
      )
    },
    {
      key: 'status',
      label: 'Status',
      render: (value) => <StatusBadge status={value} />
    },
    {
      key: 'phone',
      label: 'Phone',
      render: (value) => value || '-'
    },
    {
      key: 'created_at',
      label: 'Joined',
      render: (value) => value ? new Date(value).toLocaleDateString() : '-'
    },
    {
      key: 'actions',
      label: 'Actions',
      sortable: false,
      render: (_, row) => (
        <div className="flex gap-2">
          <button
            onClick={() => { setSelectedUser(row); setShowViewModal(true); }}
            className="p-1 hover:bg-gray-100 rounded"
            title="View"
          >
            <Eye className="w-4 h-4 text-gray-500" />
          </button>
          {currentUser?.role === 'admin' && (
            <button
              onClick={() => { setDetailUser(row); setDetailForm({ ...row }); setNewPassword(''); }}
              className="p-1.5 rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200"
              title="View/Edit Details"
            >
              <Lock className="w-4 h-4" />
            </button>
          )}
          {hasRole(['admin', 'manager']) && (
            <>
              <button
                onClick={() => {
                  setSelectedUser(row);
                  setFormData({
                    name: row.name,
                    email: row.email,
                    password: '',
                    role: row.role,
                    phone: row.phone || '',
                    department: row.department || '',
                    location: row.location || '',
                  });
                  setShowEditModal(true);
                }}
                className="p-1 hover:bg-gray-100 rounded"
                title="Edit"
              >
                <Edit className="w-4 h-4 text-blue-500" />
              </button>
              {row.id !== currentUser.id && (
                <button
                  onClick={() => { setSelectedUser(row); setShowDeleteModal(true); }}
                  className="p-1 hover:bg-gray-100 rounded"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4 text-red-500" />
                </button>
              )}
            </>
          )}
        </div>
      )
    }
  ];

  const handleAddUser = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        name: formData.name,
        email: formData.email,
        password: formData.password,
        role: formData.role,
      };
      if (formData.phone)      payload.phone = formData.phone;
      if (formData.department) payload.department = formData.department;
      if (formData.location)   payload.location = formData.location;

      await usersAPI.createUser(payload);
      showToast('User created successfully', 'success');
      setShowAddModal(false);
      setFormData(emptyForm);
      fetchUsers();
    } catch (error) {
      showToast(error.message || 'Failed to create user', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditUser = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {};
      if (formData.name)       payload.name = formData.name;
      if (formData.phone)      payload.phone = formData.phone;
      if (formData.department) payload.department = formData.department;
      if (formData.location)   payload.location = formData.location;

      await usersAPI.updateUser(selectedUser._id || selectedUser.id, payload);
      showToast('User updated successfully', 'success');
      setShowEditModal(false);
      fetchUsers();
    } catch (error) {
      showToast(error.message || 'Failed to update user', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteUser = async () => {
    try {
      await usersAPI.deleteUser(selectedUser._id || selectedUser.id);
      showToast('User deleted successfully', 'success');
      setShowDeleteModal(false);
      setSelectedUser(null);
      fetchUsers();
    } catch (error) {
      showToast(error.message || 'Failed to delete user', 'error');
    }
  };

  const stats = [
    { label: 'Total Users',     value: users.length,                                                        icon: UsersIcon, color: 'blue' },
    { label: 'Administrators',  value: users.filter(u => u.role === 'admin').length,                        icon: Shield,    color: 'red' },
    { label: 'Distributors',    value: users.filter(u => ['sub_distributor','cluster'].includes(u.role)).length, icon: Building, color: 'indigo' },
    { label: 'Operators',       value: users.filter(u => u.role === 'operator').length,                     icon: UsersIcon, color: 'green' }
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">User Management</h1>
          <p className="text-gray-500 mt-1">Manage system users and their permissions</p>
        </div>
        {canCreateUsers && (
          <Button icon={UserPlus} onClick={openAddModal}>
            Add User
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <Card key={index} className="text-center">
            <div className={`inline-flex p-3 rounded-lg bg-${stat.color}-100 mb-2`}>
              <stat.icon className={`w-6 h-6 text-${stat.color}-600`} />
            </div>
            <p className="text-2xl font-bold text-gray-800">{stat.value}</p>
            <p className="text-sm text-gray-500">{stat.label}</p>
          </Card>
        ))}
      </div>

      {/* Users Table */}
      <Card>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            <span className="ml-3 text-gray-500">Loading users...</span>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={users}
            searchable
            searchPlaceholder="Search users..."
          />
        )}
      </Card>

      {/* View Modal */}
      <Modal
        isOpen={showViewModal}
        onClose={() => { setShowViewModal(false); setSelectedUser(null); }}
        title="User Details"
        size="md"
      >
        {selectedUser && (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center">
                <span className="text-xl font-medium text-gray-600">
                  {selectedUser.name.split(' ').map(n => n[0]).join('')}
                </span>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">{selectedUser.name}</h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${getRoleColor(selectedUser.role)}`}>
                  {ROLE_LABELS[selectedUser.role] || selectedUser.role}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Email</p>
                  <p className="font-medium text-gray-800">{selectedUser.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Phone className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Phone</p>
                  <p className="font-medium text-gray-800">{selectedUser.phone || 'Not provided'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Building className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Department</p>
                  <p className="font-medium text-gray-800">{selectedUser.department || 'Not assigned'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <MapPin className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Location</p>
                  <p className="font-medium text-gray-800">{selectedUser.location || 'Not assigned'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Joined</p>
                  <p className="font-medium text-gray-800">{selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleDateString() : 'Unknown'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <StatusBadge status={selectedUser.status} />
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Add User Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => { setShowAddModal(false); setFormData(emptyForm); }}
        title="Add New User"
        size="md"
      >
        <form onSubmit={handleAddUser} className="space-y-4">
          {/* Required fields */}
          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter full name"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="user@example.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <span className="flex items-center gap-1"><Lock className="w-3.5 h-3.5" /> Password <span className="text-red-500">*</span></span>
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Min. 6 characters"
                minLength={6}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Role <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              >
                {creatableRoles.map(r => (
                  <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Optional fields */}
          <p className="text-xs text-gray-400 pt-1">Optional — user can fill these in later</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="+880..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., IT"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., Dhaka"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => { setShowAddModal(false); setFormData(emptyForm); }}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Creating...' : 'Create User'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Edit User Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => { setShowEditModal(false); setSelectedUser(null); }}
        title="Edit User"
        size="md"
      >
        <form onSubmit={handleEditUser} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => { setShowEditModal(false); setSelectedUser(null); }}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => { setShowDeleteModal(false); setSelectedUser(null); }}
        title="Delete User"
        size="sm"
      >
        <div className="text-center py-4">
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Trash2 className="w-6 h-6 text-red-600" />
          </div>
          <p className="text-gray-700 mb-4">
            Are you sure you want to delete <strong>{selectedUser?.name}</strong>?
            This action cannot be undone.
          </p>
          <div className="flex justify-center gap-3">
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDeleteUser}>
              Delete User
            </Button>
          </div>
        </div>
      </Modal>

      {/* Admin User Detail Modal */}
      {detailUser && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-800">User Details</h2>
                <p className="text-sm text-gray-500">{detailUser.email}</p>
              </div>
              <button onClick={() => setDetailUser(null)} className="p-2 hover:bg-gray-100 rounded-lg">✕</button>
            </div>
            <div className="p-6 space-y-4">
              {/* Status toggle */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-800">Account Status</p>
                  <p className={`text-sm ${detailForm.status === 'active' ? 'text-green-600' : 'text-red-600'}`}>
                    {detailForm.status === 'active' ? 'Active' : 'Inactive'}
                  </p>
                </div>
                <button
                  onClick={async () => {
                    const newStatus = detailForm.status === 'active' ? 'inactive' : 'active';
                    try {
                      await usersAPI.updateUserStatus(detailUser.id, newStatus);
                      setDetailForm(p => ({ ...p, status: newStatus }));
                      showToast(`User ${newStatus === 'active' ? 'activated' : 'deactivated'}`, 'success');
                      fetchUsers();
                    } catch (err) {
                      showToast(err.message || 'Failed to update status', 'error');
                    }
                  }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    detailForm.status === 'active'
                      ? 'bg-red-100 text-red-700 hover:bg-red-200'
                      : 'bg-green-100 text-green-700 hover:bg-green-200'
                  }`}
                >
                  {detailForm.status === 'active' ? 'Deactivate' : 'Activate'}
                </button>
              </div>

              {/* Basic info fields */}
              {[
                { key: 'name', label: 'Full Name' },
                { key: 'email', label: 'Email' },
                { key: 'phone', label: 'Phone' },
                { key: 'department', label: 'Department' },
                { key: 'location', label: 'Location' },
              ].map(({ key, label }) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                  <input
                    value={detailForm[key] || ''}
                    onChange={e => setDetailForm(p => ({ ...p, [key]: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
              <div className="text-sm text-gray-500">
                <span className="font-medium">Role:</span> {detailUser.role} &nbsp;|&nbsp;
                <span className="font-medium">Created:</span> {new Date(detailUser.created_at).toLocaleDateString()}
              </div>

              <Button
                disabled={savingDetail}
                onClick={async () => {
                  setSavingDetail(true);
                  try {
                    // Update basic fields
                    await usersAPI.updateUser(detailUser.id, {
                      name: detailForm.name,
                      phone: detailForm.phone,
                      department: detailForm.department,
                      location: detailForm.location,
                    });
                    // Update email separately if changed
                    if (detailForm.email && detailForm.email !== detailUser.email) {
                      await adminUpdateCredentials(detailUser.id, { email: detailForm.email });
                    }
                    showToast('User details saved', 'success');
                    fetchUsers();
                  } catch (err) {
                    showToast(err.message || 'Failed to save', 'error');
                  } finally {
                    setSavingDetail(false);
                  }
                }}
              >
                {savingDetail ? 'Saving...' : 'Save Details'}
              </Button>

              {/* Password reset */}
              <div className="border-t pt-4 mt-4">
                <p className="font-medium text-gray-800 mb-3 flex items-center gap-2">
                  <Lock className="w-4 h-4" /> Reset Password
                </p>
                <input
                  type="password"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  placeholder="Enter new password (min 6 chars)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 mb-3"
                />
                <Button
                  variant="outline"
                  onClick={async () => {
                    if (!newPassword || newPassword.length < 6) {
                      showToast('Password must be at least 6 characters', 'error');
                      return;
                    }
                    try {
                      await adminUpdateCredentials(detailUser.id, { password: newPassword });
                      showToast('Password reset successfully', 'success');
                      setNewPassword('');
                    } catch (err) {
                      showToast(err.message || 'Failed to reset password', 'error');
                    }
                  }}
                >
                  Reset Password
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Users;
