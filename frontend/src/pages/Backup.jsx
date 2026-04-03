import { useState } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { reportsAPI } from '../services/api';
import { useNotifications } from '../context/NotificationContext';
import { Download, Database, FileSpreadsheet, FileText } from 'lucide-react';

const Backup = () => {
  const { showToast } = useNotifications();
  const [format, setFormat] = useState('xlsx');
  const [downloadingDevices, setDownloadingDevices] = useState(false);
  const [downloadingTracking, setDownloadingTracking] = useState(false);

  const extractFilename = (contentDisposition, fallback) => {
    const match = /filename="?([^\";]+)"?/i.exec(contentDisposition || '');
    return (match && match[1]) || fallback;
  };

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleDeviceBackupDownload = async () => {
    setDownloadingDevices(true);
    try {
      const { blob, contentDisposition } = await reportsAPI.downloadDeviceBackup(format);
      const fallbackName = `device-backup.${format}`;
      const fileName = extractFilename(contentDisposition, fallbackName);
      downloadBlob(blob, fileName);

      showToast('Backup generated and downloaded successfully', 'success');
    } catch (error) {
      showToast(error.message || 'Failed to download backup', 'error');
    } finally {
      setDownloadingDevices(false);
    }
  };

  const handleTrackingBackupDownload = async () => {
    setDownloadingTracking(true);
    try {
      const { blob, contentDisposition } = await reportsAPI.downloadReturnsDefectsBackup(format);
      const fallbackName = `returns-defects-backup.${format}`;
      const fileName = extractFilename(contentDisposition, fallbackName);
      downloadBlob(blob, fileName);

      showToast('Returns and defects backup downloaded successfully', 'success');
    } catch (error) {
      showToast(error.message || 'Failed to download returns/defects backup', 'error');
    } finally {
      setDownloadingTracking(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-gray-800">Backup</h1>
        <p className="text-gray-500">
          Download a full backup of all devices including journey path from source to current location.
        </p>
      </div>

      <Card>
        <div className="space-y-5">
          <div className="flex items-start gap-3 text-gray-700">
            <Database className="w-5 h-5 mt-0.5 text-blue-600" />
            <div>
              <p className="font-medium">Included in backup</p>
              <p className="text-sm text-gray-500 mt-1">
                Device details, starting point, path traversed through hierarchy levels, and current location.
              </p>
            </div>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">File format</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setFormat('xlsx')}
                className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                  format === 'xlsx'
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                }`}
              >
                <FileSpreadsheet className="w-4 h-4" />
                XLSX
              </button>
              <button
                type="button"
                onClick={() => setFormat('csv')}
                className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                  format === 'csv'
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                }`}
              >
                <FileText className="w-4 h-4" />
                CSV
              </button>
            </div>
          </div>

          <div className="pt-2">
            <Button icon={Download} loading={downloadingDevices} onClick={handleDeviceBackupDownload}>
              {downloadingDevices ? 'Generating Device Backup...' : 'Download Device Backup'}
            </Button>
          </div>
        </div>
      </Card>

      <Card>
        <div className="space-y-5">
          <div className="flex items-start gap-3 text-gray-700">
            <Database className="w-5 h-5 mt-0.5 text-orange-600" />
            <div>
              <p className="font-medium">Returns and defects tracking backup</p>
              <p className="text-sm text-gray-500 mt-1">
                Downloads a separate file containing all return records and defect reports for audit and tracking.
              </p>
            </div>
          </div>

          <div className="pt-2">
            <Button icon={Download} loading={downloadingTracking} onClick={handleTrackingBackupDownload}>
              {downloadingTracking ? 'Generating Tracking Backup...' : 'Download Returns + Defects Backup'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Backup;
