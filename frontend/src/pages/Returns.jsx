import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Card from '../components/ui/Card';
import Timeline from '../components/ui/Timeline';
import { returnsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { Plus, Eye, RotateCcw, CheckCircle, XCircle, Truck, Loader2 } from 'lucide-react';

const Returns = () => {
  const { user } = useAuth();
  const { showToast } = useNotifications();
  const [returnRequests, setReturnRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedReturn, setSelectedReturn] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showActionModal, setShowActionModal] = useState(false);
  const [actionComment, setActionComment] = useState('');

  const fetchReturns = async () => {
    try {
      setLoading(true);
      const response = await returnsAPI.getReturns();
      setReturnRequests(response.data || []);
    } catch (error) {
      console.error('Failed to fetch returns:', error);
      showToast('Failed to load return requests', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReturns();
  }, []);

  const canInitiate = ['operator', 'sub_distributor', 'cluster'].includes(user?.role);
  const canApprove = ['sub_distributor', 'admin', 'manager', 'staff'].includes(user?.role);

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
    { key: 'reason', label: 'Reason' },
    { key: 'requested_action', label: 'Requested' },
    { key: 'initiated_by_name', label: 'Initiated By' },
    { key: 'created_at', label: 'Date', render: (value) => value ? new Date(value).toLocaleDateString() : '-' },
    {
      key: 'current_approver',
      label: 'Awaiting',
      render: (value) => value ? <span className="capitalize">{value}</span> : '-'
    },
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
              setSelectedReturn(row);
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
                  setSelectedReturn(row);
                  setShowActionModal(true);
                }}
                className="p-1 text-green-600 hover:bg-green-50 rounded"
              >
                <CheckCircle className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      )
    }
  ];

  const handleAction = async (action) => {
    try {
      await returnsAPI.updateReturnStatus(
        selectedReturn._id || selectedReturn.id,
        action,
        actionComment
      );
      showToast(`Return request ${action}`, action === 'approved' ? 'success' : 'warning');
      setShowActionModal(false);
      setActionComment('');
      fetchReturns();
    } catch (error) {
      showToast('Failed to update return request', 'error');
    }
  };

  const getTimelineItems = (returnReq) => {
    const items = [
      {
        title: 'Return Initiated',
        description: `By ${returnReq.initiated_by_name || 'Unknown'}`,
        timestamp: returnReq.created_at ? new Date(returnReq.created_at).toLocaleDateString() : '',
        status: 'completed'
      }
    ];

    if (returnReq.approval_chain) {
      returnReq.approval_chain.forEach((approval) => {
        items.push({
          title: `${(approval.role || '').replace('-', ' ')} Review`,
          description: approval.status === 'approved' 
            ? `Approved by ${approval.by || 'Unknown'}`
            : approval.status === 'pending' 
              ? 'Awaiting review'
              : 'Under review',
          timestamp: approval.at || '',
          user: approval.by,
          status: approval.status === 'approved' ? 'completed' : 
                  approval.status === 'pending' ? 'current' : 'pending'
        });
      });
    }

    if (returnReq.completed_at) {
      items.push({
        title: 'Return Completed',
        timestamp: new Date(returnReq.completed_at).toLocaleDateString(),
        status: 'completed'
      });
    }

    return items;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Return Requests</h1>
          <p className="text-gray-500 mt-1">Manage device return requests and approvals</p>
        </div>
        {canInitiate && (
          <Link to="/returns/create">
            <Button icon={Plus}>Initiate Return</Button>
          </Link>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Total</p>
          <p className="text-2xl font-bold text-gray-800">{returnRequests.length}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Pending</p>
          <p className="text-2xl font-bold text-yellow-600">
            {returnRequests.filter(r => r.status === 'pending').length}
          </p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Under Review</p>
          <p className="text-2xl font-bold text-blue-600">
            {returnRequests.filter(r => r.status === 'under-review').length}
          </p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Approved</p>
          <p className="text-2xl font-bold text-green-600">
            {returnRequests.filter(r => r.status === 'approved').length}
          </p>
        </Card>
        <Card className="!p-4">
          <p className="text-sm text-gray-500">Rejected</p>
          <p className="text-2xl font-bold text-red-600">
            {returnRequests.filter(r => r.status === 'rejected').length}
          </p>
        </Card>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="ml-3 text-gray-500">Loading return requests...</span>
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={returnRequests}
          onRowClick={(row) => {
            setSelectedReturn(row);
            setShowModal(true);
          }}
        />
      )}

      {/* View Return Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          setSelectedReturn(null);
        }}
        title="Return Request Details"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Close</Button>
            {canApprove && selectedReturn?.status === 'pending' && (
              <Button onClick={() => {
                setShowModal(false);
                setShowActionModal(true);
              }}>
                Review Request
              </Button>
            )}
          </>
        }
      >
        {selectedReturn && (
          <div className="space-y-6">
            <div className="flex items-center gap-4 p-4 bg-orange-50 rounded-lg">
              <div className="w-16 h-16 bg-orange-100 rounded-xl flex items-center justify-center">
                <RotateCcw className="w-8 h-8 text-orange-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-800">{selectedReturn.device_name || selectedReturn.device_type || 'Unknown'}</h3>
                <p className="text-gray-500">{selectedReturn.serial_number || selectedReturn.mac_address || ''}</p>
                <StatusBadge status={selectedReturn.status} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Reason</label>
                <p className="font-medium text-gray-800">{selectedReturn.reason}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Requested Action</label>
                <p className="font-medium text-gray-800">{selectedReturn.requested_action}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Initiated By</label>
                <p className="font-medium text-gray-800">{selectedReturn.initiated_by_name || 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Created At</label>
                <p className="font-medium text-gray-800">{selectedReturn.created_at ? new Date(selectedReturn.created_at).toLocaleDateString() : 'N/A'}</p>
              </div>
            </div>

            {selectedReturn.notes && (
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Notes</label>
                <p className="text-gray-800 mt-1 p-3 bg-gray-50 rounded-lg">{selectedReturn.notes}</p>
              </div>
            )}

            {selectedReturn.defect_report_id && (
              <div className="p-4 bg-red-50 rounded-lg">
                <label className="text-xs text-red-600 uppercase tracking-wider">Linked Defect Report</label>
                <p className="font-medium text-red-800">Report ID: {selectedReturn.defect_report_id}</p>
              </div>
            )}

            {/* Approval Timeline */}
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider mb-3 block">Approval Timeline</label>
              <Timeline items={getTimelineItems(selectedReturn)} />
            </div>
          </div>
        )}
      </Modal>

      {/* Action Modal */}
      <Modal
        isOpen={showActionModal}
        onClose={() => {
          setShowActionModal(false);
          setActionComment('');
        }}
        title="Review Return Request"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowActionModal(false)}>Cancel</Button>
            <Button variant="danger" onClick={() => handleAction('rejected')}>Reject</Button>
            <Button onClick={() => handleAction('approved')}>Approve</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-800">{selectedReturn?.device_name || selectedReturn?.device_type || 'Unknown'}</p>
            <p className="text-sm text-gray-500">{selectedReturn?.reason}</p>
            <p className="text-sm text-gray-500">Requested: {selectedReturn?.requested_action}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Comments
            </label>
            <textarea
              value={actionComment}
              onChange={(e) => setActionComment(e.target.value)}
              rows={3}
              placeholder="Add your review comments..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-800">
              {user?.role === 'sub_distributor' 
                ? 'Approving will forward this request to the management.'
                : 'Approving will complete this return request.'}
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Returns;
