import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import StatusBadge from '../components/ui/StatusBadge';
import { useNotifications } from '../context/NotificationContext';
import { devicesAPI, defectsAPI, returnsAPI } from '../services/api';
import { RotateCcw, Save, X, AlertTriangle, Link as LinkIcon } from 'lucide-react';

const CreateReturn = () => {
  const navigate = useNavigate();
  const { showToast } = useNotifications();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    deviceId: '',
    reason: '',
    defectReportId: '',
    requestedAction: '',
    notes: ''
  });

  const [returnableDevices, setReturnableDevices] = useState([]);
  const [defectReports, setDefectReports] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [devicesRes, defectsRes] = await Promise.all([
          devicesAPI.getDevices().catch(() => ({ data: [] })),
          defectsAPI.getDefects().catch(() => ({ data: [] }))
        ]);
        setReturnableDevices(devicesRes.data || []);
        setDefectReports(defectsRes.data || []);
      } catch (error) {
        console.error('Failed to load data:', error);
      }
    };
    fetchData();
  }, []);

  // Related defect reports for selected device
  const relatedDefects = defectReports.filter(d => d.device_id === formData.deviceId);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await returnsAPI.createReturn({
        device_id: formData.deviceId,
        reason: formData.reason,
        defect_report_id: formData.defectReportId || undefined,
        requested_action: formData.requestedAction,
        notes: formData.notes
      });
      showToast('Return request submitted successfully!', 'success');
      navigate('/returns');
    } catch (error) {
      showToast(error.message || 'Failed to submit return request', 'error');
    } finally {
      setLoading(false);
    }
  };

  const selectedDevice = returnableDevices.find(d => (d._id || d.id) === formData.deviceId);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Initiate Return</h1>
        <p className="text-gray-500 mt-1">Submit a return request for a device</p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Device Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Device <span className="text-red-500">*</span>
            </label>
            <select
              name="deviceId"
              value={formData.deviceId}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select a device...</option>
              {returnableDevices.map(device => (
                <option key={device._id || device.id} value={device._id || device.id}>
                  {device.model || device.device_type} - {device.mac_address}
                </option>
              ))}
            </select>
          </div>

          {/* Selected Device Info */}
          {selectedDevice && (
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <RotateCcw className="w-6 h-6 text-orange-600" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{selectedDevice.model || selectedDevice.device_type}</p>
                  <p className="text-sm text-gray-500">MAC: {selectedDevice.mac_address}</p>
                  <p className="text-sm text-gray-500">SN: {selectedDevice.serial_number}</p>
                </div>
                <StatusBadge status={selectedDevice.status} />
              </div>
            </div>
          )}

          {/* Return Reason */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Return Reason <span className="text-red-500">*</span>
            </label>
            <select
              name="reason"
              value={formData.reason}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select reason...</option>
              <option value="Defective device">Defective device</option>
              <option value="Wrong device received">Wrong device received</option>
              <option value="Excess inventory">Excess inventory</option>
              <option value="Customer cancellation">Customer cancellation</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {/* Link Defect Report */}
          {formData.reason === 'Defective device' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Link Defect Report
              </label>
              <select
                name="defectReportId"
                value={formData.defectReportId}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select defect report (optional)...</option>
                {relatedDefects.map(defect => (
                  <option key={defect._id || defect.id} value={defect._id || defect.id}>
                    {defect.defect_type} - {defect.severity} ({defect.created_at ? new Date(defect.created_at).toLocaleDateString() : ''})
                  </option>
                ))}
              </select>
              {relatedDefects.length === 0 && formData.deviceId && (
                <p className="text-sm text-gray-500 mt-1">
                  No defect reports found for this device. 
                  <button 
                    type="button"
                    onClick={() => navigate('/defects/create')}
                    className="text-blue-600 hover:text-blue-700 ml-1"
                  >
                    Report a defect first
                  </button>
                </p>
              )}
            </div>
          )}

          {/* Requested Action */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Requested Action <span className="text-red-500">*</span>
            </label>
            <select
              name="requestedAction"
              value={formData.requestedAction}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select action...</option>
              <option value="Replace">Replace with new device</option>
              <option value="Repair">Repair and return</option>
              <option value="Refund">Refund/Credit</option>
            </select>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Additional Notes
            </label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              rows={4}
              placeholder="Provide any additional details about the return..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Info Banner */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-blue-800">Return Tracking Process</p>
              <p className="text-sm text-blue-600 mt-1">
                Your return request will appear in Returns for PDIC device-reached confirmation.
                You can track the status from the Returns page.
              </p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <Button variant="secondary" onClick={() => navigate('/returns')} icon={X}>
              Cancel
            </Button>
            <Button type="submit" loading={loading} icon={Save}>
              Submit Return Request
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};

export default CreateReturn;
