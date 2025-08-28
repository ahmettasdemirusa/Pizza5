import React, { useState, useEffect } from 'react';
import { AppContext } from './App';

const useAppContext = () => {
  const context = React.useContext(AppContext);
  if (!context) {
    return { user: null };
  }
  return context;
};

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export function Admin() {
  const { user } = useAppContext();
  const [activeTab, setActiveTab] = useState('orders');
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user && user.is_admin) {
      fetchOrders();
    }
  }, [user]);

  const fetchOrders = async () => {
    try {
      const response = await fetch(`${API}/admin/orders`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });

      if (response.ok) {
        const data = await response.json();
        setOrders(data);
      }
    } catch (error) {
      console.error('Error fetching orders:', error);
    }
    setLoading(false);
  };

  const updateOrderStatus = async (orderId, newStatus) => {
    try {
      const response = await fetch(`${API}/admin/orders/${orderId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ status: newStatus })
      });

      if (response.ok) {
        setOrders(orders.map(order => 
          order.id === orderId ? { ...order, status: newStatus } : order
        ));
      }
    } catch (error) {
      console.error('Error updating order status:', error);
    }
  };

  // Check if user is admin
  if (!user || !user.is_admin) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🚫</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Access Denied</h2>
          <p className="text-gray-600">You need admin privileges to access this page.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading admin panel...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Admin Panel</h1>
          <p className="text-gray-600">NY Pizza Woodstock Management</p>
        </div>

        {/* Tab Navigation */}
        <div className="mb-8">
          <div className="flex space-x-1 bg-white p-1 rounded-lg shadow-sm">
            <button
              onClick={() => setActiveTab('orders')}
              className={`flex-1 px-4 py-2 rounded-md transition ${
                activeTab === 'orders'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              📋 Orders ({orders.length})
            </button>
            <button
              onClick={() => setActiveTab('menu')}
              className={`flex-1 px-4 py-2 rounded-md transition ${
                activeTab === 'menu'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              🍕 Menu Management
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`flex-1 px-4 py-2 rounded-md transition ${
                activeTab === 'analytics'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              📊 Analytics
            </button>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'orders' && (
          <OrdersManagement 
            orders={orders} 
            onUpdateStatus={updateOrderStatus}
            onRefresh={fetchOrders}
          />
        )}
        
        {activeTab === 'menu' && <MenuManagement />}
        {activeTab === 'analytics' && <Analytics orders={orders} />}
      </div>
    </div>
  );
}

function OrdersManagement({ orders, onUpdateStatus, onRefresh }) {
  const [filter, setFilter] = useState('all');

  const filteredOrders = orders.filter(order => {
    if (filter === 'all') return true;
    return order.status === filter;
  });

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      confirmed: 'bg-blue-100 text-blue-800 border-blue-300',
      preparing: 'bg-purple-100 text-purple-800 border-purple-300',
      ready: 'bg-green-100 text-green-800 border-green-300',
      delivered: 'bg-gray-100 text-gray-800 border-gray-300',
      cancelled: 'bg-red-100 text-red-800 border-red-300'
    };
    return colors[status] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  return (
    <div>
      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-lg shadow-sm mb-6">
        <div className="flex justify-between items-center">
          <div className="flex space-x-2">
            {['all', 'pending', 'confirmed', 'preparing', 'ready'].map(status => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`px-3 py-1 rounded-full text-sm ${
                  filter === status
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {status === 'all' ? 'All Orders' : status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
          <button
            onClick={onRefresh}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Orders List */}
      <div className="space-y-4">
        {filteredOrders.map(order => (
          <AdminOrderCard 
            key={order.id} 
            order={order} 
            onUpdateStatus={onUpdateStatus}
            getStatusColor={getStatusColor}
          />
        ))}
        
        {filteredOrders.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg">
            <p className="text-gray-600">No orders found for the selected filter.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function AdminOrderCard({ order, onUpdateStatus, getStatusColor }) {
  const [updating, setUpdating] = useState(false);

  const handleStatusUpdate = async (newStatus) => {
    setUpdating(true);
    await onUpdateStatus(order.id, newStatus);
    setUpdating(false);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const statusOptions = ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled'];

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Order Info */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <h3 className="font-bold text-lg">Order #{order.id.slice(-8)}</h3>
            <span className={`px-2 py-1 rounded text-xs ${getStatusColor(order.status)}`}>
              {order.status.toUpperCase()}
            </span>
          </div>
          
          <div className="space-y-1 text-sm text-gray-600">
            <p>📅 {formatDate(order.created_at)}</p>
            <p>🚚 {order.order_type === 'delivery' ? 'Delivery' : 'Pickup'}</p>
            <p>💳 {order.payment_method === 'cash' ? 'Cash' : 'Online'}</p>
            <p className="font-medium text-red-600">💰 ${order.total.toFixed(2)}</p>
          </div>

          {order.delivery_address && (
            <div className="mt-3 p-2 bg-gray-50 rounded text-sm">
              <p className="font-medium">Delivery:</p>
              <p>{order.delivery_address.street}</p>
              <p>{order.delivery_address.city}, {order.delivery_address.state}</p>
            </div>
          )}
        </div>

        {/* Order Items */}
        <div>
          <h4 className="font-medium mb-2">Items ({order.items.length}):</h4>
          <div className="space-y-1 text-sm max-h-32 overflow-y-auto">
            {order.items.map((item, index) => (
              <div key={index} className="flex justify-between">
                <span>{item.quantity}x {item.name} {item.size && `(${item.size})`}</span>
                <span>${(item.price * item.quantity).toFixed(2)}</span>
              </div>
            ))}
          </div>
          
          {order.special_instructions && (
            <div className="mt-2 p-2 bg-yellow-50 rounded text-xs">
              <strong>Note:</strong> {order.special_instructions}
            </div>
          )}
        </div>

        {/* Status Management */}
        <div>
          <h4 className="font-medium mb-2">Update Status:</h4>
          <div className="grid grid-cols-2 gap-2">
            {statusOptions.map(status => (
              <button
                key={status}
                onClick={() => handleStatusUpdate(status)}
                disabled={updating || order.status === status}
                className={`px-3 py-2 rounded text-sm transition ${
                  order.status === status
                    ? `${getStatusColor(status)} cursor-not-allowed`
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                } ${updating ? 'opacity-50' : ''}`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
          
          {order.estimated_delivery && (
            <div className="mt-3 text-xs text-gray-600">
              <p>⏱️ Est: {formatDate(order.estimated_delivery)}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MenuManagement() {
  return (
    <div className="bg-white rounded-lg p-6 shadow-sm">
      <h2 className="text-2xl font-bold mb-4">Menu Management</h2>
      <div className="text-center py-12">
        <div className="text-6xl mb-4">🍕</div>
        <h3 className="text-xl font-bold mb-2">Menu Management Coming Soon</h3>
        <p className="text-gray-600">
          Full menu editing capabilities will be available in the next update.
        </p>
      </div>
    </div>
  );
}

function Analytics({ orders }) {
  const totalOrders = orders.length;
  const totalRevenue = orders.reduce((sum, order) => sum + order.total, 0);
  const averageOrder = totalOrders > 0 ? totalRevenue / totalOrders : 0;
  
  const statusStats = orders.reduce((acc, order) => {
    acc[order.status] = (acc[order.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm text-center">
          <div className="text-3xl font-bold text-red-600">{totalOrders}</div>
          <div className="text-gray-600">Total Orders</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm text-center">
          <div className="text-3xl font-bold text-green-600">${totalRevenue.toFixed(2)}</div>
          <div className="text-gray-600">Total Revenue</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm text-center">
          <div className="text-3xl font-bold text-blue-600">${averageOrder.toFixed(2)}</div>
          <div className="text-gray-600">Average Order</div>
        </div>
      </div>

      {/* Order Status Distribution */}
      <div className="bg-white p-6 rounded-lg shadow-sm">
        <h3 className="text-lg font-bold mb-4">Order Status Distribution</h3>
        <div className="space-y-3">
          {Object.entries(statusStats).map(([status, count]) => (
            <div key={status} className="flex justify-between items-center">
              <span className="capitalize">{status}</span>
              <div className="flex items-center space-x-2">
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-red-600 h-2 rounded-full"
                    style={{ width: `${(count / totalOrders) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium">{count}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}