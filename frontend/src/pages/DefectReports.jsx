import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Card from '../components/ui/Card';
import { defectsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { Plus, Eye, AlertTriangle, CheckCircle, XCircle, MessageSquare, Loader2, RefreshCw } from 'lucide-react';

const DefectReports = () => {
  const { user } = useAuth();
  const { showToast } = useNotifications();
  const [defectReports, setDefectReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDefect, setSelectedDefect] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [showReplaceModal, setShowReplaceModal] = useState(false);
  const [reviewComment, setReviewComment] = useState('');
  const [replaceData, setReplaceData] = useState({ mac_address: '', serial_number: '', notes: '' });

  const fetchDefects = async () => {
    try {
      setLoading(true);
      const response = await defectsAPI.getDefects();
      setDefectReports(response.data || []);
    } catch (error) {
      console.error('Failed to fetch defects:', error);
      showToast('Failed to load defect reports', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDefects();
  }, []);

  const canReport = ['operator', 'sub_distributor', 'cluster'].includes(user?.role);
  const canReview = ['sub_distributor', 'admin', 'manager', 'staff'].includes(user?.role);
  const canReplace = ['admin', 'manager', 'staff'].includes(user?.role);

  const columns = [
    {
      key: 'device_name',
      label: 'Device',
      render: (value, row) => (
        <div>
          <p className="font-medium text-gray-800">{value || row.device_type || 'Unknown'}</p>
          <p className="text-xs text-gray-500">{row.serial_number || row.mac_address || ''}</p>
        </div>
      )
    },
    { key: 'defect_type', label: 'Type' },
    {
      key: 'severity',
      label: 'Severity',
      render: (value) => <StatusBadge status={value} size="sm" />
    },
    { key: 'reported_by_name', label: 'Reported By' },
    { key: 'created_at', label: 'Date', render: (value) => value ? new Date(value).toLocaleDateString() : '-' },
    {
      key: 'status',
      label: 'Status',
      render: (value) => <StatusBadge status={value} />
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
              setSelectedDefect(row);
              setShowModal(true);
            }}
            className="p-1 text-blue-600 hover:bg-blue-50 rounded"
          >
            <Eye className="w-4 h-4" />
          </button>
          {canReview && row.status === 'reported' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSelectedDefect(row);
                setShowReviewModal(true);
              }}
              className="p-1 text-green-600 hover:bg-green-50 rounded"
            >
              <MessageSquare className="w-4 h-4" />
            </button>
          )}
          {canReplace && row.status === 'approved' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSelectedDefect(row);
                setReplaceData({ mac_address: '', serial_number: '', notes: '' });
                setShowReplaceModal(true);
              }}
              className="p-1 text-purple-600 hover:bg-purple-50 rounded"
              title="Replace Device"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
        </div>
      )
    }
  ];

  const handleReview = async (action) => {
    try {
      await defectsAPI.updateDefectStatus(
        selectedDefect._id || selectedDefect.id,
        action,
        reviewComment
      );
      showToast(
        action === 'approved'
          ? 'Defect approved — return request automatically created'
          : 'Defect report rejected',
        action === 'approved' ? 'success' : 'warning'
      );
      setShowReviewModal(false);
      setReviewComment('');
      fetchDefects();
    } catch (error) {
      showToast('Failed to update defect report', 'error');
    }
  };

  const handleReplace = async () => {
    if (!replaceData.mac_address && !replaceData.serial_number) {
      showToast('Please enter MAC address or serial number of the replacement device', 'error');
      return;
    }
    try {
      await defectsAPI.replaceDevice(selectedDefect._id || selectedDefect.id, replaceData);
      showToast('Replacement device assigned to original operator successfully', 'success');
      setShowReplaceModal(false);
      setReplaceData({ mac_address: '', serial_number: '', notes: '' });
      fetchDefects();
    } catch (error) {
      showToast(error.message || 'Failed to replace device', 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Defect Reports</h1>
          <p className="text-gray-500 mt-1">View and manage device defect reports</p>
        </div>
        {canReport && (
          <Link to="/defects/create">
            <Button icon={Plus}>Report Defect</Button>
          </Link>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Total</p>
          <p className="text-2xl font-bold text-gray-800">{defectReports.length}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Open</p>
          <p className="text-2xl font-bold text-yellow-600">
            {defectReports.filter(d => d.status === 'reported').length}
          </p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Under Review</p>
          <p className="text-2xl font-bold text-blue-600">
            {defectReports.filter(d => d.status === 'under_review').length}
          </p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Resolved</p>
          <p className="text-2xl font-bold text-green-600">
            {defectReports.filter(d => d.status === 'resolved').length}
          </p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Critical</p>
          <p className="text-2xl font-bold text-red-600">
            {defectReports.filter(d => d.severity === 'critical').length}
          </p>
        </Card>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="ml-3 text-gray-500">Loading defect reports...</span>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={defectReports}
          onRowClick={(row) => {
            setSelectedDefect(row);
            setShowModal(true);
          }}
        />
      )}

      {/* View Defect Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          setSelectedDefect(null);
        }}
        title="Defect Report Details"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Close</Button>
            {canReview && selectedDefect?.status === 'reported' && (
              <Button onClick={() => {
                setShowModal(false);
                setShowReviewModal(true);
              }}>
                Review Defect
              </Button>
            )}
          </>
        }
      >
        {selectedDefect && (
          <div className="space-y-6">
            <div className="flex items-center gap-4 p-4 bg-red-50 rounded-lg">
              <div className="w-16 h-16 bg-red-100 rounded-xl flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-red-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-800">{selectedDefect.device_name || selectedDefect.device_type || 'Unknown'}</h3>
                <p className="text-gray-500">{selectedDefect.serial_number || selectedDefect.mac_address || ''}</p>
                <div className="flex gap-2 mt-2">
                  <StatusBadge status={selectedDefect.severity} />
                  <StatusBadge status={selectedDefect.status} />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Defect Type</label>
                <p className="font-medium text-gray-800">{selectedDefect.defect_type}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Reported By</label>
                <p className="font-medium text-gray-800">{selectedDefect.reported_by_name || 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Reported At</label>
                <p className="font-medium text-gray-800">{selectedDefect.created_at ? new Date(selectedDefect.created_at).toLocaleDateString() : 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Location</label>
                <p className="font-medium text-gray-800">{selectedDefect.location || 'N/A'}</p>
              </div>
            </div>

            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Description</label>
              <p className="text-gray-800 mt-1 p-3 bg-gray-50 rounded-lg">{selectedDefect.description}</p>
            </div>

            {selectedDefect.auto_return_id && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <label className="text-xs text-green-600 uppercase tracking-wider">Auto-Created Return Request</label>
                <p className="font-medium text-green-800 mt-1">{selectedDefect.auto_return_id}</p>
              </div>
            )}

            {selectedDefect.replacement_device_id && (
              <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                <label className="text-xs text-purple-600 uppercase tracking-wider">Replacement Device</label>
                <p className="font-medium text-purple-800 mt-1">{selectedDefect.resolution}</p>
              </div>
            )}

            {selectedDefect.images && selectedDefect.images.length > 0 && (
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">Photos</label>
                <div className="grid grid-cols-3 gap-2">
                  {selectedDefect.images.map((photo, index) => (
                    <div key={index} className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center">
                      <span className="text-xs text-gray-500">{photo}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedDefect.review_comments && (
              <div className="p-4 bg-blue-50 rounded-lg">
                <label className="text-xs text-blue-600 uppercase tracking-wider">Review Comments</label>
                <p className="text-gray-800 mt-1">{selectedDefect.review_comments}</p>
                <p className="text-xs text-gray-500 mt-2">By: {selectedDefect.reviewed_by_name || 'N/A'}</p>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Review Modal */}
      <Modal
        isOpen={showReviewModal}
        onClose={() => {
          setShowReviewModal(false);
          setReviewComment('');
        }}
        title="Review Defect Report"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowReviewModal(false)}>Cancel</Button>
            <Button variant="danger" onClick={() => handleReview('rejected')}>Reject</Button>
            <Button onClick={() => handleReview('approved')}>Approve & Initiate Return</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-800">{selectedDefect?.device_name || selectedDefect?.device_type || 'Unknown'}</p>
            <p className="text-sm text-gray-500">{selectedDefect?.defect_type} - {selectedDefect?.severity}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Review Comments <span className="text-red-500">*</span>
            </label>
            <textarea
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
              rows={4}
              placeholder="Add your review comments..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-sm text-yellow-800">
              Approving this defect will automatically create a return request for the device.
            </p>
          </div>
        </div>
      </Modal>

      {/* Replace Device Modal */}
      <Modal
        isOpen={showReplaceModal}
        onClose={() => {
          setShowReplaceModal(false);
          setReplaceData({ mac_address: '', serial_number: '', notes: '' });
        }}
        title="Replace Defective Device"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowReplaceModal(false)}>Cancel</Button>
            <Button onClick={handleReplace}>Assign Replacement</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-800">{selectedDefect?.device_type || 'Unknown'}</p>
            <p className="text-sm text-gray-500">
              Original holder: {selectedDefect?.reported_by_name || 'N/A'}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              The replacement device will be automatically mapped to the same operator.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Replacement Device MAC Address
            </label>
            <input
              type="text"
              value={replaceData.mac_address}
              onChange={(e) => setReplaceData(prev => ({ ...prev, mac_address: e.target.value }))}
              placeholder="e.g. AA:BB:CC:DD:EE:FF"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center text-sm text-gray-500 gap-2">
            <div className="flex-1 border-t border-gray-200" />
            <span>or</span>
            <div className="flex-1 border-t border-gray-200" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Replacement Device Serial Number
            </label>
            <input
              type="text"
              value={replaceData.serial_number}
              onChange={(e) => setReplaceData(prev => ({ ...prev, serial_number: e.target.value }))}
              placeholder="e.g. SN-12345678"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes (Optional)
            </label>
            <textarea
              value={replaceData.notes}
              onChange={(e) => setReplaceData(prev => ({ ...prev, notes: e.target.value }))}
              rows={2}
              placeholder="Additional notes about the replacement..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default DefectReports;
