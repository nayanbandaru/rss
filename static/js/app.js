// API base URL
const API_BASE = '/api/v1';

// Token storage key
const TOKEN_KEY = 'reddit_alert_token';

// ========================================
// Token Management
// ========================================

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
}

// Authenticated fetch wrapper
async function authFetch(url, options = {}) {
    const token = getToken();
    if (token) {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        };
    }
    const response = await fetch(url, options);

    // Handle 401 - unauthorized
    if (response.status === 401) {
        clearToken();
        updateUIForAuthState(false);
        showAuthModal('login');
        throw new Error('Session expired. Please login again.');
    }

    return response;
}

// ========================================
// Auth State Management
// ========================================

let currentUser = null;

async function checkAuth() {
    const token = getToken();
    if (!token) {
        updateUIForAuthState(false);
        return false;
    }

    try {
        const response = await authFetch(`${API_BASE}/auth/me`);
        if (response.ok) {
            currentUser = await response.json();
            updateUIForAuthState(true);
            loadUserAlerts();
            return true;
        } else {
            clearToken();
            updateUIForAuthState(false);
            return false;
        }
    } catch (error) {
        clearToken();
        updateUIForAuthState(false);
        return false;
    }
}

function updateUIForAuthState(isLoggedIn) {
    const authPrompt = document.getElementById('auth-prompt');
    const userBar = document.getElementById('user-bar');
    const authRequiredNotice = document.getElementById('auth-required-notice');
    const createAlertSection = document.getElementById('create-alert-section');
    const viewAlertsSection = document.getElementById('view-alerts-section');

    if (isLoggedIn && currentUser) {
        // Show logged-in UI
        authPrompt.style.display = 'none';
        userBar.style.display = 'flex';
        document.getElementById('user-email').textContent = currentUser.email;

        authRequiredNotice.style.display = 'none';
        createAlertSection.style.display = 'block';
        viewAlertsSection.style.display = 'block';
    } else {
        // Show logged-out UI
        authPrompt.style.display = 'flex';
        userBar.style.display = 'none';

        authRequiredNotice.style.display = 'block';
        createAlertSection.style.display = 'none';
        viewAlertsSection.style.display = 'none';

        currentUser = null;
    }
}

// ========================================
// Auth Modal Functions
// ========================================

function showAuthModal(tab = 'login') {
    const modal = document.getElementById('auth-modal');
    modal.style.display = 'flex';
    switchAuthTab(tab);
    document.body.style.overflow = 'hidden';
}

function hideAuthModal() {
    const modal = document.getElementById('auth-modal');
    modal.style.display = 'none';
    document.body.style.overflow = '';

    // Reset forms
    document.querySelectorAll('.auth-form').forEach(form => form.reset());
}

function switchAuthTab(tab) {
    // Update tab buttons
    document.querySelectorAll('.modal-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    // Show/hide forms
    const forms = {
        'login': document.getElementById('login-form'),
        'register': document.getElementById('register-form'),
        'setup-password': document.getElementById('setup-password-form'),
        'forgot-password': document.getElementById('forgot-password-form')
    };

    Object.entries(forms).forEach(([key, form]) => {
        if (form) {
            form.style.display = key === tab ? 'block' : 'none';
        }
    });
}

// ========================================
// Auth Form Handlers
// ========================================

// Login handler
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitButton = e.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.classList.add('loading');

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const result = await response.json();

        if (!response.ok) {
            // Check if user needs to set up password (403)
            if (response.status === 403 && result.detail?.includes('password')) {
                document.getElementById('setup-email').value = email;
                switchAuthTab('setup-password');
                showMessage('Please set up a password for your account', 'warning');
                return;
            }
            throw new Error(result.detail || 'Login failed');
        }

        setToken(result.access_token);
        hideAuthModal();
        showMessage('Login successful!', 'success');
        checkAuth();

    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.classList.remove('loading');
    }
});

// Register handler
document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitButton = e.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.classList.add('loading');

    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Registration failed');
        }

        setToken(result.access_token);
        hideAuthModal();
        showMessage('Account created successfully!', 'success');
        checkAuth();

    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.classList.remove('loading');
    }
});

// Setup password handler (for existing users)
document.getElementById('setup-password-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitButton = e.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.classList.add('loading');

    const email = document.getElementById('setup-email').value;
    const password = document.getElementById('setup-password').value;

    try {
        const response = await fetch(`${API_BASE}/auth/setup-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to set password');
        }

        setToken(result.access_token);
        hideAuthModal();
        showMessage('Password set successfully!', 'success');
        checkAuth();

    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.classList.remove('loading');
    }
});

// Forgot password handler
document.getElementById('forgot-password-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitButton = e.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.classList.add('loading');

    const email = document.getElementById('forgot-email').value;

    try {
        const response = await fetch(`${API_BASE}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to send reset email');
        }

        showMessage(result.message, 'success');
        switchAuthTab('login');

    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.classList.remove('loading');
    }
});

// Logout handler
function handleLogout() {
    clearToken();
    currentUser = null;
    updateUIForAuthState(false);
    showMessage('Logged out successfully', 'success');
}

// ========================================
// Categorized Subreddit Data
// ========================================

const SUBREDDIT_CATEGORIES = [
    {
        label: 'Electronics & Technology',
        choices: [
            { value: 'hardwareswap', label: 'r/hardwareswap', customProperties: { description: 'PC parts & hardware' } },
            { value: 'appleswap', label: 'r/appleswap', customProperties: { description: 'Apple devices' } },
            { value: 'homelabsale', label: 'r/homelabsale', customProperties: { description: 'Homelab equipment' } }
        ]
    },
    {
        label: 'Computers & Peripherals',
        choices: [
            { value: 'mechmarket', label: 'r/mechmarket', customProperties: { description: 'Mechanical keyboards' } },
            { value: 'photomarket', label: 'r/photomarket', customProperties: { description: 'Camera gear' } },
            { value: 'AVexchange', label: 'r/AVexchange', customProperties: { description: 'Audio & video' } }
        ]
    },
    {
        label: 'Collectibles & Luxury',
        choices: [
            { value: 'watchexchange', label: 'r/watchexchange', customProperties: { description: 'Watches' } },
            { value: 'knife_swap', label: 'r/knife_swap', customProperties: { description: 'Knives' } },
            { value: 'pen_swap', label: 'r/pen_swap', customProperties: { description: 'Pens' } }
        ]
    },
    {
        label: 'Fashion & Accessories',
        choices: [
            { value: 'sneakermarket', label: 'r/sneakermarket', customProperties: { description: 'Sneakers' } },
            { value: 'fragranceswap', label: 'r/fragranceswap', customProperties: { description: 'Fragrances' } },
            { value: 'malefashionmarket', label: 'r/malefashionmarket', customProperties: { description: "Men's fashion" } }
        ]
    },
    {
        label: 'Entertainment & Media',
        choices: [
            { value: 'gameswap', label: 'r/gameswap', customProperties: { description: 'Video games' } },
            { value: 'gamesale', label: 'r/gamesale', customProperties: { description: 'Video game sales' } },
            { value: 'comicswap', label: 'r/comicswap', customProperties: { description: 'Comic books' } },
            { value: 'vinylcollectors', label: 'r/vinylcollectors', customProperties: { description: 'Vinyl records' } }
        ]
    },
    {
        label: 'Other',
        choices: [
            { value: 'legomarket', label: 'r/legomarket', customProperties: { description: 'LEGO sets' } },
            { value: 'bookexchange', label: 'r/bookexchange', customProperties: { description: 'Books' } }
        ]
    }
];

// ========================================
// Initialize Choices.js
// ========================================

let subredditChoices;

function initializeChoices() {
    const subredditSelect = document.getElementById('create-subreddit');
    if (!subredditSelect || subredditChoices) return;

    subredditChoices = new Choices(subredditSelect, {
        addItems: true,
        addItemFilter: function(value) {
            const normalized = value.replace(/^r\//, '').trim();
            return normalized.length > 0 && normalized.length <= 100;
        },
        searchEnabled: false,
        searchChoices: true,
        searchPlaceholderValue: 'Type to search subreddits...',
        searchFloor: 1,
        fuseOptions: {
            threshold: 0.3,
            keys: ['label', 'value', 'customProperties.description']
        },
        shouldSort: false,
        renderChoiceLimit: 50,
        placeholder: true,
        placeholderValue: 'Select or type a subreddit...',
        itemSelectText: 'Press to select',
        noResultsText: 'No matching subreddits. Press Enter to add custom subreddit.',
        noChoicesText: 'Start typing to add custom subreddit',
        removeItemButton: false,
        callbackOnCreateTemplates: function(template) {
            return {
                choice: (classNames, data) => {
                    const description = data.customProperties?.description;
                    return template(`
                        <div class="${classNames.item} ${classNames.itemChoice} ${data.disabled ? classNames.itemDisabled : classNames.itemSelectable}"
                             data-select-text="${this.config.itemSelectText}"
                             data-choice ${data.disabled ? 'data-choice-disabled aria-disabled="true"' : 'data-choice-selectable'}
                             data-id="${data.id}"
                             data-value="${data.value}"
                             ${data.groupId > 0 ? 'role="treeitem"' : 'role="option"'}>
                            <span>${data.label}</span>
                            ${description ? `<small class="choice-description">${description}</small>` : ''}
                        </div>
                    `);
                }
            };
        }
    });

    subredditChoices.setChoices(SUBREDDIT_CATEGORIES, 'value', 'label', true);
}

// ========================================
// Page Initialization
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Choices.js
    initializeChoices();

    // Check authentication state
    checkAuth();
});

// ========================================
// Utility Functions
// ========================================

function showMessage(message, type = 'success') {
    const container = document.getElementById('message-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    container.appendChild(messageDiv);

    setTimeout(() => {
        messageDiv.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => messageDiv.remove(), 300);
    }, 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========================================
// Alert Management
// ========================================

// Load user's alerts
async function loadUserAlerts() {
    if (!currentUser) return;

    const loadingEl = document.getElementById('alerts-loading');
    if (loadingEl) loadingEl.style.display = 'block';

    try {
        const response = await authFetch(`${API_BASE}/alerts/`);

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to load alerts');
        }

        displayAlerts(result.alerts);

    } catch (error) {
        if (error.message !== 'Session expired. Please login again.') {
            showMessage(error.message, 'error');
        }
    } finally {
        if (loadingEl) loadingEl.style.display = 'none';
    }
}

// Display alerts in the UI
function displayAlerts(alerts) {
    const listDiv = document.getElementById('alerts-list');
    const countSpan = document.getElementById('alert-count');

    countSpan.textContent = alerts.length;

    if (alerts.length === 0) {
        listDiv.innerHTML = `
            <div class="empty-state">
                <p>No alerts found.</p>
                <p>Create one using the form above!</p>
            </div>
        `;
    } else {
        listDiv.innerHTML = alerts.map(alert => {
            const createdDate = new Date(alert.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });

            return `
                <div class="alert-item">
                    <div class="alert-info">
                        <strong>r/${escapeHtml(alert.subreddit)}</strong>
                        <div class="alert-meta">
                            <div>Keyword: "${escapeHtml(alert.keyword)}"</div>
                            <div>Created: ${createdDate}</div>
                            <div>Status: ${alert.is_active ? 'Active' : 'Inactive'}</div>
                        </div>
                    </div>
                    <button class="btn btn-danger" onclick="deleteAlert('${alert.id}')">
                        Delete
                    </button>
                </div>
            `;
        }).join('');
    }
}

// Create Alert Form Handler
document.getElementById('create-alert-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitButton = e.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.classList.add('loading');

    const formData = new FormData(e.target);
    const data = {
        subreddit: formData.get('subreddit'),
        keyword: formData.get('keyword')
    };

    try {
        const response = await authFetch(`${API_BASE}/alerts/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to create alert');
        }

        showMessage(result.message, 'success');
        e.target.reset();

        if (subredditChoices) {
            subredditChoices.setChoiceByValue('');
        }

        // Reload alerts list
        loadUserAlerts();

    } catch (error) {
        if (error.message !== 'Session expired. Please login again.') {
            showMessage(error.message, 'error');
        }
    } finally {
        submitButton.disabled = false;
        submitButton.classList.remove('loading');
    }
});

// Delete alert function
async function deleteAlert(alertId) {
    if (!confirm('Are you sure you want to delete this alert?')) {
        return;
    }

    try {
        const response = await authFetch(
            `${API_BASE}/alerts/${alertId}`,
            { method: 'DELETE' }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to delete alert');
        }

        showMessage(result.message, 'success');
        loadUserAlerts();

    } catch (error) {
        if (error.message !== 'Session expired. Please login again.') {
            showMessage(error.message, 'error');
        }
    }
}
