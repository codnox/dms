import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Card from '../components/ui/Card';
import { distributionsAPI, devicesAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { Plus, Eye, Truck, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';

const Distributions = () => {
  const { user } = useAuth();
  const { showToast } = useNotifications();
  const [distributions, setDistributions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDist, setSelectedDist] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [approvalComment, setApprovalComment] = useState('');
  const [distributionDevices, setDistributionDevices] = useState([]);
  const [loadingDevices, setLoadingDevices] = useState(false);

  const fetchDistributions = async () => {
    try {
      setLoading(true);
      const response = await distributionsAPI.getDistributions();
      setDistributions(response.data || []);
    } catch (error) {
      console.error('Failed to fetch distributions:', error);
      showToast('Failed to load distributions', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchDistributionDevices = async (deviceIds) => {
    if (!deviceIds || deviceIds.length === 0) {
      setDistributionDevices([]);
      return;
    }
    
    try {
      setLoadingDevices(true);
      const devicePromises = deviceIds.map(id => devicesAPI.getDevice(id));
      const responses = await Promise.all(devicePromises);
      const devices = responses.map(res => res.data).filter(Boolean);
      setDistributionDevices(devices);
    } catch (error) {
      console.error('Failed to fetch distribution devices:', error);
      setDistributionDevices([]);
    } finally {
      setLoadingDevices(false);
    }
  };

  useEffect(() => {
    fetchDistributions();
  }, []);

  useEffect(() => {
    if (showModal && selectedDist) {
      fetchDistributionDevices(selectedDist.device_ids);
    }
  }, [showModal, selectedDist]);

  const canCreate = ['admin', 'distributor', 'sub-distributor'].includes(user?.role);
  const canApprove = ['sub-distributor', 'operator'].includes(user?.role);

  const columns = [
    { key: 'distribution_id', label: 'Distribution ID' },
    { key: 'from_user_name', label: 'From' },
    { key: 'to_user_name', label: 'To' },
    { key: 'device_count', label: 'Devices', render: (value, row) => value || row.device_ids?.length || 0 },
    {
      key: 'status',
      label: 'Status',
      render: (value) => <StatusBadge status={value} />
    },
    { key: 'created_at', label: 'Created', render: (value) => value ? new Date(value).toLocaleDateString() : '-' },
    {
      key: 'approved_by_name',
      label: 'Approved By',
      render: (value) => value || '-'
    },
    {
      key: 'actions',
      label: 'Actions',
      sortable: false,
      render: (_, row) => (
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setSelectedDist(row);
              setShowModal(true);
            }}
            className="p-1 text-blue-600 hover:bg-blue-50 rounded"
          >
            <Eye className="w-4 h-4" />
          </button>
          {canApprove && row.status === 'pending' && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedDist(row);
                  setShowApproveModal(true);
                }}
                className="p-1 text-green-600 hover:bg-green-50 rounded"
              >
                <CheckCircle className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  showToast('Distribution rejected', 'warning');
                }}
                className="p-1 text-red-600 hover:bg-red-50 rounded"
              >
                <XCircle className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      )
    }
  ];

  const handleApprove = async () => {
    try {
      await distributionsAPI.updateDistributionStatus(
        selectedDist._id || selectedDist.id, 
        'approved', 
        approvalComment
      );
      showToast('Distribution approved successfully', 'success');
      setShowApproveModal(false);
      setSelectedDist(null);
      setApprovalComment('');
      fetchDistributions();
    } catch (error) {
      showToast('Failed to approve distribution', 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Distributions</h1>
          <p className="text-gray-500 mt-1">Manage device distributions across the chain</p>
        </div>
        {canCreate && (
          <Link to="/distributions/create">
            <Button icon={Plus}>Create Distribution</Button>
          </Link>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Truck className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-xl font-bold text-gray-800">{distributions.length}</p>
            </div>
          </div>
        </Card>
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Pending</p>
              <p className="text-xl font-bold text-yellow-600">
                {distributions.filter(d => d.status === 'pending').length}
              </p>
            </div>
          </div>
        </Card>
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Approved</p>
              <p className="text-xl font-bold text-green-600">
                {distributions.filter(d => d.status === 'approved').length}
              </p>
            </div>
          </div>
        </Card>
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
              <Truck className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">In Transit</p>
              <p className="text-xl font-bold text-indigo-600">
                {distributions.filter(d => d.status === 'in-transit').length}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="ml-3 text-gray-500">Loading distributions...</span>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={distributions}
          onRowClick={(row) => {
            setSelectedDist(row);
            setShowModal(true);
          }}
        />
      )}

      {/* View Distribution Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          setSelectedDist(null);
          setDistributionDevices([]);
        }}
        title="Distribution Details"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Close</Button>
            {canApprove && selectedDist?.status === 'pending' && (
              <Button onClick={() => {
                setShowModal(false);
                setShowApproveModal(true);
              }}>
                Approve Distribution
              </Button>
            )}
          </>
        }
      >
        {selectedDist && (
          <div className="space-y-6">
            <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="w-16 h-16 bg-blue-100 rounded-xl flex items-center justify-center">
                <Truck className="w-8 h-8 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-800">{selectedDist.distribution_id}</h3>
                <p className="text-gray-500">{selectedDist.from_user_name} → {selectedDist.to_user_name}</p>
                <StatusBadge status={selectedDist.status} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Created At</label>
                <p className="font-medium text-gray-800">{selectedDist.created_at ? new Date(selectedDist.created_at).toLocaleDateString() : 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Device Count</label>
                <p className="font-medium text-gray-800">{selectedDist.device_count || selectedDist.device_ids?.length || 0}</p>
              </div>
              {selectedDist.approved_at && (
                <>
                  <div>
                    <label className="text-xs text-gray-500 uppercase tracking-wider">Approved At</label>
                    <p className="font-medium text-gray-800">{new Date(selectedDist.approved_at).toLocaleDateString()}</p>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 uppercase tracking-wider">Approved By</label>
                    <p className="font-medium text-gray-800">{selectedDist.approved_by_name || 'N/A'}</p>
                  </div>
                </>
              )}
            </div>

            {selectedDist.notes && (
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Notes</label>
                <p className="text-gray-800 mt-1">{selectedDist.notes}</p>
              </div>
            )}

            {/* Devices List */}
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">Devices</label>
              {loadingDevices ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  <span className="ml-2 text-gray-500">Loading devices...</span>
                </div>
              ) : distributionDevices.length > 0 ? (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {distributionDevices.map((device, index) => (
                    <div key={device._id || device.id || index} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="font-medium text-gray-800">{device.model || device.device_type}</p>
                          <p className="text-sm text-gray-500 font-mono">{device.serial_number}</p>
                          <p className="text-xs text-gray-400">{device.mac_address}</p>
                        </div>
                        <StatusBadge status={device.status} size="sm" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm py-2">No device details available</p>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* Approval Modal */}
      <Modal
        isOpen={showApproveModal}
        onClose={() => {
          setShowApproveModal(false);
          setApprovalComment('');
        }}
        title="Approve Distribution"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowApproveModal(false)}>Cancel</Button>
            <Button variant="danger" onClick={() => {
              showToast('Distribution rejected', 'warning');
              setShowApproveModal(false);
            }}>
              Reject
            </Button>
            <Button onClick={handleApprove}>Approve</Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-gray-600">
            You are about to approve distribution <span className="font-medium">{selectedDist?.distribution_id}</span> with {selectedDist?.device_count || selectedDist?.device_ids?.length || 0} devices.
          </p>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Comments (Optional)
            </label>
            <textarea
              value={approvalComment}
              onChange={(e) => setApprovalComment(e.target.value)}
              rows={3}
              placeholder="Add any comments or notes..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-sm text-yellow-800">
              By approving, you confirm that you have received all devices in good condition.
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Distributions;
