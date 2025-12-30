// API base URL
const API_BASE = '/api/v1';

// Utility: Show message notification
function showMessage(message, type = 'success') {
    const container = document.getElementById('message-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    container.appendChild(messageDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        messageDiv.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => messageDiv.remove(), 300);
    }, 5000);
}

// Create Alert Form Handler
document.getElementById('create-alert-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitButton = e.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.classList.add('loading');

    const formData = new FormData(e.target);
    const data = {
        email: formData.get('email'),
        subreddit: formData.get('subreddit'),
        keyword: formData.get('keyword')
    };

    try {
        const response = await fetch(`${API_BASE}/alerts/`, {
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

        // If user loaded their alerts, refresh the list
        const viewEmail = document.getElementById('view-email').value;
        if (viewEmail && viewEmail === data.email) {
            document.getElementById('view-alerts-form').dispatchEvent(new Event('submit'));
        }

    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.classList.remove('loading');
    }
});

// View Alerts Form Handler
document.getElementById('view-alerts-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitButton = e.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.classList.add('loading');

    const email = new FormData(e.target).get('email');

    try {
        const response = await fetch(`${API_BASE}/alerts/?email=${encodeURIComponent(email)}`);

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to load alerts');
        }

        displayAlerts(result.alerts, email);

    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.classList.remove('loading');
    }
});

// Display alerts in the UI
function displayAlerts(alerts, email) {
    const container = document.getElementById('alerts-container');
    const listDiv = document.getElementById('alerts-list');
    const countSpan = document.getElementById('alert-count');

    countSpan.textContent = alerts.length;

    if (alerts.length === 0) {
        listDiv.innerHTML = `
            <div class="empty-state">
                <p>No alerts found for this email.</p>
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
                            <div>Status: ${alert.is_active ? '✅ Active' : '❌ Inactive'}</div>
                        </div>
                    </div>
                    <button class="btn btn-danger" onclick="deleteAlert('${alert.id}', '${escapeHtml(email)}')">
                        Delete
                    </button>
                </div>
            `;
        }).join('');
    }

    container.style.display = 'block';
}

// Delete alert function
async function deleteAlert(alertId, email) {
    if (!confirm('Are you sure you want to delete this alert?')) {
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/alerts/${alertId}?email=${encodeURIComponent(email)}`,
            { method: 'DELETE' }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to delete alert');
        }

        showMessage(result.message, 'success');

        // Reload alerts
        document.getElementById('view-alerts-form').dispatchEvent(new Event('submit'));

    } catch (error) {
        showMessage(error.message, 'error');
    }
}

// Utility: Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-fill view-email from create-email for convenience
document.getElementById('create-email').addEventListener('change', (e) => {
    const viewEmailInput = document.getElementById('view-email');
    if (!viewEmailInput.value) {
        viewEmailInput.value = e.target.value;
    }
});
