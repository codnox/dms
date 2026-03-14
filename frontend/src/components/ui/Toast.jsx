import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

const Toast = ({ message, type = 'success', onClose }) => {
  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-500" />,
    error: <XCircle className="w-5 h-5 text-red-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />,
  };

  const bgColors = {
    success: 'bg-emerald-900/45 border-emerald-400/35',
    error: 'bg-rose-900/45 border-rose-400/35',
    warning: 'bg-amber-900/45 border-amber-400/35',
    info: 'bg-cyan-900/45 border-cyan-400/35',
  };

  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg backdrop-blur animate-slideIn ${bgColors[type]}`}>
      {icons[type]}
      <p className="text-sm text-slate-100">{message}</p>
    </div>
  );
};

export default Toast;
