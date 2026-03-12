import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import StatusBadge from '../components/ui/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { devicesAPI, usersAPI, distributionsAPI } from '../services/api';
import { Truck, Save, X, Plus, Trash2, Search, Loader2, ChevronRight } from 'lucide-react';

const ROLE_LABELS = {
  sub_distributor: 'Sub Distributor',
  cluster: 'Cluster',
  operator: 'Operator',
};

// Recipient types each sender role is allowed to pick
const ALLOWED_RECIPIENT_TYPES = {
  admin:           ['sub_distributor', 'cluster', 'operator'],
  manager:         ['sub_distributor', 'cluster', 'operator'],
  staff:           ['sub_distributor', 'cluster', 'operator'],
  sub_distributor: ['cluster', 'operator'],
  cluster:         ['operator'],
  operator:        ['operator'],
};

const CreateDistribution = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useNotifications();
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDevices, setSelectedDevices] = useState([]);
  const [availableDevices, setAvailableDevices] = useState([]);
  const [loadingData, setLoadingData] = useState(true);

  // Cascading recipient state
  const [subDists, setSubDists] = useState([]);
  const [allClusters, setAllClusters] = useState([]);
  const [allOperators, setAllOperators] = useState([]);
  const [recipientType, setRecipientType] = useState('');
  const [filterSubDistId, setFilterSubDistId] = useState('');
  const [filterClusterId, setFilterClusterId] = useState('');
  const [formData, setFormData] = useState({ toDistributor: '', notes: '' });

  const role = user?.role;
  const isManagement = ['admin', 'manager', 'staff'].includes(role);
  const allowedTypes = ALLOWED_RECIPIENT_TYPES[role] || [];

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoadingData(true);
        // Devices: management sees PDIC stock; others see devices they currently hold
        const devicesRes = await devicesAPI.getAvailableDevices().catch(() => ({ data: [] }));
        setAvailableDevices(devicesRes.data || []);

        if (isManagement) {
          const [sdRes, clRes, opRes] = await Promise.all([
            usersAPI.getUsers({ role: 'sub_distributor', status: 'active', page_size: 500 }).catch(() => ({ data: [] })),
            usersAPI.getUsers({ role: 'cluster',        status: 'active', page_size: 500 }).catch(() => ({ data: [] })),
            usersAPI.getUsers({ role: 'operator',       status: 'active', page_size: 500 }).catch(() => ({ data: [] })),
          ]);
          setSubDists(sdRes.data || []);
          setAllClusters(clRes.data || []);
          setAllOperators(opRes.data || []);
        } else if (role === 'sub_distributor') {
          const [clRes, opRes] = await Promise.all([
            usersAPI.getUsers({ role: 'cluster',  status: 'active', page_size: 500 }).catch(() => ({ data: [] })),
            usersAPI.getUsers({ role: 'operator', status: 'active', page_size: 500 }).catch(() => ({ data: [] })),
          ]);
          setAllClusters(clRes.data || []);
          setAllOperators(opRes.data || []);
        } else if (role === 'cluster') {
          const opRes = await usersAPI.getUsers({ role: 'operator', status: 'active', page_size: 500 }).catch(() => ({ data: [] }));
          setAllOperators(opRes.data || []);
        } else if (role === 'operator') {
          // Backend returns only sibling operators (same parent_id); exclude self
          const opRes = await usersAPI.getUsers({ role: 'operator', status: 'active', page_size: 500 }).catch(() => ({ data: [] }));
          setAllOperators((opRes.data || []).filter(o => String(o.id) !== String(user?.id)));
        }
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        setLoadingData(false);
      }
    };
    if (role) fetchData();
  }, [role]);

  const handleRecipientTypeChange = (type) => {
    setRecipientType(type);
    setFilterSubDistId('');
    setFilterClusterId('');
    setFormData(p => ({ ...p, toDistributor: '' }));
  };

  // Clusters shown in the cluster filter dropdown
  const visibleClusters = useMemo(() => {
    if (isManagement) {
      return filterSubDistId ? allClusters.filter(c => String(c.parent_id) === filterSubDistId) : allClusters;
    }
    return allClusters; // already scoped by backend for sub_distributor
  }, [allClusters, filterSubDistId, isManagement]);

  // Operators shown in the final recipient list when type = 'operator'
  const visibleOperators = useMemo(() => {
    if (filterClusterId) return allOperators.filter(o => String(o.parent_id) === filterClusterId);
    if (isManagement && filterSubDistId) {
      const clusterIds = new Set(allClusters.filter(c => String(c.parent_id) === filterSubDistId).map(c => String(c.id)));
      return allOperators.filter(o => clusterIds.has(String(o.parent_id)));
    }
    return allOperators;
  }, [allOperators, allClusters, filterSubDistId, filterClusterId, isManagement]);

  const finalRecipients = useMemo(() => {
    if (recipientType === 'sub_distributor') return subDists;
    if (recipientType === 'cluster') return visibleClusters;
    if (recipientType === 'operator') return visibleOperators;
    return [];
  }, [recipientType, subDists, visibleClusters, visibleOperators]);

  const selectedRecipient = useMemo(() => {
    if (!formData.toDistributor) return null;
    return [...subDists, ...allClusters, ...allOperators].find(u => String(u.id) === String(formData.toDistributor));
  }, [formData.toDistributor, subDists, allClusters, allOperators]);

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
    if (selectedDevices.length === 0) { showToast('Please select at least one device', 'error'); return; }
    if (!formData.toDistributor) { showToast('Please select a recipient', 'error'); return; }
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

  const pageSubtitle = isManagement
    ? 'Distribute devices from PDIC stock to sub-distributors, clusters, or operators'
    : role === 'sub_distributor' ? 'Distribute your devices to clusters or operators under you'
    : role === 'cluster'         ? 'Distribute your devices to operators under your cluster'
    : 'Transfer a device to another operator in your cluster';

  const currentType = recipientType || (allowedTypes.length === 1 ? allowedTypes[0] : '');

  // Auto-select the only allowed type if there is exactly one
  useEffect(() => {
    if (allowedTypes.length === 1 && recipientType !== allowedTypes[0]) {
      setRecipientType(allowedTypes[0]);
    }
  }, [allowedTypes, recipientType]);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Create Distribution</h1>
        <p className="text-gray-500 mt-1 text-sm sm:text-base">{pageSubtitle}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {/* Available / Held Devices */}
          <Card title={isManagement ? 'PDIC Available Devices' : 'Your Held Devices'} icon={Search}>
            <div className="space-y-4">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by MAC, model, or serial..."
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <div className="max-h-80 overflow-y-auto space-y-2">
                {loadingData ? (
                  <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-blue-500" /></div>
                ) : filteredDevices.length === 0 ? (
                  <p className="text-center text-gray-500 py-4">
                    {isManagement ? 'No devices available in PDIC stock' : 'You have no devices in your possession'}
                  </p>
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
                        <p className="text-xs text-gray-400">{device.serial_number}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={device.status} size="sm" />
                        <button type="button" onClick={(e) => { e.stopPropagation(); handleAddDevice(device); }} className="p-1 text-blue-600 hover:bg-blue-100 rounded">
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
            <div className="max-h-80 overflow-y-auto space-y-2">
              {selectedDevices.length === 0 ? (
                <p className="text-center text-gray-500 py-8">Click on devices to add them</p>
              ) : (
                selectedDevices.map(device => (
                  <div key={device._id || device.id} className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-800">{device.model || device.device_type}</p>
                      <p className="text-sm text-gray-500">{device.mac_address}</p>
                    </div>
                    <button type="button" onClick={() => handleRemoveDevice(device._id || device.id)} className="p-1 text-red-600 hover:bg-red-100 rounded">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Recipient Selector */}
        <Card title="Select Recipient">
          <div className="space-y-4">

            {/* Recipient Type selector — only shown when there are multiple options */}
            {allowedTypes.length > 1 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Recipient Type <span className="text-red-500">*</span>
                </label>
                <div className="flex flex-wrap gap-3">
                  {allowedTypes.map(type => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => handleRecipientTypeChange(type)}
                      className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
                        recipientType === type
                          ? type === 'sub_distributor' ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : type === 'cluster'         ? 'border-teal-500 bg-teal-50 text-teal-700'
                                                       : 'border-green-500 bg-green-50 text-green-700'
                          : 'border-gray-200 text-gray-600 hover:border-gray-400'
                      }`}
                    >
                      {ROLE_LABELS[type]}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Sub-Distributor filter — management only, when distributing to cluster/operator */}
            {isManagement && (currentType === 'cluster' || currentType === 'operator') && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Filter by Sub-Distributor
                  <span className="text-xs text-gray-400 ml-2">(optional)</span>
                </label>
                <select
                  value={filterSubDistId}
                  onChange={e => { setFilterSubDistId(e.target.value); setFilterClusterId(''); setFormData(p => ({ ...p, toDistributor: '' })); }}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Sub-Distributors</option>
                  {subDists.map(sd => (
                    <option key={sd.id} value={String(sd.id)}>{sd.name}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Cluster filter — for distributing to operators (management & sub_distributor) */}
            {currentType === 'operator' && (isManagement || role === 'sub_distributor') && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Filter by Cluster
                  <span className="text-xs text-gray-400 ml-2">
                    (optional — {visibleClusters.length} cluster{visibleClusters.length !== 1 ? 's' : ''})
                  </span>
                </label>
                <select
                  value={filterClusterId}
                  onChange={e => { setFilterClusterId(e.target.value); setFormData(p => ({ ...p, toDistributor: '' })); }}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Clusters</option>
                  {visibleClusters.map(c => (
                    <option key={c.id} value={String(c.id)}>
                      {c.name} ({allOperators.filter(o => String(o.parent_id) === String(c.id)).length} operators)
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Final recipient select */}
            {currentType && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Select {ROLE_LABELS[currentType]}
                  <span className="text-red-500"> *</span>
                  <span className="text-xs text-gray-400 ml-2">({finalRecipients.length} available)</span>
                </label>
                {finalRecipients.length === 0 ? (
                  <p className="text-sm text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
                    No {ROLE_LABELS[currentType].toLowerCase()}s found
                    {filterClusterId || filterSubDistId ? ' matching the selected filter.' : '.'}
                  </p>
                ) : (
                  <select
                    value={formData.toDistributor}
                    onChange={e => setFormData(p => ({ ...p, toDistributor: e.target.value }))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    <option value="">Select {ROLE_LABELS[currentType]}…</option>
                    {finalRecipients.map(r => (
                      <option key={r._id || r.id} value={r._id || r.id}>{r.name}</option>
                    ))}
                  </select>
                )}
              </div>
            )}

            {/* Breadcrumb — shows the hierarchy path to the selected recipient */}
            {selectedRecipient && (
              <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg text-sm flex-wrap">
                {selectedRecipient.role === 'cluster' && (() => {
                  const sd = subDists.find(s => String(s.id) === String(selectedRecipient.parent_id));
                  return sd
                    ? <><span className="px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 font-medium">{sd.name}</span><ChevronRight className="w-4 h-4 text-gray-400" /></>
                    : null;
                })()}
                {selectedRecipient.role === 'operator' && (() => {
                  const cl = allClusters.find(c => String(c.id) === String(selectedRecipient.parent_id));
                  const sd = cl ? subDists.find(s => String(s.id) === String(cl.parent_id)) : null;
                  const clOperatorCount = cl ? allOperators.filter(o => String(o.parent_id) === String(cl.id)).length : 0;
                  return (
                    <>
                      {sd && <><span className="px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 font-medium">{sd.name}</span><ChevronRight className="w-4 h-4 text-gray-400" /></>}
                      {cl && <><span className="px-2 py-0.5 rounded bg-teal-100 text-teal-700 font-medium">{cl.name} ({clOperatorCount} operators)</span><ChevronRight className="w-4 h-4 text-gray-400" /></>}
                    </>
                  );
                })()}
                <span className={`px-2 py-0.5 rounded font-semibold ${
                  selectedRecipient.role === 'sub_distributor' ? 'bg-indigo-100 text-indigo-800' :
                  selectedRecipient.role === 'cluster'         ? 'bg-teal-100 text-teal-800' :
                                                                 'bg-green-100 text-green-800'
                }`}>{selectedRecipient.name}</span>
                <StatusBadge status={selectedRecipient.status} size="sm" />
              </div>
            )}
          </div>
        </Card>

        {/* Notes */}
        <Card title="Notes">
          <textarea
            value={formData.notes}
            onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
            rows={3}
            placeholder="Add any notes for this distribution..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </Card>

        {/* Distribution Summary */}
        {selectedDevices.length > 0 && selectedRecipient && (
          <Card className="bg-blue-50 border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-blue-800">Distribution Summary</p>
                <p className="text-sm text-blue-600">
                  {selectedDevices.length} device(s) will be transferred to {selectedRecipient.name} ({ROLE_LABELS[selectedRecipient.role] || selectedRecipient.role})
                </p>
                <p className="text-xs text-blue-500 mt-0.5">
                  Device status will become <strong>{selectedRecipient.role === 'operator' ? 'In Use' : 'Distributed'}</strong> immediately
                </p>
              </div>
              <Truck className="w-8 h-8 text-blue-600 flex-shrink-0" />
            </div>
          </Card>
        )}

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-3">
          <Button variant="secondary" onClick={() => navigate('/distributions')} icon={X} className="w-full sm:w-auto">Cancel</Button>
          <Button type="submit" loading={loading} icon={Save} className="w-full sm:w-auto">Create Distribution</Button>
        </div>
      </form>
    </div>
  );
};

export default CreateDistribution;
