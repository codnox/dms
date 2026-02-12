import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import StatusBadge from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { devicesAPI, usersAPI, distributionsAPI } from '../services/api';
import { Truck, Save, X, Plus, Trash2, Search, ShieldAlert, Loader2 } from 'lucide-react';

const CreateDistribution = () => {
  const { user, hasRole } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useNotifications();
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDevices, setSelectedDevices] = useState([]);
  const [availableDevices, setAvailableDevices] = useState([]);
  const [recipients, setRecipients] = useState([]);
  const [loadingData, setLoadingData] = useState(true);
  const [formData, setFormData] = useState({
    toDistributor: '',
    notes: ''
  });

  // Only admin and manager can create distributions
  const canCreateDistribution = hasRole(['admin', 'manager']);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoadingData(true);
        const [devicesRes, usersRes] = await Promise.all([
          devicesAPI.getAvailableDevices().catch(() => ({ data: [] })),
          usersAPI.getUsers().catch(() => ({ data: [] }))
        ]);
        setAvailableDevices(devicesRes.data || []);
        const allUsers = usersRes.data || [];
        setRecipients(allUsers.filter(u => 
          ['sub-distributor', 'operator', 'distributor'].includes(u.role) && u.status === 'active'
        ));
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        setLoadingData(false);
      }
    };
    if (canCreateDistribution) fetchData();
  }, [canCreateDistribution]);
  
  if (!canCreateDistribution) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <ShieldAlert className="w-16 h-16 text-red-500 mb-4" />
        <h1 className="text-xl font-bold text-gray-800 text-center">Access Denied</h1>
        <p className="text-gray-500 mt-2 text-center">Only Admins and Managers can create distributions.</p>
        <Button className="mt-4" onClick={() => navigate('/distributions')}>
          Back to Distributions
        </Button>
      </div>
    );
  }
  
  const filteredDevices = availableDevices.filter(d => 
    (d.mac_address || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.model || d.device_type || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.serial_number || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddDevice = (device) => {
    if (!selectedDevices.find(d => (d._id || d.id) === (device._id || device.id))) {
      setSelectedDevices(prev => [...prev, device]);
    }
  };

  const handleRemoveDevice = (deviceId) => {
    setSelectedDevices(prev => prev.filter(d => (d._id || d.id) !== deviceId));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (selectedDevices.length === 0) {
      showToast('Please select at least one device', 'error');
      return;
    }

    if (!formData.toDistributor) {
      showToast('Please select a recipient', 'error');
      return;
    }

    setLoading(true);
    try {
      await distributionsAPI.createDistribution({
        device_ids: selectedDevices.map(d => d._id || d.id),
        to_user_id: formData.toDistributor,
        notes: formData.notes
      });
      showToast('Distribution created successfully!', 'success');
      navigate('/distributions');
    } catch (error) {
      showToast(error.message || 'Failed to create distribution', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Create Distribution</h1>
        <p className="text-gray-500 mt-1 text-sm sm:text-base">
          Distribute devices to distributors, sub-distributors, or operators
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {/* Available Devices */}
          <Card title="Available Devices" icon={Search}>
            <div className="space-y-4">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by MAC, model, or serial..."
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              
              <div className="max-h-80 overflow-y-auto space-y-2">
                {filteredDevices.length === 0 ? (
                  <p className="text-center text-gray-500 py-4">No devices available</p>
                ) : (
                  filteredDevices.map(device => (
                    <div 
                      key={device._id || device.id} 
                      className={`flex items-center justify-between p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedDevices.find(d => (d._id || d.id) === (device._id || device.id))
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300'
                      }`}
                      onClick={() => handleAddDevice(device)}
                    >
                      <div>
                        <p className="font-medium text-gray-800">{device.model || device.device_type}</p>
                        <p className="text-sm text-gray-500">{device.mac_address}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={device.status} size="sm" />
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAddDevice(device);
                          }}
                          className="p-1 text-blue-600 hover:bg-blue-100 rounded"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </Card>

          {/* Selected Devices */}
          <Card title={`Selected Devices (${selectedDevices.length})`} icon={Truck}>
            <div className="space-y-4">
              <div className="max-h-80 overflow-y-auto space-y-2">
                {selectedDevices.length === 0 ? (
                  <p className="text-center text-gray-500 py-8">
                    Click on devices to add them to the distribution
                  </p>
                ) : (
                  selectedDevices.map(device => (
                    <div 
                      key={device._id || device.id} 
                      className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-gray-800">{device.model || device.device_type}</p>
                        <p className="text-sm text-gray-500">{device.mac_address}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveDevice(device._id || device.id)}
                        className="p-1 text-red-600 hover:bg-red-100 rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* Distribution Details */}
        <Card title="Distribution Details">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Recipient <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.toDistributor}
                onChange={(e) => setFormData(prev => ({ ...prev, toDistributor: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Select recipient...</option>
                {recipients.map(r => (
                  <option key={r._id || r.id} value={r._id || r.id}>
                    {r.name} ({r.role})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Batch ID
              </label>
              <input
                type="text"
                value={`BATCH-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, '0')}`}
                disabled
                className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-500"
              />
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
              rows={3}
              placeholder="Add any notes for this distribution..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </Card>

        {/* Summary */}
        {selectedDevices.length > 0 && (
          <Card className="bg-blue-50 border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-blue-800">Distribution Summary</p>
                <p className="text-sm text-blue-600">
                  {selectedDevices.length} device(s) will be sent to{' '}
                  {recipients.find(r => r.id === formData.toDistributor)?.name || 'selected recipient'}
                </p>
              </div>
              <Truck className="w-8 h-8 text-blue-600" />
            </div>
          </Card>
        )}

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-3">
          <Button variant="secondary" onClick={() => navigate('/distributions')} icon={X} className="w-full sm:w-auto">
            Cancel
          </Button>
          <Button type="submit" loading={loading} icon={Save} className="w-full sm:w-auto">
            Create Distribution
          </Button>
        </div>
      </form>
    </div>
  );
};

export default CreateDistribution;
