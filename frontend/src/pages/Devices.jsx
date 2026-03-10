import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Card from '../components/ui/Card';
import { devicesAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { Plus, Eye, Edit, Trash2, Box, Download, Upload, Loader2 } from 'lucide-react';

const Devices = () => {
  const { user } = useAuth();
  const { showToast } = useNotifications();
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const response = await devicesAPI.getDevices({ page_size: 100 });
      setDevices(response.data || []);
    } catch (error) {
      console.error('Failed to fetch devices:', error);
      showToast('Failed to load devices', 'error');
    } finally {
      setLoading(false);
    }
  };

  const canRegister = ['admin', 'manager', 'staff'].includes(user?.role);

  const columns = [
    { key: 'mac_address', label: 'MAC Address' },
    { key: 'serial_number', label: 'Serial Number' },
    { key: 'model', label: 'Model' },
    { key: 'manufacturer', label: 'Manufacturer' },
    {
      key: 'device_type',
      label: 'Type',
      render: (value) => <StatusBadge status={value} size="sm" />
    },
    {
      key: 'status',
      label: 'Status',
      render: (value) => <StatusBadge status={value} />
    },
    { key: 'current_holder_name', label: 'Current Holder', render: (value, row) => {
      if (value && value !== 'NOC') return value;
      if (!row.current_holder_type || row.current_holder_type === 'noc') return 'PDIC (Distribution)';
      return value || 'PDIC (Distribution)';
    } },
    {
      key: 'actions',
      label: 'Actions',
      sortable: false,
      render: (_, row) => (
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setSelectedDevice(row);
              setShowModal(true);
            }}
            className="p-1 text-blue-600 hover:bg-blue-50 rounded"
          >
            <Eye className="w-4 h-4" />
          </button>
          {canRegister && (
            <>
              <button className="p-1 text-gray-600 hover:bg-gray-50 rounded">
                <Edit className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedDevice(row);
                  setShowDeleteModal(true);
                }}
                className="p-1 text-red-600 hover:bg-red-50 rounded"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      )
    }
  ];

  const handleDelete = async () => {
    try {
      await devicesAPI.deleteDevice(selectedDevice.id);
      showToast(`Device ${selectedDevice.mac_address} deleted successfully`, 'success');
      setShowDeleteModal(false);
      setSelectedDevice(null);
      fetchDevices();
    } catch (error) {
      showToast('Failed to delete device', 'error');
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Devices</h1>
          <p className="text-gray-500 mt-1 text-sm sm:text-base">
            {user?.role === 'operator' ? 'Your assigned devices' : 'Manage all registered devices'}
          </p>
        </div>
        {canRegister && (
          <div className="flex flex-col sm:flex-row gap-2">
            <Link to="/devices/bulk-import" className="w-full sm:w-auto">
              <Button variant="secondary" icon={Upload} className="w-full sm:w-auto">Bulk Import</Button>
            </Link>
            <Link to="/devices/register" className="w-full sm:w-auto">
              <Button icon={Plus} className="w-full sm:w-auto">Register Device</Button>
            </Link>
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Total</p>
          <p className="text-2xl font-bold text-gray-800">{devices.length}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Available</p>
          <p className="text-2xl font-bold text-green-600">{devices.filter(d => d.status === 'available').length}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Distributed</p>
          <p className="text-2xl font-bold text-blue-600">{devices.filter(d => d.status === 'distributed').length}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">In Use</p>
          <p className="text-2xl font-bold text-purple-600">{devices.filter(d => d.status === 'in_use').length}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Defective</p>
          <p className="text-2xl font-bold text-red-600">{devices.filter(d => d.status === 'defective').length}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Returned</p>
          <p className="text-2xl font-bold text-orange-600">{devices.filter(d => d.status === 'returned').length}</p>
        </Card>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="ml-3 text-gray-500">Loading devices...</span>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={devices}
          selectable={canRegister}
          onRowClick={(row) => {
            setSelectedDevice(row);
            setShowModal(true);
          }}
        />
      )}

      {/* View Device Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          setSelectedDevice(null);
        }}
        title="Device Details"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Close</Button>
            <Link to={`/track-device?serial=${selectedDevice?.serial_number}`}>
              <Button>Track Device</Button>
            </Link>
          </>
        }
      >
        {selectedDevice && (
          <div className="space-y-6">
            <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="w-16 h-16 bg-blue-100 rounded-xl flex items-center justify-center">
                <Box className="w-8 h-8 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">{selectedDevice.model || selectedDevice.device_type}</h3>
                <p className="text-gray-500">{selectedDevice.manufacturer || 'N/A'}</p>
                <div className="flex gap-2 mt-2">
                  <StatusBadge status={selectedDevice.status} />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">MAC Address</label>
                <p className="font-medium text-gray-800 font-mono">{selectedDevice.mac_address}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Serial Number</label>
                <p className="font-medium text-gray-800">{selectedDevice.serial_number}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Device Type</label>
                <p className="font-medium text-gray-800">{selectedDevice.device_type}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Device ID</label>
                <p className="font-medium text-gray-800">{selectedDevice.device_id}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Current Location</label>
                <p className="font-medium text-gray-800">
                  {(() => {
                    const loc = selectedDevice.current_location;
                    if (!loc || loc === 'NOC' || loc === 'PDIC') return 'PDIC (Distribution)';
                    return loc;
                  })()}
                </p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Current Holder</label>
                <p className="font-medium text-gray-800">
                  {(() => {
                    const name = selectedDevice.current_holder_name;
                    const type = selectedDevice.current_holder_type;
                    if (!name || name === 'NOC' || (!name && type === 'noc')) return 'PDIC (Distribution)';
                    return name;
                  })()}
                </p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Created At</label>
                <p className="font-medium text-gray-800">{selectedDevice.created_at ? new Date(selectedDevice.created_at).toLocaleDateString() : 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Registered By</label>
                <p className="font-medium text-gray-800">{selectedDevice.registered_by_name || 'N/A'}</p>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Device"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>Cancel</Button>
            <Button variant="danger" onClick={handleDelete}>Delete</Button>
          </>
        }
      >
        <p className="text-gray-600">
          Are you sure you want to delete device <span className="font-medium">{selectedDevice?.mac_address}</span>? 
          This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
};

export default Devices;
