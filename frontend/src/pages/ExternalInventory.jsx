import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import DataTable from '../components/ui/DataTable';
import { externalInventoryAPI } from '../services/api';
import { useNotifications } from '../context/NotificationContext';
import {
  AlertTriangle,
  Boxes,
  ClipboardCheck,
  DollarSign,
  Factory,
  PackagePlus,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';

const initialItemForm = {
  sku: '',
  name: '',
  category: '',
  unit: 'pcs',
  quantity_on_hand: 0,
  reorder_level: 0,
  unit_cost: 0,
  supplier_name: '',
  location: '',
  notes: '',
};

const ExternalInventory = () => {
  const { showToast } = useNotifications();

  const [dashboard, setDashboard] = useState(null);
  const [items, setItems] = useState([]);
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [movements, setMovements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [showAddItemModal, setShowAddItemModal] = useState(false);
  const [showCreatePOModal, setShowCreatePOModal] = useState(false);
  const [receivingPO, setReceivingPO] = useState(null);

  const [itemForm, setItemForm] = useState(initialItemForm);

  const [poForm, setPoForm] = useState({
    supplier_name: '',
    expected_date: '',
    notes: '',
    lines: [{ item_inventory_id: '', quantity_ordered: 1, unit_cost: 0 }],
  });

  const [receiptForm, setReceiptForm] = useState({
    notes: '',
    lines: [],
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [dashboardRes, itemsRes, poRes, movementRes] = await Promise.all([
        externalInventoryAPI.getDashboard(),
        externalInventoryAPI.getItems({ page_size: 100 }),
        externalInventoryAPI.getPurchaseOrders({ page_size: 50 }),
        externalInventoryAPI.getMovements({ page_size: 50 }),
      ]);

      setDashboard(dashboardRes.data || null);
      setItems(itemsRes.data || []);
      setPurchaseOrders(poRes.data || []);
      setMovements(movementRes.data || []);
    } catch (error) {
      showToast(error.message || 'Failed to load external inventory data', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const lowStockItems = useMemo(
    () => items.filter((item) => Number(item.quantity_on_hand) <= Number(item.reorder_level)),
    [items]
  );

  const resetPoForm = () => {
    setPoForm({
      supplier_name: '',
      expected_date: '',
      notes: '',
      lines: [{ item_inventory_id: '', quantity_ordered: 1, unit_cost: 0 }],
    });
  };

  const handleCreateItem = async () => {
    if (!itemForm.sku.trim() || !itemForm.name.trim() || !itemForm.category.trim()) {
      showToast('SKU, name, and category are required', 'error');
      return;
    }

    try {
      setSubmitting(true);
      await externalInventoryAPI.createItem({
        ...itemForm,
        quantity_on_hand: Number(itemForm.quantity_on_hand),
        reorder_level: Number(itemForm.reorder_level),
        unit_cost: Number(itemForm.unit_cost),
      });
      showToast('Inventory item created', 'success');
      setShowAddItemModal(false);
      setItemForm(initialItemForm);
      await loadData();
    } catch (error) {
      showToast(error.message || 'Failed to create item', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const addPOLine = () => {
    setPoForm((prev) => ({
      ...prev,
      lines: [...prev.lines, { item_inventory_id: '', quantity_ordered: 1, unit_cost: 0 }],
    }));
  };

  const updatePOLine = (index, key, value) => {
    setPoForm((prev) => {
      const next = [...prev.lines];
      next[index] = { ...next[index], [key]: value };
      return { ...prev, lines: next };
    });
  };

  const removePOLine = (index) => {
    setPoForm((prev) => {
      const next = prev.lines.filter((_, i) => i !== index);
      return { ...prev, lines: next.length ? next : [{ item_inventory_id: '', quantity_ordered: 1, unit_cost: 0 }] };
    });
  };

  const handleCreatePO = async () => {
    if (!poForm.supplier_name.trim()) {
      showToast('Supplier name is required', 'error');
      return;
    }

    if (poForm.lines.some((line) => !line.item_inventory_id || Number(line.quantity_ordered) <= 0)) {
      showToast('Each PO line needs an item and quantity', 'error');
      return;
    }

    try {
      setSubmitting(true);
      await externalInventoryAPI.createPurchaseOrder({
        supplier_name: poForm.supplier_name,
        expected_date: poForm.expected_date || null,
        notes: poForm.notes || null,
        status: 'submitted',
        lines: poForm.lines.map((line) => ({
          item_inventory_id: line.item_inventory_id,
          quantity_ordered: Number(line.quantity_ordered),
          unit_cost: Number(line.unit_cost),
        })),
      });

      showToast('Purchase order created', 'success');
      setShowCreatePOModal(false);
      resetPoForm();
      await loadData();
    } catch (error) {
      showToast(error.message || 'Failed to create purchase order', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const openReceiveModal = (po) => {
    setReceivingPO(po);
    setReceiptForm({
      notes: '',
      lines: (po.lines || []).map((line) => ({
        item_inventory_id: line.item_inventory_id,
        quantity_received: Number(line.quantity_ordered) || 1,
        unit_cost: Number(line.unit_cost) || 0,
      })),
    });
  };

  const handleReceivePO = async () => {
    if (!receivingPO) return;

    if (receiptForm.lines.some((line) => Number(line.quantity_received) <= 0)) {
      showToast('Receipt line quantities must be greater than zero', 'error');
      return;
    }

    try {
      setSubmitting(true);
      await externalInventoryAPI.receivePurchaseOrder(receivingPO.po_id, {
        notes: receiptForm.notes || null,
        lines: receiptForm.lines.map((line) => ({
          item_inventory_id: line.item_inventory_id,
          quantity_received: Number(line.quantity_received),
          unit_cost: Number(line.unit_cost),
        })),
      });
      showToast('Stock receipt recorded', 'success');
      setReceivingPO(null);
      setReceiptForm({ notes: '', lines: [] });
      await loadData();
    } catch (error) {
      showToast(error.message || 'Failed to receive purchase order', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const itemColumns = [
    { key: 'inventory_id', label: 'Item ID' },
    { key: 'sku', label: 'SKU' },
    { key: 'name', label: 'Name' },
    { key: 'category', label: 'Category' },
    { key: 'quantity_on_hand', label: 'On Hand' },
    { key: 'reorder_level', label: 'Reorder Level' },
    {
      key: 'stock_status',
      label: 'Stock Health',
      render: (_, row) => {
        const low = Number(row.quantity_on_hand) <= Number(row.reorder_level);
        return (
          <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${low ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}>
            {low ? 'Low Stock' : 'Healthy'}
          </span>
        );
      },
    },
  ];

  const poColumns = [
    { key: 'po_id', label: 'PO ID' },
    { key: 'supplier_name', label: 'Supplier' },
    { key: 'status', label: 'Status' },
    { key: 'line_count', label: 'Lines' },
    {
      key: 'total_amount',
      label: 'Total',
      render: (value) => `$${Number(value || 0).toLocaleString()}`,
    },
    {
      key: 'actions',
      label: 'Actions',
      sortable: false,
      render: (_, row) => (
        <Button
          size="sm"
          variant="outline"
          onClick={() => openReceiveModal(row)}
          disabled={['received', 'cancelled'].includes(row.status)}
        >
          Receive
        </Button>
      ),
    },
  ];

  const movementColumns = [
    { key: 'movement_id', label: 'Movement ID' },
    { key: 'item_sku', label: 'SKU' },
    { key: 'item_name', label: 'Item' },
    { key: 'movement_type', label: 'Type' },
    { key: 'quantity', label: 'Qty' },
    { key: 'reference_type', label: 'Reference' },
    { key: 'reference_id', label: 'Ref ID' },
  ];

  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-2xl border border-orange-200 bg-gradient-to-r from-orange-50 via-amber-50 to-lime-50 p-6">
        <div className="absolute -top-8 -right-8 h-32 w-32 rounded-full bg-orange-200/40 blur-2xl" />
        <div className="absolute -bottom-10 left-20 h-28 w-28 rounded-full bg-lime-200/40 blur-2xl" />
        <div className="relative z-10 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">External Inventory Hub</h1>
            <p className="mt-1 text-sm text-gray-600">
              Manage third-party spare parts, purchase flow, and stock movement from one control deck.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" icon={RefreshCw} onClick={loadData}>
              Refresh
            </Button>
            <Button icon={PackagePlus} onClick={() => setShowAddItemModal(true)}>
              Add Item
            </Button>
            <Button variant="secondary" icon={Factory} onClick={() => setShowCreatePOModal(true)}>
              New PO
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Card title="SKUs" icon={Boxes}>
          <p className="text-2xl font-bold text-gray-900">{dashboard?.total_skus ?? 0}</p>
        </Card>
        <Card title="Units" icon={TrendingUp}>
          <p className="text-2xl font-bold text-gray-900">{dashboard?.total_units ?? 0}</p>
        </Card>
        <Card title="Low Stock" icon={AlertTriangle}>
          <p className="text-2xl font-bold text-red-600">{dashboard?.low_stock_items ?? 0}</p>
        </Card>
        <Card title="Pending POs" icon={ClipboardCheck}>
          <p className="text-2xl font-bold text-amber-600">{dashboard?.pending_purchase_orders ?? 0}</p>
        </Card>
        <Card title="Inventory Value" icon={DollarSign}>
          <p className="text-2xl font-bold text-emerald-600">${Number(dashboard?.inventory_value || 0).toLocaleString()}</p>
        </Card>
      </div>

      {lowStockItems.length > 0 && (
        <Card title="Low Stock Attention" subtitle="These items are at or below reorder level">
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
            {lowStockItems.slice(0, 6).map((item) => (
              <div key={item.id} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2">
                <p className="text-sm font-semibold text-red-800">{item.name}</p>
                <p className="text-xs text-red-700">{item.sku} • {item.quantity_on_hand} / reorder {item.reorder_level}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title="Inventory Items" subtitle="Current external stock" padding={false}>
        <DataTable
          columns={itemColumns}
          data={items}
          loading={loading}
          emptyMessage="No external inventory items yet"
        />
      </Card>

      <Card title="Purchase Orders" subtitle="Order and receiving status" padding={false}>
        <DataTable
          columns={poColumns}
          data={purchaseOrders}
          loading={loading}
          emptyMessage="No purchase orders yet"
        />
      </Card>

      <Card title="Stock Movements" subtitle="Latest material flow" padding={false}>
        <DataTable
          columns={movementColumns}
          data={movements}
          loading={loading}
          emptyMessage="No stock movements yet"
        />
      </Card>

      <Modal
        isOpen={showAddItemModal}
        onClose={() => setShowAddItemModal(false)}
        title="Add External Inventory Item"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowAddItemModal(false)}>Cancel</Button>
            <Button loading={submitting} onClick={handleCreateItem}>Create Item</Button>
          </>
        }
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">SKU</span>
            <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={itemForm.sku} onChange={(e) => setItemForm((p) => ({ ...p, sku: e.target.value }))} />
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">Name</span>
            <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={itemForm.name} onChange={(e) => setItemForm((p) => ({ ...p, name: e.target.value }))} />
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">Category</span>
            <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={itemForm.category} onChange={(e) => setItemForm((p) => ({ ...p, category: e.target.value }))} />
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">Unit</span>
            <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={itemForm.unit} onChange={(e) => setItemForm((p) => ({ ...p, unit: e.target.value }))} />
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">Opening Qty</span>
            <input type="number" min="0" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={itemForm.quantity_on_hand} onChange={(e) => setItemForm((p) => ({ ...p, quantity_on_hand: e.target.value }))} />
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">Reorder Level</span>
            <input type="number" min="0" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={itemForm.reorder_level} onChange={(e) => setItemForm((p) => ({ ...p, reorder_level: e.target.value }))} />
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">Unit Cost</span>
            <input type="number" min="0" step="0.01" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={itemForm.unit_cost} onChange={(e) => setItemForm((p) => ({ ...p, unit_cost: e.target.value }))} />
          </label>
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">Supplier</span>
            <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={itemForm.supplier_name} onChange={(e) => setItemForm((p) => ({ ...p, supplier_name: e.target.value }))} />
          </label>
          <label className="space-y-1 md:col-span-2">
            <span className="text-sm font-medium text-gray-700">Location</span>
            <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={itemForm.location} onChange={(e) => setItemForm((p) => ({ ...p, location: e.target.value }))} />
          </label>
        </div>
      </Modal>

      <Modal
        isOpen={showCreatePOModal}
        onClose={() => setShowCreatePOModal(false)}
        title="Create Purchase Order"
        size="xl"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowCreatePOModal(false)}>Cancel</Button>
            <Button loading={submitting} onClick={handleCreatePO}>Create PO</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-sm font-medium text-gray-700">Supplier Name</span>
              <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={poForm.supplier_name} onChange={(e) => setPoForm((p) => ({ ...p, supplier_name: e.target.value }))} />
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium text-gray-700">Expected Date</span>
              <input type="date" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={poForm.expected_date} onChange={(e) => setPoForm((p) => ({ ...p, expected_date: e.target.value }))} />
            </label>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-gray-800">PO Lines</h4>
              <Button size="sm" variant="outline" onClick={addPOLine}>Add Line</Button>
            </div>
            {poForm.lines.map((line, idx) => (
              <div key={idx} className="grid grid-cols-1 gap-2 rounded-lg border border-gray-200 p-3 md:grid-cols-12">
                <select
                  className="rounded-lg border border-gray-300 px-3 py-2 md:col-span-5"
                  value={line.item_inventory_id}
                  onChange={(e) => updatePOLine(idx, 'item_inventory_id', e.target.value)}
                >
                  <option value="">Select item</option>
                  {items.map((item) => (
                    <option key={item.inventory_id} value={item.inventory_id}>
                      {item.sku} - {item.name}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min="1"
                  className="rounded-lg border border-gray-300 px-3 py-2 md:col-span-2"
                  value={line.quantity_ordered}
                  onChange={(e) => updatePOLine(idx, 'quantity_ordered', e.target.value)}
                />
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  className="rounded-lg border border-gray-300 px-3 py-2 md:col-span-3"
                  value={line.unit_cost}
                  onChange={(e) => updatePOLine(idx, 'unit_cost', e.target.value)}
                />
                <Button size="sm" variant="danger" className="md:col-span-2" onClick={() => removePOLine(idx)}>
                  Remove
                </Button>
              </div>
            ))}
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={!!receivingPO}
        onClose={() => setReceivingPO(null)}
        title={`Receive Purchase Order ${receivingPO?.po_id || ''}`}
        size="lg"
        footer={
          <>
            <Button variant="ghost" onClick={() => setReceivingPO(null)}>Cancel</Button>
            <Button loading={submitting} onClick={handleReceivePO}>Confirm Receipt</Button>
          </>
        }
      >
        <div className="space-y-3">
          {receiptForm.lines.map((line, idx) => (
            <div key={idx} className="grid grid-cols-1 gap-2 rounded-lg border border-gray-200 p-3 md:grid-cols-3">
              <select
                className="rounded-lg border border-gray-300 px-3 py-2"
                value={line.item_inventory_id}
                onChange={(e) => {
                  const value = e.target.value;
                  setReceiptForm((prev) => {
                    const next = [...prev.lines];
                    next[idx] = { ...next[idx], item_inventory_id: value };
                    return { ...prev, lines: next };
                  });
                }}
              >
                {receivingPO?.lines?.map((poLine) => (
                  <option key={`${idx}-${poLine.item_inventory_id}`} value={poLine.item_inventory_id}>
                    {poLine.item_sku} - {poLine.item_name}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min="1"
                className="rounded-lg border border-gray-300 px-3 py-2"
                value={line.quantity_received}
                onChange={(e) => {
                  const value = e.target.value;
                  setReceiptForm((prev) => {
                    const next = [...prev.lines];
                    next[idx] = { ...next[idx], quantity_received: value };
                    return { ...prev, lines: next };
                  });
                }}
              />
              <input
                type="number"
                min="0"
                step="0.01"
                className="rounded-lg border border-gray-300 px-3 py-2"
                value={line.unit_cost}
                onChange={(e) => {
                  const value = e.target.value;
                  setReceiptForm((prev) => {
                    const next = [...prev.lines];
                    next[idx] = { ...next[idx], unit_cost: value };
                    return { ...prev, lines: next };
                  });
                }}
              />
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
};

export default ExternalInventory;
