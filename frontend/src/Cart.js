import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppContext } from './App';

// Custom hook to use app context  
const useAppContext = () => {
  const context = React.useContext(AppContext);
  if (!context) {
    // If context is not available, return mock data for now
    return {
      cart: [],
      removeFromCart: () => {},
      updateCartItemQuantity: () => {},
      getCartTotal: () => 0,
      user: null
    };
  }
  return context;
};

// Cart Component
export function Cart() {
  const navigate = useNavigate();
  const { cart, removeFromCart, updateCartItemQuantity, getCartTotal, user } = useAppContext();
  const [promoCode, setPromoCode] = useState('');
  const [promoDiscount, setPromoDiscount] = useState(0);

  const subtotal = getCartTotal();
  const tax = subtotal * 0.085; // Georgia tax rate
  const total = subtotal + tax - promoDiscount;

  const handleQuantityChange = (index, newQuantity) => {
    updateCartItemQuantity(index, newQuantity);
  };

  const handleRemoveItem = (index) => {
    removeFromCart(index);
  };

  const handleApplyPromo = () => {
    // Simple promo code logic - in real app, this would call API
    const validPromoCodes = {
      'WELCOME10': 0.10 * subtotal,
      'PIZZA20': 0.20 * subtotal,
      'STUDENT': 5.00
    };

    if (validPromoCodes[promoCode.toUpperCase()]) {
      setPromoDiscount(validPromoCodes[promoCode.toUpperCase()]);
    } else {
      alert('Invalid promo code');
    }
  };

  const handleCheckout = () => {
    if (!user) {
      navigate('/login');
      return;
    }
    navigate('/checkout');
  };

  if (cart.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          <div className="text-center py-16">
            <div className="text-6xl mb-6">🛒</div>
            <h2 className="text-3xl font-bold text-gray-800 mb-4">Your cart is empty</h2>
            <p className="text-gray-600 mb-8">Looks like you haven't added any delicious pizzas yet!</p>
            <button
              onClick={() => navigate('/')}
              className="bg-red-600 text-white px-8 py-3 rounded-lg hover:bg-red-700 transition font-medium"
            >
              Browse Our Menu
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
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Shopping Cart</h1>
          <p className="text-gray-600">Review your order before checkout</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm">
              <div className="p-6 border-b">
                <h3 className="text-lg font-semibold">Order Items ({cart.length})</h3>
              </div>
              
              <div className="divide-y">
                {cart.map((item, index) => (
                  <CartItem
                    key={index}
                    item={item}
                    index={index}
                    onQuantityChange={handleQuantityChange}
                    onRemove={handleRemoveItem}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm sticky top-24">
              <div className="p-6 border-b">
                <h3 className="text-lg font-semibold">Order Summary</h3>
              </div>
              
              <div className="p-6 space-y-4">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span className="font-medium">${subtotal.toFixed(2)}</span>
                </div>
                
                <div className="flex justify-between">
                  <span>Tax (8.5%)</span>
                  <span className="font-medium">${tax.toFixed(2)}</span>
                </div>
                
                {promoDiscount > 0 && (
                  <div className="flex justify-between text-green-600">
                    <span>Promo Discount</span>
                    <span className="font-medium">-${promoDiscount.toFixed(2)}</span>
                  </div>
                )}
                
                <div className="border-t pt-4">
                  <div className="flex justify-between text-lg font-bold">
                    <span>Total</span>
                    <span>${total.toFixed(2)}</span>
                  </div>
                </div>

                {/* Promo Code */}
                <div className="border-t pt-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">Promo Code</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={promoCode}
                        onChange={(e) => setPromoCode(e.target.value)}
                        placeholder="Enter code"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
                      />
                      <button
                        onClick={handleApplyPromo}
                        className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition text-sm"
                      >
                        Apply
                      </button>
                    </div>
                  </div>
                </div>

                {/* Checkout Button */}
                <button
                  onClick={handleCheckout}
                  className="w-full bg-red-600 text-white py-3 rounded-lg hover:bg-red-700 transition font-medium text-lg"
                >
                  {user ? 'Proceed to Checkout' : 'Sign In to Checkout'}
                </button>

                {/* Continue Shopping */}
                <button
                  onClick={() => navigate('/')}
                  className="w-full border border-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-50 transition font-medium"
                >
                  Continue Shopping
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Cart Item Component
function CartItem({ item, index, onQuantityChange, onRemove }) {
  return (
    <div className="p-6">
      <div className="flex gap-4">
        {/* Item Image */}
        <div className="w-20 h-20 bg-gray-200 rounded-lg flex-shrink-0">
          <div className="w-full h-full bg-red-100 rounded-lg flex items-center justify-center">
            <span className="text-red-600 text-2xl">🍕</span>
          </div>
        </div>

        {/* Item Details */}
        <div className="flex-1">
          <div className="flex justify-between items-start">
            <div>
              <h4 className="font-semibold text-gray-800">{item.name}</h4>
              {item.size && (
                <p className="text-sm text-gray-600">Size: {item.size}</p>
              )}
              {item.toppings && item.toppings.length > 0 && (
                <div className="mt-1">
                  <p className="text-sm text-gray-600">Toppings:</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {item.toppings.map((topping, i) => (
                      <span key={i} className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {topping}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {item.special_instructions && (
                <p className="text-sm text-gray-600 mt-1">
                  Note: {item.special_instructions}
                </p>
              )}
            </div>
            
            <button
              onClick={() => onRemove(index)}
              className="text-gray-400 hover:text-red-600 transition ml-4"
              title="Remove item"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>

          {/* Quantity and Price */}
          <div className="flex justify-between items-center mt-4">
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">Quantity:</span>
              <div className="flex items-center border border-gray-300 rounded">
                <button
                  onClick={() => onQuantityChange(index, Math.max(1, item.quantity - 1))}
                  className="px-3 py-1 hover:bg-gray-50 transition"
                >
                  -
                </button>
                <span className="px-3 py-1 min-w-12 text-center">{item.quantity}</span>
                <button
                  onClick={() => onQuantityChange(index, item.quantity + 1)}
                  className="px-3 py-1 hover:bg-gray-50 transition"
                >
                  +
                </button>
              </div>
            </div>
            
            <div className="text-right">
              <div className="text-sm text-gray-600">${item.price.toFixed(2)} each</div>
              <div className="font-semibold text-lg">
                ${(item.price * item.quantity).toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}