const StatusBadge = ({ status, size = 'md' }) => {
  const statusConfig = {
    // Device statuses
    'active': { bg: 'bg-green-100/30', text: 'text-green-300', label: 'Active' },
    'inactive': { bg: 'bg-gray-100/30', text: 'text-gray-300', label: 'Inactive' },
    'in-use': { bg: 'bg-blue-100/30', text: 'text-blue-300', label: 'In Use' },
    'stored': { bg: 'bg-purple-100/30', text: 'text-purple-300', label: 'Stored' },
    'defective': { bg: 'bg-red-100/30', text: 'text-red-300', label: 'Defective' },
    'replaced': { bg: 'bg-gray-200', text: 'text-gray-700 line-through', label: 'Replaced' },
    'returned': { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Returned' },
    
    // Distribution statuses
    'pending': { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Pending' },
    'pending_receipt': { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Awaiting Receipt' },
    'disputed': { bg: 'bg-red-100', text: 'text-red-700', label: 'Disputed' },
    'in-transit': { bg: 'bg-blue-100', text: 'text-blue-700', label: 'In Transit' },
    'delivered': { bg: 'bg-indigo-100', text: 'text-indigo-700', label: 'Delivered' },
    'approved': { bg: 'bg-green-100', text: 'text-green-700', label: 'Confirmed' },
    'replacement_pending_confirmation': { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Pending Confirmation' },
    'replacement_waiting_for_device': { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Waiting For Device' },
    'rejected': { bg: 'bg-red-100', text: 'text-red-700', label: 'Rejected' },
    'completed': { bg: 'bg-green-100', text: 'text-green-700', label: 'Completed' },
    'cancelled': { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Cancelled' },
    
    // Defect/Return statuses
    'open': { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Open' },
    'under-review': { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Under Review' },
    'resolved': { bg: 'bg-green-100', text: 'text-green-700', label: 'Resolved' },
    'closed': { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Closed' },
    
    // Severity
    'critical': { bg: 'bg-red-100', text: 'text-red-700', label: 'Critical' },
    'high': { bg: 'bg-orange-100', text: 'text-orange-700', label: 'High' },
    'medium': { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Medium' },
    'low': { bg: 'bg-green-100', text: 'text-green-700', label: 'Low' },
    
    // Condition
    'new': { bg: 'bg-green-100', text: 'text-green-700', label: 'New' },
    'refurbished': { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Refurbished' },

    // Replacement relation
    'replacement': { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Replacement Device' },
    'defective_device': { bg: 'bg-red-100', text: 'text-red-700', label: 'Defective Device' },
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  };

  const config = statusConfig[status?.toLowerCase()] || {
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    label: status || 'Unknown'
  };

  return (
    <span className={`inline-flex items-center font-medium rounded-full ${config.bg} ${config.text} ${sizeClasses[size]}`}>
      {config.label}
    </span>
  );
};

export default StatusBadge;
