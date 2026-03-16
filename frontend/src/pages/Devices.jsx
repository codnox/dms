import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Card from '../components/ui/Card';
import { devicesAPI, defectsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { Plus, Eye, Edit, Trash2, Box, Upload, Loader2, Users, Send, ArrowDownToLine, Link2, AlertTriangle, CheckCircle2, Save } from 'lucide-react';

const Devices = () => {
  const { user } = useAuth();
  const { showToast } = useNotifications();
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [overview, setOverview] = useState(null);
  const [defectsData, setDefectsData] = useState([]);
  const [replacementMap, setReplacementMap] = useState({ replacementIds: new Set(), defectiveIds: new Set(), defectByDeviceId: {} });
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all');

  // Edit form state
  const [editForm, setEditForm] = useState({ model: '', manufacturer: '', current_location: '' });
  const [editSubmitting, setEditSubmitting] = useState(false);

  const isManagement = ['admin', 'manager', 'staff'].includes(user?.role);
  const hasHierarchy = ['sub_distributor', 'cluster'].includes(user?.role);
  const canRegister = ['admin', 'manager', 'staff'].includes(user?.role);
  const isStaff = user?.role === 'staff';
  const isAdminOrManager = ['admin', 'manager'].includes(user?.role);

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const [overviewResponse, defectsResponse] = await Promise.all([
        devicesAPI.getMyOverview(),
        defectsAPI.getDefects({ page_size: 100 })
      ]);

      setOverview(overviewResponse.data);

      const replacementIds = new Set();
      const defectiveIds = new Set();
      const defectByDeviceId = {};
      for (const defect of defectsResponse.data || []) {
        if (defect.replacement_device_id) {
          replacementIds.add(String(defect.replacement_device_id));
          defectiveIds.add(String(defect.device_id));
          defectByDeviceId[String(defect.replacement_device_id)] = defect;
          defectByDeviceId[String(defect.device_id)] = defect;
        } else if (defect.device_id) {
          defectByDeviceId[String(defect.device_id)] = defect;
          if (defect.status !== 'resolved') defectiveIds.add(String(defect.device_id));
        }
      }
      setDefectsData(defectsResponse.data || []);
      setReplacementMap({ replacementIds, defectiveIds, defectByDeviceId });
    } catch (error) {
      console.error('Failed to fetch devices:', error);
      showToast('Failed to load devices', 'error');
    } finally {
      setLoading(false);
    }
  };

  const overviewStats = overview?.stats || {};

  const getEffectiveDeviceStatus = (device) => {
    const linked = replacementMap.defectByDeviceId[String(device.id)];
    if (
      linked &&
      String(linked.device_id) === String(device.id) &&
      Boolean(linked.replacement_device_id)
    ) {
      return 'replaced';
    }
    return device.status;
  };

  const displayedDevices = (() => {
    if (!overview) return [];
    const getCategoryRank = (device) => {
      const id = String(device.id);
      if (replacementMap.replacementIds.has(id)) return 1;  // replacement — show second
      if (replacementMap.defectiveIds.has(id) || device.status === 'defective') return 2; // defective — show last
      return 0; // normal — show first
    };

    const sortByReplacementGroups = (devices) => [...devices].sort((a, b) => {
      const rankDiff = getCategoryRank(a) - getCategoryRank(b);
      if (rankDiff !== 0) return rankDiff;
      const aTime = new Date(a.updated_at || a.created_at || 0).getTime();
      const bTime = new Date(b.updated_at || b.created_at || 0).getTime();
      return bTime - aTime;
    });

    if (!hasHierarchy) return sortByReplacementGroups(overview.all_under_me || []);
    switch (activeTab) {
      case 'mine': return sortByReplacementGroups(overview.held_by_me || []);
      case 'hierarchy': return sortByReplacementGroups(overview.under_subordinates || []);
      default: return sortByReplacementGroups(overview.all_under_me || []);
    }
  })();

  const getRowClassName = (row) => {
    const id = String(row.id);
    if (replacementMap.replacementIds.has(id)) return 'bg-emerald-50 border-l-4 border-l-emerald-400';
    if (replacementMap.defectiveIds.has(id) || row.status === 'defective') return 'bg-red-50 border-l-4 border-l-red-400';
    return '';
  };

  const openEditModal = (device) => {
    setSelectedDevice(device);
    setEditForm({
      model: device.model || '',
      manufacturer: device.manufacturer || '',
      current_location: device.current_location || '',
    });
    setShowEditModal(true);
  };

  const handleEditSubmit = async () => {
    if (!editForm.model && !editForm.manufacturer && !editForm.current_location) {
      showToast('At least one field must be filled in.', 'error');
      return;
    }
    try {
      setEditSubmitting(true);
      if (isStaff) {
        // Staff must request approval — send notification to admins/managers
        await devicesAPI.requestDeviceEdit(selectedDevice.id, editForm);
        showToast('Edit request submitted. A manager or admin will review your proposed changes.', 'info');
      } else {
        // Admin/manager: apply directly
        await devicesAPI.updateDevice(selectedDevice.id, editForm);
        showToast('Device updated successfully.', 'success');
      }
      setShowEditModal(false);
      fetchDevices();
    } catch (error) {
      showToast(error.message || 'Failed to update device', 'error');
    } finally {
      setEditSubmitting(false);
    }
  };

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
      render: (_, row) => <StatusBadge status={getEffectiveDeviceStatus(row)} />
    },
    {
      key: 'replacement_relation',
      label: 'Relation',
      sortable: false,
      render: (_, row) => {
        const id = String(row.id);
        if (replacementMap.replacementIds.has(id)) {
          return <StatusBadge status="replacement" size="sm" />;
        }
        if (replacementMap.defectiveIds.has(id) || row.status === 'defective') {
          return <StatusBadge status="defective_device" size="sm" />;
        }
        return <span className="text-xs text-gray-500">Regular</span>;
      }
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
            title="View Details"
          >
            <Eye className="w-4 h-4" />
          </button>
          {canRegister && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  openEditModal(row);
                }}
                className="p-1 text-amber-600 hover:bg-amber-50 rounded"
                title={isStaff ? 'Request Edit (requires manager approval)' : 'Edit Device'}
              >
                <Edit className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedDevice(row);
                  setShowDeleteModal(true);
                }}
                className="p-1 text-red-600 hover:bg-red-50 rounded"
                title="Delete Device"
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

  // Get the defect linked to the selected device (if any)
  const linkedDefect = selectedDevice
    ? replacementMap.defectByDeviceId[String(selectedDevice.id)]
    : null;
  const isReplacementDevice = selectedDevice ? replacementMap.replacementIds.has(String(selectedDevice.id)) : false;
  const selectedDeviceEffectiveStatus = selectedDevice ? getEffectiveDeviceStatus(selectedDevice) : null;
  const isDefectiveDevice = selectedDevice
    ? (
      (replacementMap.defectiveIds.has(String(selectedDevice.id)) || selectedDevice.status === 'defective') &&
      selectedDeviceEffectiveStatus !== 'replaced'
    )
    : false;

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Devices</h1>
          <p className="text-gray-500 mt-1 text-sm sm:text-base">
            {isManagement ? 'All registered devices in the system'
              : hasHierarchy ? 'Devices across your entire distribution chain'
              : 'Your assigned devices'}
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
      {!loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {isManagement ? (
            <>
              <Card className="!p-4">
                <p className="text-sm text-gray-500">Total</p>
                <p className="text-2xl font-bold text-gray-800">{overviewStats.total || (overview?.all_under_me?.length || 0)}</p>
              </Card>
              <Card className="!p-4">
                <p className="text-sm text-gray-500">Available</p>
                <p className="text-2xl font-bold text-green-600">{overviewStats.available || (overview?.all_under_me || []).filter(d => d.status === 'available').length}</p>
              </Card>
              <Card className="!p-4">
                <p className="text-sm text-gray-500">Distributed</p>
                <p className="text-2xl font-bold text-blue-600">{overviewStats.distributed || (overview?.all_under_me || []).filter(d => d.status === 'distributed').length}</p>
              </Card>
              <Card className="!p-4">
                <p className="text-sm text-gray-500">In Use</p>
                <p className="text-2xl font-bold text-purple-600">{overviewStats.in_use || (overview?.all_under_me || []).filter(d => d.status === 'in_use').length}</p>
              </Card>
              <Card className="!p-4">
                <p className="text-sm text-gray-500">Defective</p>
                <p className="text-2xl font-bold text-red-600">{overviewStats.defective || (overview?.all_under_me || []).filter(d => d.status === 'defective').length}</p>
              </Card>
              <Card className="!p-4">
                <p className="text-sm text-gray-500">Returned</p>
                <p className="text-2xl font-bold text-orange-600">{overviewStats.returned || (overview?.all_under_me || []).filter(d => d.status === 'returned').length}</p>
              </Card>
            </>
          ) : (
            <>
              <Card className="!p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Box className="w-4 h-4 text-blue-500" />
                  <p className="text-xs text-gray-500">In My Hand</p>
                </div>
                <p className="text-2xl font-bold text-blue-600">{overviewStats.in_my_hand || 0}</p>
              </Card>
              {hasHierarchy && (
                <Card className="!p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="w-4 h-4 text-purple-500" />
                    <p className="text-xs text-gray-500">Under My Chain</p>
                  </div>
                  <p className="text-2xl font-bold text-purple-600">{overviewStats.under_subordinates || 0}</p>
                </Card>
              )}
              <Card className="!p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Box className="w-4 h-4 text-gray-500" />
                  <p className="text-xs text-gray-500">Total in Chain</p>
                </div>
                <p className="text-2xl font-bold text-gray-700">{overviewStats.total_in_chain || 0}</p>
              </Card>
              <Card className="!p-4">
                <div className="flex items-center gap-2 mb-1">
                  <ArrowDownToLine className="w-4 h-4 text-green-500" />
                  <p className="text-xs text-gray-500">Total Received</p>
                </div>
                <p className="text-2xl font-bold text-green-600">{overviewStats.total_devices_received || 0}</p>
              </Card>
              <Card className="!p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Send className="w-4 h-4 text-orange-500" />
                  <p className="text-xs text-gray-500">Total Sent</p>
                </div>
                <p className="text-2xl font-bold text-orange-600">{overviewStats.total_devices_sent || 0}</p>
              </Card>
              <Card className="!p-4">
                <div className="flex items-center gap-2 mb-1">
                  <ArrowDownToLine className="w-4 h-4 text-indigo-500" />
                  <p className="text-xs text-gray-500">Transfers</p>
                </div>
                <p className="text-base font-bold text-indigo-600">
                  {overviewStats.total_distributions_received || 0} in / {overviewStats.total_distributions_sent || 0} out
                </p>
              </Card>
            </>
          )}
        </div>
      )}

      {/* Tabs for hierarchy roles */}
      {!loading && hasHierarchy && (
        <div className="flex border-b border-gray-200">
          {[
            { key: 'all', label: `All in Chain (${overviewStats.total_in_chain || 0})` },
            { key: 'mine', label: `In My Hand (${overviewStats.in_my_hand || 0})` },
            { key: 'hierarchy', label: `Under My Hierarchy (${overviewStats.under_subordinates || 0})` },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="ml-3 text-gray-500">Loading devices...</span>
        </div>
      ) : (
        <>
          {/* Color legend */}
          {(replacementMap.replacementIds.size > 0 || replacementMap.defectiveIds.size > 0) && (
            <div className="flex flex-wrap items-center gap-4 px-1 py-2 text-xs text-gray-500">
              <span className="font-medium text-gray-600">Row colours:</span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-emerald-200 border border-emerald-400" />
                Replacement device
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-red-200 border border-red-400" />
                Defective device
              </span>
            </div>
          )}
          <DataTable
            columns={columns}
            data={displayedDevices}
            selectable={canRegister}
            getRowClassName={getRowClassName}
            onRowClick={(row) => {
              setSelectedDevice(row);
              setShowModal(true);
            }}
          />
        </>
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
            {canRegister && (
              <Button variant="secondary" onClick={() => {
                setShowModal(false);
                openEditModal(selectedDevice);
              }}>
                <Edit className="w-4 h-4 mr-2" />
                Edit Device
              </Button>
            )}
            <Link to={`/track-device?serial=${selectedDevice?.serial_number}`}>
              <Button>Track Device</Button>
            </Link>
          </>
        }
      >
        {selectedDevice && (
          <div className="space-y-5">
            {/* Header with status */}
            <div className={`flex items-center gap-4 p-4 rounded-lg ${
              isReplacementDevice ? 'bg-emerald-50 border border-emerald-200' :
              isDefectiveDevice ? 'bg-red-50 border border-red-200' : 'bg-gray-50'
            }`}>
              <div className={`w-16 h-16 rounded-xl flex items-center justify-center ${
                isReplacementDevice ? 'bg-emerald-100' :
                isDefectiveDevice ? 'bg-red-100' : 'bg-blue-100'
              }`}>
                {isDefectiveDevice ? (
                  <AlertTriangle className="w-8 h-8 text-red-600" />
                ) : isReplacementDevice ? (
                  <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                ) : (
                  <Box className="w-8 h-8 text-blue-600" />
                )}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-800">{selectedDevice.model || selectedDevice.device_type}</h3>
                <p className="text-gray-500">{selectedDevice.manufacturer || 'N/A'}</p>
                <div className="flex gap-2 mt-2 flex-wrap">
                  <StatusBadge status={selectedDeviceEffectiveStatus || selectedDevice.status} />
                  {isReplacementDevice && (
                    <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-100 text-emerald-800 rounded-full border border-emerald-300">
                      ✅ Replacement Device
                    </span>
                  )}
                  {isDefectiveDevice && !isReplacementDevice && (
                    <span className="px-2 py-0.5 text-xs font-semibold bg-red-100 text-red-800 rounded-full border border-red-300">
                      🔴 Defective Device
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Core device info */}
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

            {/* Replacement mapping section */}
            {linkedDefect && (
              <div className={`rounded-xl border-2 p-4 space-y-3 ${
                isReplacementDevice ? 'border-emerald-300 bg-emerald-50' : 'border-red-300 bg-red-50'
              }`}>
                <div className="flex items-center gap-2">
                  <Link2 className={`w-4 h-4 flex-shrink-0 ${isReplacementDevice ? 'text-emerald-700' : 'text-red-700'}`} />
                  <p className={`text-sm font-semibold uppercase tracking-wider ${isReplacementDevice ? 'text-emerald-800' : 'text-red-800'}`}>
                    {isReplacementDevice ? 'Replacement Mapping — This is the Replacement Device' : 'Defect Mapping — This Device is Defective'}
                  </p>
                </div>
                <p className="text-xs text-gray-600">
                  Defect Report: <span className="font-semibold">{linkedDefect.report_id}</span> &middot; Status:{' '}
                  <StatusBadge status={linkedDefect.status} size="sm" />
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Defective device box */}
                  <div className="p-3 bg-red-100 border border-red-200 rounded-lg">
                    <p className="text-xs font-semibold text-red-700 uppercase tracking-wider mb-1.5">🔴 Defective Device</p>
                    {linkedDefect.defective_device ? (
                      <>
                        <p className="text-sm font-semibold text-red-900">{linkedDefect.defective_device.device_id}</p>
                        <p className="text-xs text-red-800">Serial: {linkedDefect.defective_device.serial_number}</p>
                        <p className="text-xs text-red-800">MAC: {linkedDefect.defective_device.mac_address}</p>
                        <p className="text-xs text-red-800">Type: {linkedDefect.defective_device.device_type}</p>
                        <p className="text-xs text-red-800">Status: {linkedDefect.defective_device.status}</p>
                      </>
                    ) : (
                      <p className="text-xs text-red-700 italic">Details not available</p>
                    )}
                  </div>

                  {/* Replacement device box */}
                  <div className="p-3 bg-emerald-100 border border-emerald-200 rounded-lg">
                    <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1.5">🟢 Replacement Device</p>
                    {linkedDefect.replacement_device ? (
                      <>
                        <p className="text-sm font-semibold text-emerald-900">{linkedDefect.replacement_device.device_id}</p>
                        <p className="text-xs text-emerald-800">Serial: {linkedDefect.replacement_device.serial_number}</p>
                        <p className="text-xs text-emerald-800">MAC: {linkedDefect.replacement_device.mac_address}</p>
                        <p className="text-xs text-emerald-800">Type: {linkedDefect.replacement_device.device_type}</p>
                        <p className="text-xs text-emerald-800">
                          Status: {linkedDefect.status === 'resolved' ? '✅ Confirmed & Active' : '⏳ Awaiting Confirmation'}
                        </p>
                      </>
                    ) : (
                      <p className="text-xs text-emerald-700 italic">No replacement assigned yet</p>
                    )}
                  </div>
                </div>

                {linkedDefect.resolution && (
                  <p className="text-xs text-gray-600 mt-1 italic">Note: {linkedDefect.resolution}</p>
                )}
              </div>
            )}

            {/* Full payload details */}
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider mb-2 block">All Device Fields</label>
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="max-h-64 overflow-y-auto divide-y divide-gray-100">
                  {Object.entries(selectedDevice)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([key, value]) => {
                      let formattedValue = 'N/A';
                      if (value !== null && value !== undefined && value !== '') {
                        if (typeof value === 'object') {
                          try {
                            formattedValue = JSON.stringify(value);
                          } catch {
                            formattedValue = String(value);
                          }
                        } else {
                          formattedValue = String(value);
                        }
                      }

                      return (
                        <div key={key} className="grid grid-cols-12 gap-2 px-3 py-2 text-xs">
                          <p className="col-span-4 sm:col-span-3 font-semibold text-gray-600 break-all">{key}</p>
                          <p className="col-span-8 sm:col-span-9 text-gray-800 break-all">{formattedValue}</p>
                        </div>
                      );
                    })}
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Edit Device Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedDevice(null);
        }}
        title={isStaff ? 'Request Device Edit (Approval Required)' : 'Edit Device'}
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowEditModal(false)}>Cancel</Button>
            <Button onClick={handleEditSubmit} disabled={editSubmitting}>
              {editSubmitting ? (
                <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Saving...</>
              ) : isStaff ? (
                <><Send className="w-4 h-4 mr-2" /> Submit for Approval</>
              ) : (
                <><Save className="w-4 h-4 mr-2" /> Save Changes</>
              )}
            </Button>
          </>
        }
      >
        {selectedDevice && (
          <div className="space-y-4">
            {/* Staff notice */}
            {isStaff && (
              <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-semibold text-amber-900">Approval Required</p>
                  <p className="text-amber-800 mt-0.5">
                    As a staff member, device edits require approval from a Manager or Admin before they take effect. Your request will be sent for review.
                  </p>
                </div>
              </div>
            )}

            {/* Device reference */}
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Editing Device</p>
              <p className="font-semibold text-gray-800">{selectedDevice.device_id}</p>
              <p className="text-sm text-gray-600">{selectedDevice.device_type} · {selectedDevice.serial_number}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Model
              </label>
              <input
                type="text"
                value={editForm.model}
                onChange={(e) => setEditForm(prev => ({ ...prev, model: e.target.value }))}
                placeholder={selectedDevice.model || 'e.g. EchoLife HG8145'}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Manufacturer
              </label>
              <input
                type="text"
                value={editForm.manufacturer}
                onChange={(e) => setEditForm(prev => ({ ...prev, manufacturer: e.target.value }))}
                placeholder={selectedDevice.manufacturer || 'e.g. Huawei'}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Location
              </label>
              <input
                type="text"
                value={editForm.current_location}
                onChange={(e) => setEditForm(prev => ({ ...prev, current_location: e.target.value }))}
                placeholder={selectedDevice.current_location || 'e.g. Warehouse A'}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {isAdminOrManager && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                ✅ As {user?.role}, your changes will be applied immediately without approval.
              </div>
            )}
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
