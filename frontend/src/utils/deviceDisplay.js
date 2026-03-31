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

export const getDeviceSerial = (device) =>
  device?.serial_number || device?.device_serial || device?.defective_device?.serial_number || 'N/A';

export const getDeviceMac = (device) =>
  device?.mac_address || device?.defective_device?.mac_address || 'N/A';

export const getDeviceType = (device) =>
  device?.device_type || device?.defective_device?.device_type || 'Unknown Type';

export const getDeviceSelectLabel = (device) => {
  const model = getDeviceModel(device);
  const serial = getDeviceSerial(device);
  const mac = getDeviceMac(device);
  const type = getDeviceType(device);
  return `${model} | SN: ${serial} | MAC: ${mac} | Type: ${type}`;
};
