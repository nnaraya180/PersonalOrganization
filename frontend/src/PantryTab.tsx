import React, { useState, useEffect } from 'react';
import './App.css';
import {
  fetchPantryItems,
  createPantryItem,
  updatePantryItem,
  deletePantryItem,
  consumePantryItem,
  restockPantryItem,
  fetchRecipes,
  type PantryItem as APIPantryItem,
  type Recipe as APIRecipe,
} from './api';

// Local types that match our UI needs
interface PantryItem {
  id: number;
  name: string;
  quantity: number | null;
  category?: string | null;
  expiresOn?: string | null;
}

interface Recipe {
  id: number;
  title: string;
  timeMinutes?: number | null;
  tags?: string[];
  lastCooked?: string;
  cookNext?: boolean;
  moodNote?: string;
}

type PantryView = 'hub' | 'pantry' | 'recipes';

// Helper to convert API item to UI item
function apiItemToUI(item: APIPantryItem): PantryItem {
  return {
    id: item.id,
    name: item.name,
    quantity: item.quantity ?? null,
    category: item.category ?? null,
    expiresOn: item.expiration_date ?? null,
  };
}

// Helper to convert API recipe to UI recipe
function apiRecipeToUI(recipe: APIRecipe): Recipe {
  // Convert ingredients array to tag-like strings
  const tags = recipe.ingredients?.slice(0, 5) ?? [];
  
  return {
    id: recipe.id,
    title: recipe.title,
    timeMinutes: recipe.time_minutes ?? null,
    tags: tags,
  };
}

// Helper functions
const getExpirationStatus = (expiresOn?: string | null): { label: string; className: string } => {
  if (!expiresOn) return { label: 'OK', className: 'badge-gray' };

  const now = new Date();
  const expiration = new Date(expiresOn);
  const daysUntilExpiration = Math.ceil((expiration.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  if (daysUntilExpiration <= 3) {
    return { label: 'Urgent', className: 'badge-red' };
  } else if (daysUntilExpiration <= 7) {
    return { label: 'Soon', className: 'badge-yellow' };
  }
  return { label: 'OK', className: 'badge-gray' };
};

const getExpiringItems = (items: PantryItem[], days: number = 7): PantryItem[] => {
  const now = new Date();
  return items
    .filter((item) => {
      if (!item.expiresOn) return false;
      const expiration = new Date(item.expiresOn);
      const daysUntilExpiration = Math.ceil((expiration.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
      return daysUntilExpiration <= days && daysUntilExpiration >= 0;
    })
    .sort((a, b) => {
      const dateA = new Date(a.expiresOn!).getTime();
      const dateB = new Date(b.expiresOn!).getTime();
      return dateA - dateB;
    })
    .slice(0, 3);
};

// Main PantryTab Component
const PantryTab: React.FC = () => {
  const [view, setView] = useState<PantryView>('hub');
  const [pantryItems, setPantryItems] = useState<PantryItem[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [recipeFilter, setRecipeFilter] = useState<string>('all');

  // Loading and error states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isGroceryModalOpen, setIsGroceryModalOpen] = useState(false);
  const [isAddItemModalOpen, setIsAddItemModalOpen] = useState(false);
  const [isEditItemModalOpen, setIsEditItemModalOpen] = useState(false);
  const [currentItem, setCurrentItem] = useState<PantryItem | null>(null);

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    quantity: '',
    category: '',
    expiresOn: '',
  });

  // Load data on mount
  useEffect(() => {
    let mounted = true;

    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [itemsData, recipesData] = await Promise.all([
          fetchPantryItems(),
          fetchRecipes(),
        ]);

        if (!mounted) return;

        setPantryItems(itemsData.map(apiItemToUI));
        setRecipes(recipesData.map(apiRecipeToUI));
      } catch (err) {
        if (!mounted) return;
        console.error('Failed to load data:', err);
        setError('Failed to load pantry data. Please try refreshing the page.');
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      mounted = false;
    };
  }, []);

  const handleAddItem = async () => {
    try {
      const newItem = await createPantryItem({
        name: formData.name,
        quantity: formData.quantity ? parseInt(formData.quantity, 10) : null,
        category: formData.category || null,
        expiration_date: formData.expiresOn || null,
      });

      setPantryItems([...pantryItems, apiItemToUI(newItem)]);
      setFormData({ name: '', quantity: '', category: '', expiresOn: '' });
      setIsAddItemModalOpen(false);
    } catch (err) {
      console.error('Failed to add item:', err);
      alert('Failed to add item. Please try again.');
    }
  };

  const handleEditItem = (item: PantryItem) => {
    setCurrentItem(item);
    setFormData({
      name: item.name,
      quantity: item.quantity !== null ? String(item.quantity) : '',
      category: item.category || '',
      expiresOn: item.expiresOn ? item.expiresOn.split('T')[0] : '',
    });
    setIsEditItemModalOpen(true);
  };

  const handleUpdateItem = async () => {
    if (!currentItem) return;

    try {
      const updated = await updatePantryItem(currentItem.id, {
        name: formData.name,
        quantity: formData.quantity ? parseInt(formData.quantity, 10) : null,
        category: formData.category || null,
        expiration_date: formData.expiresOn || null,
      });

      setPantryItems(
        pantryItems.map((item) => (item.id === currentItem.id ? apiItemToUI(updated) : item))
      );
      setCurrentItem(null);
      setFormData({ name: '', quantity: '', category: '', expiresOn: '' });
      setIsEditItemModalOpen(false);
    } catch (err) {
      console.error('Failed to update item:', err);
      alert('Failed to update item. Please try again.');
    }
  };

  const handleRemoveItem = async (id: number) => {
    if (!confirm('Are you sure you want to delete this item?')) return;

    try {
      await deletePantryItem(id);
      setPantryItems(pantryItems.filter((item) => item.id !== id));
    } catch (err) {
      console.error('Failed to delete item:', err);
      alert('Failed to delete item. Please try again.');
    }
  };

  const handleConsume = async (id: number) => {
    const amountStr = prompt('How much to consume?');
    if (!amountStr) return;

    const amount = parseInt(amountStr, 10);
    if (isNaN(amount) || amount <= 0) {
      alert('Please enter a valid positive number');
      return;
    }

    try {
      const updated = await consumePantryItem(id, amount);
      setPantryItems(pantryItems.map((item) => (item.id === id ? apiItemToUI(updated) : item)));
    } catch (err) {
      console.error('Failed to consume item:', err);
      alert('Failed to consume item. Please try again.');
    }
  };

  const handleRestock = async (id: number) => {
    const amountStr = prompt('How much to restock?');
    if (!amountStr) return;

    const amount = parseInt(amountStr, 10);
    if (isNaN(amount) || amount <= 0) {
      alert('Please enter a valid positive number');
      return;
    }

    try {
      const updated = await restockPantryItem(id, amount);
      setPantryItems(pantryItems.map((item) => (item.id === id ? apiItemToUI(updated) : item)));
    } catch (err) {
      console.error('Failed to restock item:', err);
      alert('Failed to restock item. Please try again.');
    }
  };

  const handleToggleCooked = (id: number) => {
    setRecipes(
      recipes.map((recipe) =>
        recipe.id === id
          ? { ...recipe, lastCooked: recipe.lastCooked ? undefined : new Date().toISOString() }
          : recipe
      )
    );
  };

  const handleToggleCookNext = (id: number) => {
    setRecipes(recipes.map((recipe) => (recipe.id === id ? { ...recipe, cookNext: !recipe.cookNext } : recipe)));
  };

  const filteredRecipes = recipes.filter((recipe) => {
    if (recipeFilter === 'cookNext') return recipe.cookNext;
    if (recipeFilter === 'recentlyCooked') return recipe.lastCooked;
    return true;
  });

  const expiringItems = getExpiringItems(pantryItems);

  // Show loading state
  if (loading) {
    return (
      <div className="panel">
        <h2 className="panel-title">Pantry Hub</h2>
        <p className="card-text">Loading pantry data...</p>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="panel">
        <h2 className="panel-title">Pantry Hub</h2>
        <p className="card-text" style={{ color: '#ef4444' }}>
          {error}
        </p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }

  // Hub View
  if (view === 'hub') {
    return (
      <div className="panel">
        <h2 className="panel-title">Pantry Hub</h2>
        <p className="panel-subtitle">Manage your pantry, browse recipes, and plan meals</p>

        <div className="split-grid">
          {/* View and edit pantry */}
          <div className="card">
            <h3 className="card-title">View and edit pantry</h3>
            <p className="card-text">See everything in your kitchen and update it.</p>
            <button className="btn btn-primary" onClick={() => setView('pantry')}>
              See pantry
            </button>
          </div>

          {/* Recipe database */}
          <div className="card">
            <h3 className="card-title">Recipe database</h3>
            <p className="card-text">Browse recipes, mark favorites, and choose what to cook next.</p>
            <button className="btn btn-success" onClick={() => setView('recipes')}>
              See recipes
            </button>
          </div>

          {/* Add grocery haul */}
          <div className="card">
            <h3 className="card-title">Add grocery haul</h3>
            <p className="card-text">In the future, this will import items automatically from a receipt.</p>
            <button className="btn btn-secondary" onClick={() => setIsGroceryModalOpen(true)}>
              Import haul
            </button>
          </div>

          {/* Expiring items */}
          <div className="card">
            <h3 className="card-title">Expiring items</h3>
            {expiringItems.length > 0 ? (
              <div style={{ marginBottom: '1rem' }}>
                {expiringItems.map((item) => {
                  const status = getExpirationStatus(item.expiresOn);
                  const daysLeft = Math.ceil((new Date(item.expiresOn!).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                  return (
                    <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <span className="card-text">{item.name}</span>
                      <span className={`badge ${status.className}`}>{daysLeft}d</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="card-text" style={{ color: '#6b7280' }}>
                No items expiring soon!
              </p>
            )}
            <button
              className="btn btn-warning"
              onClick={() => alert('Feature coming soon: View recipes using expiring items')}
            >
              See expiring recipes
            </button>
          </div>
        </div>

        {/* Grocery Haul Modal */}
        {isGroceryModalOpen && (
          <div className="modal-overlay" onClick={() => setIsGroceryModalOpen(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <h3 className="modal-title">Import grocery haul</h3>
              <div className="form-group">
                <label>Paste your grocery list or receipt (coming soon)</label>
                <textarea
                  className="input-field"
                  placeholder="Example: 2 gallons milk, 1 dozen eggs..."
                  rows={6}
                  style={{ resize: 'vertical' }}
                />
              </div>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '1rem' }}>
                This feature is coming later. Stay tuned!
              </p>
              <div className="modal-actions">
                <button className="btn btn-primary" disabled>
                  Process grocery haul
                </button>
                <button className="btn btn-secondary" onClick={() => setIsGroceryModalOpen(false)}>
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Pantry View
  if (view === 'pantry') {
    return (
      <div className="panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <button className="btn btn-secondary" onClick={() => setView('hub')}>
            ← Back to Pantry hub
          </button>
          <h2 className="panel-title" style={{ margin: 0 }}>Pantry</h2>
        </div>

        <button className="btn btn-success" style={{ marginBottom: '1.5rem' }} onClick={() => setIsAddItemModalOpen(true)}>
          Add item
        </button>

        {pantryItems.length === 0 ? (
          <p className="card-text">No pantry items yet. Add your first item above!</p>
        ) : (
          <div className="split-grid">
            {pantryItems.map((item) => {
              const status = getExpirationStatus(item.expiresOn);
              return (
                <div key={item.id} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                    <h3 className="card-title" style={{ margin: 0 }}>{item.name}</h3>
                    <span className={`badge ${status.className}`}>{status.label}</span>
                  </div>
                  <p className="card-text" style={{ marginBottom: '0.25rem' }}>
                    Qty: {item.quantity ?? 'N/A'}
                    {item.category && ` • ${item.category}`}
                  </p>
                  {item.expiresOn && (
                    <p style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.75rem' }}>
                      Expires: {new Date(item.expiresOn).toLocaleDateString()}
                    </p>
                  )}
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <button className="btn btn-small btn-primary" onClick={() => handleEditItem(item)}>
                      Edit
                    </button>
                    <button className="btn btn-small btn-danger" onClick={() => handleRemoveItem(item.id)}>
                      Remove
                    </button>
                    <button className="btn btn-small btn-warning" onClick={() => handleConsume(item.id)}>
                      Consume
                    </button>
                    <button className="btn btn-small btn-success" onClick={() => handleRestock(item.id)}>
                      Restock
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Add Item Modal */}
        {isAddItemModalOpen && (
          <div className="modal-overlay" onClick={() => setIsAddItemModalOpen(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <h3 className="modal-title">Add pantry item</h3>
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  className="input-field"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Milk"
                />
              </div>
              <div className="form-group">
                <label>Quantity</label>
                <input
                  type="number"
                  className="input-field"
                  value={formData.quantity}
                  onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                  placeholder="e.g., 1"
                />
              </div>
              <div className="form-group">
                <label>Category</label>
                <input
                  type="text"
                  className="input-field"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  placeholder="e.g., Dairy"
                />
              </div>
              <div className="form-group">
                <label>Expiration date</label>
                <input
                  type="date"
                  className="input-field"
                  value={formData.expiresOn}
                  onChange={(e) => setFormData({ ...formData, expiresOn: e.target.value })}
                />
              </div>
              <div className="modal-actions">
                <button
                  className="btn btn-primary"
                  onClick={handleAddItem}
                  disabled={!formData.name}
                >
                  Add
                </button>
                <button className="btn btn-secondary" onClick={() => setIsAddItemModalOpen(false)}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Edit Item Modal */}
        {isEditItemModalOpen && (
          <div className="modal-overlay" onClick={() => setIsEditItemModalOpen(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <h3 className="modal-title">Edit pantry item</h3>
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  className="input-field"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Milk"
                />
              </div>
              <div className="form-group">
                <label>Quantity</label>
                <input
                  type="number"
                  className="input-field"
                  value={formData.quantity}
                  onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                  placeholder="e.g., 1"
                />
              </div>
              <div className="form-group">
                <label>Category</label>
                <input
                  type="text"
                  className="input-field"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  placeholder="e.g., Dairy"
                />
              </div>
              <div className="form-group">
                <label>Expiration date</label>
                <input
                  type="date"
                  className="input-field"
                  value={formData.expiresOn}
                  onChange={(e) => setFormData({ ...formData, expiresOn: e.target.value })}
                />
              </div>
              <div className="modal-actions">
                <button
                  className="btn btn-primary"
                  onClick={handleUpdateItem}
                  disabled={!formData.name}
                >
                  Update
                </button>
                <button className="btn btn-secondary" onClick={() => setIsEditItemModalOpen(false)}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Recipe Database View
  return (
    <div className="panel">
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
        <button className="btn btn-secondary" onClick={() => setView('hub')}>
          ← Back to Pantry hub
        </button>
        <h2 className="panel-title" style={{ margin: 0 }}>Recipes</h2>
      </div>

      <p className="panel-subtitle">Browse your recipe collection and plan your next meal</p>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <span style={{ fontWeight: 500 }}>Filter:</span>
        <select
          className="input-field"
          style={{ maxWidth: '250px' }}
          value={recipeFilter}
          onChange={(e) => setRecipeFilter(e.target.value)}
        >
          <option value="all">All recipes</option>
          <option value="cookNext">Cook next</option>
          <option value="recentlyCooked">Recently cooked</option>
        </select>
      </div>

      {filteredRecipes.length === 0 ? (
        <p style={{ color: '#6b7280', textAlign: 'center', marginTop: '2rem' }}>
          No recipes match the selected filter
        </p>
      ) : (
        <div className="split-grid">
          {filteredRecipes.map((recipe) => (
            <div key={recipe.id} className="card">
              <h3 className="card-title">{recipe.title}</h3>
              {recipe.timeMinutes && (
                <p className="card-text" style={{ marginBottom: '0.5rem' }}>
                  ⏱️ {recipe.timeMinutes} min
                </p>
              )}
              {recipe.tags && recipe.tags.length > 0 && (
                <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                  {recipe.tags.map((tag, idx) => (
                    <span key={idx} className="badge badge-purple">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              {recipe.moodNote && (
                <p style={{ fontSize: '0.875rem', color: '#6b7280', fontStyle: 'italic', marginBottom: '0.5rem' }}>
                  {recipe.moodNote}
                </p>
              )}
              {recipe.lastCooked && (
                <p style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.75rem' }}>
                  Last cooked: {new Date(recipe.lastCooked).toLocaleDateString()}
                </p>
              )}
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto' }}>
                <button
                  className={`btn btn-small ${recipe.lastCooked ? 'btn-success' : 'btn-secondary'}`}
                  onClick={() => handleToggleCooked(recipe.id)}
                >
                  Cooked
                </button>
                <button
                  className={`btn btn-small ${recipe.cookNext ? 'btn-warning' : 'btn-secondary'}`}
                  onClick={() => handleToggleCookNext(recipe.id)}
                >
                  Cook next
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PantryTab;
