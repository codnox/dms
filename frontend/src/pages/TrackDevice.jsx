import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import StatusBadge from '../components/ui/StatusBadge';
import Timeline from '../components/ui/Timeline';
import Button from '../components/ui/Button';
import { devicesAPI } from '../services/api';
import { Search, Box, MapPin, Clock, User, Download, ChevronRight, Loader2 } from 'lucide-react';

const TrackDevice = () => {
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || searchParams.get('mac') || searchParams.get('serial') || '';
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [searchResult, setSearchResult] = useState(null);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [allDevices, setAllDevices] = useState([]);
  const [devicesLoading, setDevicesLoading] = useState(true);
  const [deviceHistory, setDeviceHistory] = useState([]);

  // Fetch all devices on mount
  useEffect(() => {
    fetchAllDevices();
  }, []);

  // Auto-search if query param is present
  useEffect(() => {
    if (initialQuery) {
      handleSearchBySerial(initialQuery);
    }
  }, []);

  const fetchAllDevices = async () => {
    try {
      setDevicesLoading(true);
      const response = await devicesAPI.getDevices({ page_size: 100 });
      setAllDevices(response.data || []);
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    } finally {
      setDevicesLoading(false);
    }
  };

  const handleSearchBySerial = async (serialOrMac) => {
    setLoading(true);
    setSearched(true);
    try {
      const response = await devicesAPI.trackDeviceBySerial(serialOrMac);
      if (response.success && response.data) {
        setSearchResult(response.data);
        setDeviceHistory(response.data.history || []);
      } else {
        setSearchResult(null);
        setDeviceHistory([]);
      }
    } catch (error) {
      console.error('Device not found:', error);
      setSearchResult(null);
      setDeviceHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    await handleSearchBySerial(searchQuery.trim());
  };

  const handleDeviceClick = async (device) => {
    setSearchQuery(device.serial_number);
    await handleSearchBySerial(device.serial_number);
  };

  const getFormattedHistory = () => {
    if (!deviceHistory || deviceHistory.length === 0) return [];
    return deviceHistory.map((item, index) => ({
      title: (item.action || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      description: item.notes || '',
      timestamp: item.timestamp ? new Date(item.timestamp).toLocaleString() : '',
      user: item.performed_by_name || '',
      status: index === 0 ? 'current' : 'completed'
    }));
  };

  const getLocationColor = (location) => {
    if (!location) return 'bg-gray-100 text-gray-800';
    const loc = location.toLowerCase();
    if (loc.includes('noc')) return 'bg-blue-100 text-blue-800';
    if (loc.includes('distributor')) return 'bg-purple-100 text-purple-800';
    if (loc.includes('operator')) return 'bg-green-100 text-green-800';
    if (loc.includes('transit')) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  const getHolderType = (type) => {
    if (!type) return 'Unknown';
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Track Device</h1>
        <p className="text-gray-500 mt-1">Search and track device journey through the distribution chain</p>
      </div>

      {/* Search Form */}
      <Card>
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Enter serial number to track device..."
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <Button type="submit" size="lg" disabled={loading}>
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Track Device'}
          </Button>
        </form>
      </Card>

      {/* All Devices List */}
      {!searched && (
        <Card title="All Devices" icon={Box}>
          {devicesLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
              <span className="ml-3 text-gray-500">Loading devices...</span>
            </div>
          ) : allDevices.length === 0 ? (
            <div className="text-center py-12">
              <Box className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-800 mb-2">No Devices Found</h3>
              <p className="text-gray-500">No devices have been registered yet. Register a device first to start tracking.</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-gray-500 mb-4">Click on a device to view its tracking history</p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {allDevices.map((device) => (
                  <div
                    key={device.id}
                    onClick={() => handleDeviceClick(device)}
                    className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-all"
                  >
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Box className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 truncate">{device.model || 'Unknown Model'}</p>
                      <p className="text-xs text-gray-500 font-mono truncate">{device.serial_number}</p>
                      <p className="text-xs text-gray-400 truncate">{device.mac_address}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <StatusBadge status={device.status} size="sm" />
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Search Results */}
      {searched && (
        <>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
              <span className="ml-3 text-gray-500">Tracking device...</span>
            </div>
          ) : searchResult ? (
            <div className="space-y-6">
              {/* Back to all devices */}
              <button
                onClick={() => { setSearched(false); setSearchResult(null); setSearchQuery(''); }}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                ← Back to all devices
              </button>

              {/* Device Info Card */}
              <Card>
                <div className="flex flex-col lg:flex-row lg:items-start gap-6">
                  <div className="flex items-center gap-4">
                    <div className="w-20 h-20 bg-blue-100 rounded-xl flex items-center justify-center">
                      <Box className="w-10 h-10 text-blue-600" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-gray-800">{searchResult.model || 'Unknown Model'}</h2>
                      <p className="text-gray-500">{searchResult.manufacturer || searchResult.device_type}</p>
                      <div className="flex gap-2 mt-2">
                        <StatusBadge status={searchResult.status} />
                      </div>
                    </div>
                  </div>

                  <div className="flex-1 grid grid-cols-2 lg:grid-cols-4 gap-4 lg:border-l lg:border-gray-200 lg:pl-6">
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wider">MAC Address</p>
                      <p className="font-mono font-medium text-gray-800">{searchResult.mac_address}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wider">Serial Number</p>
                      <p className="font-medium text-gray-800">{searchResult.serial_number}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wider">Device Type</p>
                      <p className="font-medium text-gray-800">{searchResult.device_type}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wider">Device ID</p>
                      <p className="font-medium text-gray-800">{searchResult.device_id}</p>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Current Location & Journey */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="lg:col-span-1">
                  <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <MapPin className="w-5 h-5 text-gray-500" />
                    Current Location
                  </h3>
                  <div className={`p-4 rounded-lg ${getLocationColor(searchResult.current_location)}`}>
                    <p className="text-sm font-medium uppercase tracking-wider opacity-75">
                      {getHolderType(searchResult.current_holder_type)}
                    </p>
                    <p className="text-lg font-bold mt-1">
                      {searchResult.current_holder_name || searchResult.current_location || 'NOC'}
                    </p>
                  </div>

                  <div className="mt-4 space-y-3">
                    <div className="flex items-center gap-3 text-sm">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-600">
                        Registered: {searchResult.created_at ? new Date(searchResult.created_at).toLocaleDateString() : 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <MapPin className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-600">Location: {searchResult.current_location || 'NOC'}</span>
                    </div>
                  </div>
                </Card>

                {/* Device Journey */}
                <Card className="lg:col-span-2">
                  <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <Clock className="w-5 h-5 text-gray-500" />
                    Device Journey
                  </h3>
                  
                  {deviceHistory.length > 0 ? (
                    <Timeline items={getFormattedHistory()} />
                  ) : (
                    <div className="text-center py-8">
                      <Clock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500">No journey history available for this device</p>
                    </div>
                  )}
                </Card>
              </div>

              {/* Distribution Flow */}
              <Card title="Distribution Flow">
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 py-4">
                  <div className={`text-center ${searchResult.current_location === 'NOC' ? 'ring-2 ring-blue-500 rounded-lg p-2' : ''}`}>
                    <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto">
                      <Box className="w-8 h-8 text-blue-600" />
                    </div>
                    <p className="text-sm font-medium text-gray-800 mt-2">NOC</p>
                    <p className="text-xs text-gray-500">Source</p>
                  </div>
                  
                  <ChevronRight className="w-6 h-6 text-gray-300 rotate-90 sm:rotate-0" />
                  
                  <div className={`text-center ${searchResult.current_holder_type === 'distributor' ? 'ring-2 ring-blue-500 rounded-lg p-2' : ''}`}>
                    <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto">
                      <Box className="w-8 h-8 text-indigo-600" />
                    </div>
                    <p className="text-sm font-medium text-gray-800 mt-2">Distributor</p>
                    <p className="text-xs text-gray-500">Distribution</p>
                  </div>
                  
                  <ChevronRight className="w-6 h-6 text-gray-300 rotate-90 sm:rotate-0" />
                  
                  <div className={`text-center ${searchResult.current_holder_type === 'sub_distributor' ? 'ring-2 ring-blue-500 rounded-lg p-2' : ''}`}>
                    <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto">
                      <Box className="w-8 h-8 text-purple-600" />
                    </div>
                    <p className="text-sm font-medium text-gray-800 mt-2">Sub Dist.</p>
                    <p className="text-xs text-gray-500">Regional</p>
                  </div>
                  
                  <ChevronRight className="w-6 h-6 text-gray-300 rotate-90 sm:rotate-0" />
                  
                  <div className={`text-center ${searchResult.current_holder_type === 'operator' ? 'ring-2 ring-blue-500 rounded-lg p-2' : ''}`}>
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                      <User className="w-8 h-8 text-green-600" />
                    </div>
                    <p className="text-sm font-medium text-gray-800 mt-2">Operator</p>
                    <p className="text-xs text-gray-500">End User</p>
                  </div>
                </div>
              </Card>
            </div>
          ) : (
            <div>
              <button
                onClick={() => { setSearched(false); setSearchResult(null); setSearchQuery(''); }}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1 mb-4"
              >
                ← Back to all devices
              </button>
              <Card>
                <div className="text-center py-12">
                  <Box className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-800 mb-2">No Device Found</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    We couldn't find a device matching "{searchQuery}". Please check the serial number and try again.
                  </p>
                </div>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default TrackDevice;
