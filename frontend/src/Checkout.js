import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppContext } from './App';

const useAppContext = () => {
  const context = React.useContext(AppContext);
  if (!context) {
    return {
      cart: [],
      getCartTotal: () => 0,
      user: null,
      clearCart: () => {}
    };
  }
  return context;
};

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export function Checkout() {
  const navigate = useNavigate();
  const { cart, getCartTotal, user, clearCart } = useAppContext();
  const [loading, setLoading] = useState(false);
  const [orderPlaced, setOrderPlaced] = useState(false);
  const [orderId, setOrderId] = useState('');

  // Form states
  const [orderType, setOrderType] = useState('delivery'); // delivery, pickup
  const [paymentMethod, setPaymentMethod] = useState('cash'); // cash, online
  const [deliveryAddress, setDeliveryAddress] = useState({
    street: '',
    city: 'Woodstock',
    state: 'GA',
    zip_code: '',
    phone: user?.phone || ''
  });
  const [specialInstructions, setSpecialInstructions] = useState('');
  const [deliveryFee, setDeliveryFee] = useState(0);
  const [estimatedTime, setEstimatedTime] = useState(25);

  // Calculations
  const subtotal = getCartTotal();
  const tax = subtotal * 0.085; // Georgia tax
  const total = subtotal + deliveryFee + tax;

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    if (cart.length === 0) {
      navigate('/cart');
      return;
    }
    
    // Calculate delivery fee when address changes
    if (orderType === 'delivery' && deliveryAddress.street && deliveryAddress.zip_code) {
      calculateDeliveryFee();
    }
  }, [user, cart, orderType, deliveryAddress]);

  const calculateDeliveryFee = async () => {
    // Simple distance calculation for demo
    // In production, use Google Maps API or similar
    const distance = Math.random() * 10; // Random distance for demo
    
    if (distance <= 5) {
      setDeliveryFee(4.00);
      setEstimatedTime(35);
    } else if (distance <= 9) {
      setDeliveryFee(4.00 + ((distance - 5) * 2));
      setEstimatedTime(45);
    } else {
      setDeliveryFee(0); // Outside delivery area
      setEstimatedTime(0);
    }
  };

  const handlePlaceOrder = async () => {
    if (orderType === 'delivery' && (!deliveryAddress.street || !deliveryAddress.zip_code)) {
      alert('Please fill in your delivery address');
      return;
    }

    setLoading(true);

    try {
      const orderData = {
        items: cart,
        delivery_address: orderType === 'delivery' ? deliveryAddress : null,
        order_type: orderType,
        payment_method: paymentMethod,
        subtotal: subtotal,
        delivery_fee: orderType === 'delivery' ? deliveryFee : 0,
        tax: tax,
        total: orderType === 'delivery' ? total : subtotal + tax,
        special_instructions: specialInstructions
      };

      const response = await fetch(`${API}/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(orderData)
      });

      if (response.ok) {
        const result = await response.json();
        setOrderId(result.id);
        setOrderPlaced(true);
        clearCart();
      } else {
        const error = await response.json();
        alert(`Order failed: ${error.detail}`);
      }
    } catch (error) {
      alert(`Network error: ${error.message}`);
    }

    setLoading(false);
  };

  if (orderPlaced) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-lg text-center max-w-md">
          <div className="text-green-600 text-6xl mb-4">✓</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Order Placed Successfully!</h2>
          <p className="text-gray-600 mb-2">Order #: {orderId}</p>
          <p className="text-gray-600 mb-6">
            Estimated {orderType === 'delivery' ? 'delivery' : 'pickup'} time: {estimatedTime} minutes
          </p>
          <div className="space-y-3">
            <button
              onClick={() => navigate('/orders')}
              className="w-full bg-red-600 text-white py-3 rounded-lg hover:bg-red-700 transition font-medium"
            >
              Track Order
            </button>
            <button
              onClick={() => navigate('/')}
              className="w-full border border-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-50 transition font-medium"
            >
              Order More
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Checkout</h1>
          <p className="text-gray-600">Complete your order</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Order Details */}
          <div className="space-y-6">
            {/* Order Type Selection */}
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold mb-4">Order Type</h3>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setOrderType('delivery')}
                  className={`p-4 border-2 rounded-lg text-center transition ${
                    orderType === 'delivery'
                      ? 'border-red-600 bg-red-50 text-red-600'
                      : 'border-gray-300 hover:border-red-300'
                  }`}
                >
                  <div className="text-2xl mb-2">🚚</div>
                  <div className="font-medium">Delivery</div>
                  <div className="text-sm text-gray-500">35-45 min</div>
                </button>
                <button
                  onClick={() => setOrderType('pickup')}
                  className={`p-4 border-2 rounded-lg text-center transition ${
                    orderType === 'pickup'
                      ? 'border-red-600 bg-red-50 text-red-600'
                      : 'border-gray-300 hover:border-red-300'
                  }`}
                >
                  <div className="text-2xl mb-2">🏪</div>
                  <div className="font-medium">Pickup</div>
                  <div className="text-sm text-gray-500">20-25 min</div>
                </button>
              </div>
            </div>

            {/* Delivery Address */}
            {orderType === 'delivery' && (
              <div className="bg-white rounded-lg p-6 shadow-sm">
                <h3 className="text-lg font-semibold mb-4">Delivery Address</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Street Address *
                    </label>
                    <input
                      type="text"
                      value={deliveryAddress.street}
                      onChange={(e) => setDeliveryAddress({...deliveryAddress, street: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-red-500 focus:border-red-500"
                      placeholder="123 Main St"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                      <input
                        type="text"
                        value={deliveryAddress.city}
                        onChange={(e) => setDeliveryAddress({...deliveryAddress, city: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-red-500 focus:border-red-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
                      <select
                        value={deliveryAddress.state}
                        onChange={(e) => setDeliveryAddress({...deliveryAddress, state: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-red-500 focus:border-red-500"
                      >
                        <option value="GA">Georgia</option>
                        <option value="AL">Alabama</option>
                        <option value="TN">Tennessee</option>
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        ZIP Code *
                      </label>
                      <input
                        type="text"
                        value={deliveryAddress.zip_code}
                        onChange={(e) => setDeliveryAddress({...deliveryAddress, zip_code: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-red-500 focus:border-red-500"
                        placeholder="30188"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                      <input
                        type="tel"
                        value={deliveryAddress.phone}
                        onChange={(e) => setDeliveryAddress({...deliveryAddress, phone: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-red-500 focus:border-red-500"
                        placeholder="(555) 123-4567"
                      />
                    </div>
                  </div>
                </div>
                
                {deliveryFee === 0 && deliveryAddress.street && (
                  <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded-md">
                    <p className="text-red-700 text-sm">
                      ⚠️ This address is outside our delivery area (max 9 miles from store)
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Pickup Info */}
            {orderType === 'pickup' && (
              <div className="bg-white rounded-lg p-6 shadow-sm">
                <h3 className="text-lg font-semibold mb-4">Pickup Location</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium">NY Pizza Woodstock</h4>
                  <p className="text-gray-600">10214 Hickory Flat Hwy</p>
                  <p className="text-gray-600">Woodstock, GA 30188</p>
                  <p className="text-red-600 font-medium mt-2">📞 (470) 545-0095</p>
                </div>
              </div>
            )}

            {/* Payment Method */}
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold mb-4">Payment Method</h3>
              <div className="space-y-3">
                <div className="flex items-center">
                  <input
                    type="radio"
                    id="cash"
                    name="payment"
                    value="cash"
                    checked={paymentMethod === 'cash'}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="text-red-600 focus:ring-red-500"
                  />
                  <label htmlFor="cash" className="ml-2 flex items-center">
                    <span className="text-lg mr-2">💵</span>
                    Cash {orderType === 'delivery' ? '(Pay on delivery)' : '(Pay at pickup)'}
                  </label>
                </div>
                <div className="flex items-center">
                  <input
                    type="radio"
                    id="online"
                    name="payment"
                    value="online"
                    checked={paymentMethod === 'online'}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="text-red-600 focus:ring-red-500"
                  />
                  <label htmlFor="online" className="ml-2 flex items-center">
                    <span className="text-lg mr-2">💳</span>
                    Credit/Debit Card (Online)
                  </label>
                </div>
              </div>
              
              {paymentMethod === 'online' && (
                <div className="mt-4 p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
                  <p className="text-yellow-800 text-sm">
                    💡 Online payment integration coming soon! For now, please use cash payment.
                  </p>
                </div>
              )}
            </div>

            {/* Special Instructions */}
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold mb-4">Special Instructions</h3>
              <textarea
                value={specialInstructions}
                onChange={(e) => setSpecialInstructions(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-red-500 focus:border-red-500"
                rows="3"
                placeholder="Any special requests for your order..."
              />
            </div>
          </div>

          {/* Order Summary */}
          <div>
            <div className="bg-white rounded-lg p-6 shadow-sm sticky top-24">
              <h3 className="text-lg font-semibold mb-4">Order Summary</h3>
              
              {/* Cart Items */}
              <div className="divide-y mb-4">
                {cart.map((item, index) => (
                  <div key={index} className="py-3 flex justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium">{item.name}</h4>
                      {item.size && <p className="text-sm text-gray-600">Size: {item.size}</p>}
                      {item.toppings && item.toppings.length > 0 && (
                        <p className="text-xs text-gray-500">
                          {item.toppings.join(', ')}
                        </p>
                      )}
                      <p className="text-sm text-gray-600">Qty: {item.quantity}</p>
                    </div>
                    <div className="text-right">
                      <span className="font-medium">${(item.price * item.quantity).toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Totals */}
              <div className="border-t pt-4 space-y-2">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span>${subtotal.toFixed(2)}</span>
                </div>
                
                {orderType === 'delivery' && deliveryFee > 0 && (
                  <div className="flex justify-between">
                    <span>Delivery Fee</span>
                    <span>${deliveryFee.toFixed(2)}</span>
                  </div>
                )}
                
                <div className="flex justify-between">
                  <span>Tax (8.5%)</span>
                  <span>${tax.toFixed(2)}</span>
                </div>
                
                <div className="border-t pt-2">
                  <div className="flex justify-between text-lg font-bold">
                    <span>Total</span>
                    <span>${total.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Estimated Time */}
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-blue-800 text-sm">
                  ⏱️ Estimated {orderType} time: {estimatedTime} minutes
                </p>
              </div>

              {/* Place Order Button */}
              <button
                onClick={handlePlaceOrder}
                disabled={loading || (orderType === 'delivery' && deliveryFee === 0)}
                className="w-full mt-6 bg-red-600 text-white py-4 rounded-lg hover:bg-red-700 transition font-medium text-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Placing Order...' : `Place Order - $${total.toFixed(2)}`}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}