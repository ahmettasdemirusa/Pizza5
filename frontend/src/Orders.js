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

export function Orders() {
  const { user } = useAppContext();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      fetchOrders();
    }
  }, [user]);

  const fetchOrders = async () => {
    try {
      const response = await fetch(`${API}/orders/my-orders`, {
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

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-blue-100 text-blue-800',
      preparing: 'bg-purple-100 text-purple-800',
      ready: 'bg-green-100 text-green-800',
      delivered: 'bg-gray-100 text-gray-800',
      cancelled: 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getStatusIcon = (status) => {
    const icons = {
      pending: '⏳',
      confirmed: '✅',
      preparing: '👨‍🍳',
      ready: '🍕',
      delivered: '📦',
      cancelled: '❌'
    };
    return icons[status] || '📄';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your orders...</p>
        </div>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-8">My Orders</h1>
          <div className="text-center py-16">
            <div className="text-6xl mb-6">📋</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">No Orders Yet</h2>
            <p className="text-gray-600 mb-8">You haven't placed any orders yet.</p>
            <button
              onClick={() => window.location.href = '/'}
              className="bg-red-600 text-white px-8 py-3 rounded-lg hover:bg-red-700 transition font-medium"
            >
              Start Ordering
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-8">My Orders</h1>

        <div className="space-y-6">
          {orders.map((order) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      </div>
    </div>
  );
}

function OrderCard({ order }) {
  const [expanded, setExpanded] = useState(false);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-blue-100 text-blue-800',
      preparing: 'bg-purple-100 text-purple-800',
      ready: 'bg-green-100 text-green-800',
      delivered: 'bg-gray-100 text-gray-800',
      cancelled: 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getStatusIcon = (status) => {
    const icons = {
      pending: '⏳',
      confirmed: '✅',
      preparing: '👨‍🍳',
      ready: '🍕',
      delivered: '📦',
      cancelled: '❌'
    };
    return icons[status] || '📄';
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border">
      <div 
        className="p-6 cursor-pointer hover:bg-gray-50 transition"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <h3 className="font-semibold text-lg">Order #{order.id.slice(-8)}</h3>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                {getStatusIcon(order.status)} {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
              </span>
            </div>
            
            <div className="text-sm text-gray-600 space-y-1">
              <p>📅 {formatDate(order.created_at)}</p>
              <p>🚚 {order.order_type === 'delivery' ? 'Delivery' : 'Pickup'}</p>
              <p>💳 {order.payment_method === 'cash' ? 'Cash Payment' : 'Online Payment'}</p>
              {order.estimated_delivery && (
                <p>⏱️ Estimated: {formatDate(order.estimated_delivery)}</p>
              )}
            </div>
          </div>
          
          <div className="text-right">
            <div className="text-2xl font-bold text-red-600">${order.total.toFixed(2)}</div>
            <div className="text-sm text-gray-600">{order.items.length} items</div>
            <div className="text-xs text-gray-500 mt-1">
              {expanded ? 'Click to collapse' : 'Click to expand'}
            </div>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t bg-gray-50 p-6">
          <h4 className="font-medium mb-4">Order Items:</h4>
          <div className="space-y-3 mb-4">
            {order.items.map((item, index) => (
              <div key={index} className="flex justify-between items-start bg-white p-3 rounded">
                <div className="flex-1">
                  <h5 className="font-medium">{item.name}</h5>
                  {item.size && <p className="text-sm text-gray-600">Size: {item.size}</p>}
                  {item.toppings && item.toppings.length > 0 && (
                    <p className="text-xs text-gray-500">{item.toppings.join(', ')}</p>
                  )}
                  <p className="text-sm text-gray-600">Quantity: {item.quantity}</p>
                </div>
                <div className="text-right">
                  <span className="font-medium">${(item.price * item.quantity).toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>

          {order.delivery_address && (
            <div className="mb-4">
              <h4 className="font-medium mb-2">Delivery Address:</h4>
              <div className="bg-white p-3 rounded text-sm">
                <p>{order.delivery_address.street}</p>
                <p>{order.delivery_address.city}, {order.delivery_address.state} {order.delivery_address.zip_code}</p>
                {order.delivery_address.phone && <p>📞 {order.delivery_address.phone}</p>}
              </div>
            </div>
          )}

          {order.special_instructions && (
            <div className="mb-4">
              <h4 className="font-medium mb-2">Special Instructions:</h4>
              <div className="bg-white p-3 rounded text-sm">
                {order.special_instructions}
              </div>
            </div>
          )}

          <div className="border-t pt-4">
            <div className="flex justify-between text-sm">
              <span>Subtotal:</span>
              <span>${order.subtotal.toFixed(2)}</span>
            </div>
            {order.delivery_fee > 0 && (
              <div className="flex justify-between text-sm">
                <span>Delivery Fee:</span>
                <span>${order.delivery_fee.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm">
              <span>Tax:</span>
              <span>${order.tax.toFixed(2)}</span>
            </div>
            <div className="flex justify-between font-medium text-lg border-t pt-2 mt-2">
              <span>Total:</span>
              <span>${order.total.toFixed(2)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}