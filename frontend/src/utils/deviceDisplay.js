const normalizeType = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'set-top box' || normalized === 'set top box' || normalized === 'sb' || normalized === 'stb') {
    return 'SB';
  }
  return value;
};

export const getDeviceModel = (device) => {
  const directModel = device?.model || device?.device_model || device?.defective_device?.model || device?.replacement_device?.model;
  if (directModel) return directModel;

  // Some APIs send a generic device_name that may duplicate device_type; avoid using type as model text.
  const deviceName = device?.device_name;
  if (deviceName && String(deviceName).toLowerCase() !== String(device?.device_type || '').toLowerCase()) {
    return deviceName;
  }

  return 'Unknown Model';
};

export const getDeviceSerial = (device) => {
  const type = normalizeType(device?.device_type || device?.defective_device?.device_type || '');
  if (type === 'SB') return 'N/A';
  return device?.serial_number || device?.device_serial || device?.defective_device?.serial_number || 'N/A';
};

export const getDeviceMac = (device) => {
  const type = normalizeType(device?.device_type || device?.defective_device?.device_type || '');
  if (type === 'SB') return 'N/A';
  return device?.mac_address || device?.defective_device?.mac_address || 'N/A';
};

export const getDeviceType = (device) =>
  normalizeType(device?.device_type || device?.defective_device?.device_type || 'Unknown Type');

export const getDeviceSelectLabel = (device) => {
  const model = getDeviceModel(device);
  const serial = getDeviceSerial(device);
  const mac = getDeviceMac(device);
  const type = getDeviceType(device);
  return `${model} | SN: ${serial} | MAC: ${mac} | Type: ${type}`;
};
