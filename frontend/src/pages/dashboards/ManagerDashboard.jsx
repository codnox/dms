import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import StatCard from '../../components/ui/StatCard';
import Card from '../../components/ui/Card';
import StatusBadge from '../../components/ui/StatusBadge';
import { dashboardAPI, distributionsAPI, returnsAPI } from '../../services/api';
import {
  Box,
  Truck,
  AlertTriangle,
  RotateCcw,
  CheckSquare,
  BarChart3,
  ArrowRight,
  TrendingUp,
  Loader2
} from 'lucide-react';

const ManagerDashboard = () => {
  const [stats, setStats] = useState({});
  const [distributions, setDistributions] = useState([]);
  const [returnRequests, setReturnRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsRes, distRes, retRes] = await Promise.all([
          dashboardAPI.getStats().catch(() => ({ data: {} })),
          distributionsAPI.getDistributions().catch(() => ({ data: [] })),
          returnsAPI.getReturns().catch(() => ({ data: [] }))
        ]);
        setStats(statsRes.data || {});
        setDistributions(distRes.data || []);
        setReturnRequests(retRes.data || []);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Manager Dashboard</h1>
        <p className="text-gray-500 mt-1">Monitor distribution activities and manage approvals.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard title="Total Devices" value={stats.total_devices || 0} icon={Box} color="blue" />
        <StatCard title="Pending Approvals" value={stats.pending_approvals || 0} icon={CheckSquare} color="yellow" />
        <StatCard title="Defect Reports" value={stats.defect_reports || 0} icon={AlertTriangle} color="red" />
        <StatCard title="Return Requests" value={stats.return_requests || 0} icon={RotateCcw} color="indigo" />
        <StatCard title="This Month" value={stats.distribution_this_month || distributions.length} icon={Truck} color="green" />
        <StatCard title="Resolved" value={stats.resolved_defects || 0} icon={TrendingUp} color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title="Recent Distributions"
          icon={Truck}
          action={
            <Link to="/distributions" className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          }
        >
          <div className="space-y-3">
            {distributions.slice(0, 5).map((dist) => (
              <div key={dist.id} className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-800">{dist.batch_id}</p>
                  <p className="text-xs text-gray-500">{dist.from_name} → {dist.to_name}</p>
                  <p className="text-xs text-gray-400 mt-1">{dist.device_count || dist.device_ids?.length || 0} devices</p>
                </div>
                <StatusBadge status={dist.status} />
              </div>
            ))}
          </div>
        </Card>

        <Card
          title="Pending Returns"
          icon={RotateCcw}
          action={
            <Link to="/returns" className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          }
        >
          <div className="space-y-3">
            {returnRequests.filter(r => r.status !== 'approved').slice(0, 4).map((ret) => (
              <div key={ret.id} className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-800">{ret.device_name || ret.device_type || 'Unknown'}</p>
                  <p className="text-xs text-gray-500">{ret.reason}</p>
                  <p className="text-xs text-gray-400 mt-1">By: {ret.initiated_by_name || 'Unknown'}</p>
                </div>
                <StatusBadge status={ret.status} />
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card
        title="Distribution Analytics"
        icon={BarChart3}
        action={
          <Link to="/reports" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            Full Report
          </Link>
        }
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <p className="text-2xl font-bold text-green-600">
              {distributions.filter(d => d.status === 'approved').length}
            </p>
            <p className="text-sm text-gray-600 mt-1">Approved</p>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <p className="text-2xl font-bold text-yellow-600">
              {distributions.filter(d => d.status === 'pending').length}
            </p>
            <p className="text-sm text-gray-600 mt-1">Pending</p>
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <p className="text-2xl font-bold text-blue-600">
              {distributions.filter(d => d.status === 'in-transit').length}
            </p>
            <p className="text-sm text-gray-600 mt-1">In Transit</p>
          </div>
          <div className="text-center p-4 bg-red-50 rounded-lg">
            <p className="text-2xl font-bold text-red-600">
              {distributions.filter(d => d.status === 'rejected').length}
            </p>
            <p className="text-sm text-gray-600 mt-1">Rejected</p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ManagerDashboard;
