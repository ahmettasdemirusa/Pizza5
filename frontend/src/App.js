import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, Link } from 'react-router-dom';
import './App.css';
import { Cart as CartPage } from './Cart';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Context for user authentication and cart
export const AppContext = createContext();

// Custom hook to use app context
const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

// Auth Context Provider
function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [cart, setCart] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      fetchUserInfo();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUserInfo = async () => {
    try {
      const response = await fetch(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        logout();
      }
    } catch (error) {
      console.error('Error fetching user info:', error);
      logout();
    }
    setLoading(false);
  };

  const login = async (email, password) => {
    try {
      const response = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        setUser(data.user);
        return { success: true };
      } else {
        const error = await response.json();
        return { success: false, message: error.detail };
      }
    } catch (error) {
      return { success: false, message: 'Network error' };
    }
  };

  const register = async (userData) => {
    try {
      const response = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        setUser(data.user);
        return { success: true };
      } else {
        const error = await response.json();
        return { success: false, message: error.detail };
      }
    } catch (error) {
      return { success: false, message: 'Network error' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setCart([]);
  };

  const addToCart = (item) => {
    setCart(prevCart => {
      const existingItem = prevCart.find(cartItem => 
        cartItem.item_id === item.item_id && 
        cartItem.size === item.size &&
        JSON.stringify(cartItem.toppings) === JSON.stringify(item.toppings)
      );

      if (existingItem) {
        return prevCart.map(cartItem =>
          cartItem.item_id === item.item_id && 
          cartItem.size === item.size &&
          JSON.stringify(cartItem.toppings) === JSON.stringify(item.toppings)
            ? { ...cartItem, quantity: cartItem.quantity + item.quantity }
            : cartItem
        );
      }

      return [...prevCart, item];
    });
  };

  const removeFromCart = (index) => {
    setCart(prevCart => prevCart.filter((_, i) => i !== index));
  };

  const updateCartItemQuantity = (index, quantity) => {
    if (quantity <= 0) {
      removeFromCart(index);
      return;
    }

    setCart(prevCart => 
      prevCart.map((item, i) => 
        i === index ? { ...item, quantity } : item
      )
    );
  };

  const clearCart = () => setCart([]);

  const getCartTotal = () => {
    return cart.reduce((total, item) => total + (item.price * item.quantity), 0);
  };

  const value = {
    user,
    token,
    cart,
    loading,
    login,
    register,
    logout,
    addToCart,
    removeFromCart,
    updateCartItemQuantity,
    clearCart,
    getCartTotal
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

// Loading Component
function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-red-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading...</p>
      </div>
    </div>
  );
}

// Header Component
function Header() {
  const { user, logout, cart } = useAppContext();
  const navigate = useNavigate();
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  return (
    <header className="bg-red-600 text-white shadow-lg sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between py-4">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
              <span className="text-red-600 font-bold text-xl">🍕</span>
            </div>
            <div>
              <h1 className="text-xl font-bold">NY Pizza</h1>
              <p className="text-xs text-red-200">Woodstock</p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <Link to="/" className="hover:text-red-200 transition">Menu</Link>
            <Link to="/cart" className="hover:text-red-200 transition flex items-center">
              Cart ({cart.length})
            </Link>
            {user ? (
              <div className="flex items-center space-x-4">
                <span className="text-sm">Hello, {user.first_name}</span>
                <button 
                  onClick={logout}
                  className="bg-red-700 px-3 py-1 rounded hover:bg-red-800 transition"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="space-x-2">
                <button 
                  onClick={() => navigate('/login')}
                  className="px-4 py-2 border border-white rounded hover:bg-white hover:text-red-600 transition"
                >
                  Login
                </button>
                <button 
                  onClick={() => navigate('/register')}
                  className="px-4 py-2 bg-white text-red-600 rounded hover:bg-red-50 transition"
                >
                  Sign Up
                </button>
              </div>
            )}
          </nav>

          {/* Mobile Menu Button */}
          <button 
            onClick={() => setShowMobileMenu(!showMobileMenu)}
            className="md:hidden"
          >
            <div className="w-6 h-6 flex flex-col justify-center space-y-1">
              <div className="w-full h-0.5 bg-white"></div>
              <div className="w-full h-0.5 bg-white"></div>
              <div className="w-full h-0.5 bg-white"></div>
            </div>
          </button>
        </div>

        {/* Mobile Menu */}
        {showMobileMenu && (
          <div className="md:hidden pb-4">
            <nav className="flex flex-col space-y-2">
              <Link to="/" className="py-2 hover:text-red-200 transition">Menu</Link>
              <Link to="/cart" className="py-2 hover:text-red-200 transition">
                Cart ({cart.length})
              </Link>
              {user ? (
                <>
                  <span className="py-2 text-sm">Hello, {user.first_name}</span>
                  <button 
                    onClick={logout}
                    className="text-left py-2 hover:text-red-200 transition"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <button 
                    onClick={() => navigate('/login')}
                    className="text-left py-2 hover:text-red-200 transition"
                  >
                    Login
                  </button>
                  <button 
                    onClick={() => navigate('/register')}
                    className="text-left py-2 hover:text-red-200 transition"
                  >
                    Sign Up
                  </button>
                </>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}

// Login Component
function Login() {
  const { login } = useAppContext();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    
    if (result.success) {
      navigate('/');
    } else {
      setError(result.message);
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">Sign In</h2>
          <p className="mt-2 text-gray-600">Welcome back to NY Pizza Woodstock</p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
                placeholder="your@email.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
                placeholder="Your password"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>

          <div className="text-center">
            <p className="text-sm text-gray-600">
              Don't have an account?{' '}
              <Link to="/register" className="text-red-600 hover:text-red-500 font-medium">
                Sign up here
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}

// Register Component
function Register() {
  const { register } = useAppContext();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    phone: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await register(formData);
    
    if (result.success) {
      navigate('/');
    } else {
      setError(result.message);
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">Create Account</h2>
          <p className="mt-2 text-gray-600">Join NY Pizza Woodstock family</p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  First Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Last Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
                placeholder="your@email.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Phone Number
              </label>
              <input
                type="tel"
                required
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
                placeholder="(555) 123-4567"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
                placeholder="Create a secure password"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>

          <div className="text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link to="/login" className="text-red-600 hover:text-red-500 font-medium">
                Sign in here
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}

// Menu Component
function Menu() {
  const [pizzas, setPizzas] = useState([]);
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeCategory, setActiveCategory] = useState('pizzas');
  const [selectedPizza, setSelectedPizza] = useState(null);
  const { addToCart } = useAppContext();

  useEffect(() => {
    console.log('Menu component mounted, fetching data...');
    fetchMenuData();
  }, []);

  const fetchMenuData = async () => {
    try {
      console.log('Fetching menu data from API...');
      const [pizzasResponse, itemsResponse] = await Promise.all([
        fetch(`${API}/menu/pizzas`),
        fetch(`${API}/menu/items`)
      ]);

      console.log('API responses received:', pizzasResponse.status, itemsResponse.status);

      const pizzasData = await pizzasResponse.json();
      const itemsData = await itemsResponse.json();

      console.log('Pizzas data:', pizzasData.length, 'items');
      console.log('Menu items data:', itemsData.length, 'items');

      setPizzas(pizzasData);
      setMenuItems(itemsData);
    } catch (error) {
      console.error('Error fetching menu:', error);
      setError('Failed to load menu. Please refresh the page.');
    }
    setLoading(false);
  };

  const handlePizzaSelect = (pizza) => {
    console.log('Pizza selected:', pizza.name);
    setSelectedPizza(pizza);
  };

  console.log('Menu render - Loading:', loading, 'Pizzas:', pizzas.length, 'Error:', error);

  if (loading) return <Loading />;

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Oops! Something went wrong</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-red-600 text-white px-4 py-2 rounded"
          >
            Refresh Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-red-600 text-white py-12">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-4xl md:text-6xl font-bold mb-4">
            Authentic NY Pizza
          </h1>
          <p className="text-xl mb-6">
            Fresh ingredients, traditional recipes, delivered hot!
          </p>
          <div className="bg-white text-red-600 inline-block px-6 py-2 rounded-full">
            📍 10214 Hickory Flat Hwy, Woodstock, GA | 📞 (470) 545-0095
          </div>
        </div>
      </div>

      {/* Category Navigation */}
      <div className="bg-white shadow-sm sticky top-20 z-40">
        <div className="container mx-auto px-4">
          <div className="flex space-x-4 overflow-x-auto py-4">
            <button
              onClick={() => setActiveCategory('pizzas')}
              className={`whitespace-nowrap px-4 py-2 rounded-full transition ${
                activeCategory === 'pizzas'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              🍕 Pizzas
            </button>
            <button
              onClick={() => setActiveCategory('pasta')}
              className={`whitespace-nowrap px-4 py-2 rounded-full transition ${
                activeCategory === 'pasta'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              🍝 Pasta
            </button>
            <button
              onClick={() => setActiveCategory('calzone')}
              className={`whitespace-nowrap px-4 py-2 rounded-full transition ${
                activeCategory === 'calzone'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              🥟 Calzones
            </button>
            <button
              onClick={() => setActiveCategory('stromboli')}
              className={`whitespace-nowrap px-4 py-2 rounded-full transition ${
                activeCategory === 'stromboli'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              🌯 Stromboli
            </button>
            <button
              onClick={() => setActiveCategory('appetizers')}
              className={`whitespace-nowrap px-4 py-2 rounded-full transition ${
                activeCategory === 'appetizers'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              🥗 Appetizers
            </button>
            <button
              onClick={() => setActiveCategory('salads')}
              className={`whitespace-nowrap px-4 py-2 rounded-full transition ${
                activeCategory === 'salads'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              🥙 Salads
            </button>
            <button
              onClick={() => setActiveCategory('wings')}
              className={`whitespace-nowrap px-4 py-2 rounded-full transition ${
                activeCategory === 'wings'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:text-red-600'
              }`}
            >
              🍗 Wings
            </button>
          </div>
        </div>
      </div>

      {/* Menu Content */}
      <div className="container mx-auto px-4 py-8">
        {activeCategory === 'pizzas' && (
          <PizzaSection pizzas={pizzas} onPizzaSelect={handlePizzaSelect} />
        )}
        
        {activeCategory === 'pasta' && (
          <MenuSection 
            items={menuItems.filter(item => item.category === 'pasta')} 
            title="Fresh Pasta Dishes"
          />
        )}
        
        {activeCategory === 'calzone' && (
          <MenuSection 
            items={menuItems.filter(item => item.category === 'calzone')} 
            title="Delicious Calzones"
          />
        )}
        
        {activeCategory === 'stromboli' && (
          <MenuSection 
            items={menuItems.filter(item => item.category === 'stromboli')} 
            title="Delicious Stromboli"
          />
        )}
        
        {activeCategory === 'appetizers' && (
          <MenuSection 
            items={menuItems.filter(item => item.category === 'appetizers')} 
            title="Appetizers"
          />
        )}
        
        {activeCategory === 'salads' && (
          <MenuSection 
            items={menuItems.filter(item => item.category === 'salads')} 
            title="Fresh Salads"
          />
        )}
        
        {activeCategory === 'wings' && (
          <MenuSection 
            items={menuItems.filter(item => item.category === 'wings')} 
            title="Wings"
          />
        )}
      </div>

      {/* Pizza Detail Modal */}
      {selectedPizza && (
        <PizzaDetailModal 
          pizza={selectedPizza} 
          onClose={() => setSelectedPizza(null)}
        />
      )}
    </div>
  );
}

// Pizza Section Component
function PizzaSection({ pizzas, onPizzaSelect }) {
  const specialtyPizzas = pizzas.filter(pizza => pizza.category === 'specialty');
  const classicPizzas = pizzas.filter(pizza => pizza.category === 'classic');

  return (
    <div className="space-y-12">
      {/* Classic Pizzas */}
      {classicPizzas.length > 0 && (
        <section>
          <h2 className="text-3xl font-bold mb-6 text-gray-800">Classic Pizzas</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classicPizzas.map(pizza => (
              <PizzaCard 
                key={pizza.id} 
                pizza={pizza} 
                onClick={() => onPizzaSelect(pizza)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Specialty Pizzas */}
      {specialtyPizzas.length > 0 && (
        <section>
          <h2 className="text-3xl font-bold mb-6 text-gray-800">Specialty Pizzas</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {specialtyPizzas.map(pizza => (
              <PizzaCard 
                key={pizza.id} 
                pizza={pizza} 
                onClick={() => onPizzaSelect(pizza)}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// Pizza Card Component
function PizzaCard({ pizza, onClick }) {
  const basePrice = Math.min(...Object.values(pizza.sizes));

  return (
    <div 
      className="pizza-card bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-all duration-300 cursor-pointer transform hover:-translate-y-1"
      onClick={onClick}
    >
      <div className="pizza-image-container relative bg-gray-200">
        <img 
          src={pizza.image_url} 
          alt={pizza.name}
          className="w-full h-48 object-cover"
          onError={(e) => {
            e.target.src = 'https://via.placeholder.com/400x200/dc2626/white?text=Pizza';
          }}
        />
        <div className="pizza-image-overlay">
          Click to Customize
        </div>
      </div>
      <div className="p-4">
        <h3 className="text-lg font-semibold mb-2 text-gray-800">{pizza.name}</h3>
        <p className="text-gray-600 text-sm mb-3 line-clamp-2">{pizza.description}</p>
        
        {/* Show toppings if available */}
        {pizza.toppings && pizza.toppings.length > 0 && (
          <div className="mb-3">
            <div className="flex flex-wrap gap-1">
              {pizza.toppings.slice(0, 3).map((topping, index) => (
                <span 
                  key={index}
                  className="topping-chip text-xs"
                >
                  {topping}
                </span>
              ))}
              {pizza.toppings.length > 3 && (
                <span className="text-xs text-gray-500">+{pizza.toppings.length - 3} more</span>
              )}
            </div>
          </div>
        )}
        
        <div className="flex justify-between items-center">
          <span className="price text-lg font-bold text-red-600">
            From ${basePrice.toFixed(2)}
          </span>
          <button 
            className="btn-primary px-4 py-2 rounded-md text-sm font-medium"
            onClick={(e) => {
              e.stopPropagation();
              onClick();
            }}
          >
            Customize
          </button>
        </div>
      </div>
    </div>
  );
}

// Menu Section Component (for non-pizza items)
function MenuSection({ items, title }) {
  const { addToCart } = useAppContext();

  const handleAddToCart = (item) => {
    const cartItem = {
      item_id: item.id,
      item_type: 'menu_item',
      name: item.name,
      quantity: 1,
      price: item.price,
      toppings: []
    };
    addToCart(cartItem);
  };

  return (
    <section>
      <h2 className="text-3xl font-bold mb-6 text-gray-800">{title}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.map(item => (
          <div key={item.id} className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="aspect-w-16 aspect-h-9 bg-gray-200">
              <img 
                src={item.image_url} 
                alt={item.name}
                className="w-full h-48 object-cover"
              />
            </div>
            <div className="p-4">
              <h3 className="text-lg font-semibold mb-2">{item.name}</h3>
              <p className="text-gray-600 text-sm mb-3">{item.description}</p>
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold text-red-600">
                  ${item.price.toFixed(2)}
                </span>
                <button 
                  onClick={() => handleAddToCart(item)}
                  className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 transition text-sm"
                >
                  Add to Cart
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// Pizza Detail Modal Component
function PizzaDetailModal({ pizza, onClose }) {
  const [selectedSize, setSelectedSize] = useState('Medium');
  const [quantity, setQuantity] = useState(1);
  const { addToCart } = useAppContext();

  const handleAddToCart = () => {
    const cartItem = {
      item_id: pizza.id,
      item_type: 'pizza',
      name: pizza.name,
      size: selectedSize,
      quantity: quantity,
      price: pizza.sizes[selectedSize],
      toppings: pizza.toppings
    };
    addToCart(cartItem);
    onClose();
  };

  const currentPrice = pizza.sizes[selectedSize] || 0;
  const totalPrice = currentPrice * quantity;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-screen overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex justify-between items-start mb-4">
            <h2 className="text-2xl font-bold">{pizza.name}</h2>
            <button 
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              ×
            </button>
          </div>

          {/* Image */}
          <img 
            src={pizza.image_url} 
            alt={pizza.name}
            className="w-full h-64 object-cover rounded-lg mb-4"
          />

          {/* Description */}
          <p className="text-gray-600 mb-6">{pizza.description}</p>

          {/* Toppings */}
          {pizza.toppings && pizza.toppings.length > 0 && (
            <div className="mb-6">
              <h3 className="font-semibold mb-2">Toppings:</h3>
              <div className="flex flex-wrap gap-2">
                {pizza.toppings.map((topping, index) => (
                  <span 
                    key={index}
                    className="bg-gray-100 px-3 py-1 rounded-full text-sm"
                  >
                    {topping}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Size Selection */}
          <div className="mb-6">
            <h3 className="font-semibold mb-3">Choose Size:</h3>
            <div className="grid grid-cols-3 gap-3">
              {Object.entries(pizza.sizes).map(([size, price]) => (
                <button
                  key={size}
                  onClick={() => setSelectedSize(size)}
                  className={`p-3 border rounded-lg text-center transition ${
                    selectedSize === size
                      ? 'border-red-600 bg-red-50 text-red-600'
                      : 'border-gray-300 hover:border-red-300'
                  }`}
                >
                  <div className="font-medium">{size}</div>
                  <div className="text-sm text-gray-600">${price.toFixed(2)}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Quantity */}
          <div className="mb-6">
            <h3 className="font-semibold mb-3">Quantity:</h3>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                className="w-10 h-10 border border-gray-300 rounded-md flex items-center justify-center hover:bg-gray-50"
              >
                -
              </button>
              <span className="font-medium text-lg">{quantity}</span>
              <button
                onClick={() => setQuantity(quantity + 1)}
                className="w-10 h-10 border border-gray-300 rounded-md flex items-center justify-center hover:bg-gray-50"
              >
                +
              </button>
            </div>
          </div>

          {/* Add to Cart Button */}
          <div className="flex justify-between items-center">
            <div className="text-2xl font-bold">
              Total: ${totalPrice.toFixed(2)}
            </div>
            <button
              onClick={handleAddToCart}
              className="bg-red-600 text-white px-6 py-3 rounded-md hover:bg-red-700 transition font-medium"
            >
              Add to Cart
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Router>
        <AppContent />
      </Router>
    </AppProvider>
  );
}

function AppContent() {
  const { loading } = useAppContext();

  if (loading) {
    return <Loading />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <Routes>
        <Route path="/" element={<Menu />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/checkout" element={<Checkout />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

// Checkout Component (placeholder for now)
function Checkout() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Checkout</h1>
      <p>Checkout component will be implemented next...</p>
    </div>
  );
}