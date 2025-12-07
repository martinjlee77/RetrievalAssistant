// Dashboard initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

// Update auth button in navbar based on authentication state
function updateAuthButton(isAuthenticated) {
    const authButton = document.getElementById('authButton');
    if (authButton) {
        authButton.textContent = isAuthenticated ? 'Log Out' : 'Log In';
    }
}

// Handle auth button clicks
function handleAuthButton() {
    const token = localStorage.getItem('authToken');
    if (token && token !== 'null' && token !== 'undefined') {
        // User is logged in - log them out
        logout();
    } else {
        // User is not logged in - redirect to login page
        window.location.href = '/login.html';
    }
}

async function initializeDashboard() {
    const token = localStorage.getItem('authToken');
    
    if (!token || token === 'null' || token === 'undefined') {
        // No valid token - show login form immediately
        showLoginForm();
        return;
    }
    
    // Have valid token - try to fetch user data
    try {
        const response = await fetch('/api/user/profile', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const profileData = await response.json();
            showDashboard(profileData.user);
        } else {
            // Token invalid - clear and show login
            localStorage.removeItem('authToken');
            showLoginForm();
        }
    } catch (error) {
        console.error('Network error:', error);
        // Only show network error if we actually had a token (real network issue)
        showNetworkError();
    }
}

function showLoginForm() {
    // Hide all other sections
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('dashboardSidebar').classList.add('hidden');
    document.getElementById('dashboardMain').classList.add('hidden');
    document.getElementById('verificationSection').classList.add('hidden');
    
    // Show login form
    document.getElementById('loginSection').classList.remove('hidden');
    
    // Update navbar button to show "Log In"
    updateAuthButton(false);
}

function showDashboard(userData) {
    // Hide loading and login
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('loginSection').classList.add('hidden');
    
    // Check email verification status
    if (!userData.email_verified) {
        showVerificationRequired(userData);
        return;
    }
    
    // Hide verification, show dashboard
    document.getElementById('verificationSection').classList.add('hidden');
    document.getElementById('dashboardSidebar').classList.remove('hidden');
    document.getElementById('dashboardMain').classList.remove('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    
    // Update navbar button to show "Log Out"
    updateAuthButton(true);
    
    populateDashboard(userData);
    
    // Check for hash in URL to show specific section
    const hash = window.location.hash.replace('#', '');
    if (hash && ['overview', 'subscription', 'profile', 'history'].includes(hash)) {
        showSection(hash);
    } else {
        showSection('overview');
    }
}

function showVerificationRequired(userData) {
    // Show verification section, hide everything else
    document.getElementById('verificationSection').classList.remove('hidden');
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('dashboardSidebar').classList.add('hidden');
    document.getElementById('dashboardMain').classList.add('hidden');
    if (document.getElementById('mainContent')) {
        document.getElementById('mainContent').classList.add('hidden');
    }
    
    // Update navbar button to show "Log Out" (user is authenticated, just needs verification)
    updateAuthButton(true);
    
    // Display obfuscated email
    const email = userData.email;
    const [localPart, domain] = email.split('@');
    const obfuscatedLocal = localPart.charAt(0) + '*'.repeat(Math.max(0, localPart.length - 2)) + localPart.slice(-1);
    const obfuscatedEmail = `${obfuscatedLocal}@${domain}`;
    document.getElementById('verificationEmail').textContent = obfuscatedEmail;
    
    // Start auto-check polling (every 10 seconds)
    startVerificationPolling();
}

let verificationPollInterval = null;

function startVerificationPolling() {
    // Clear any existing polling
    if (verificationPollInterval) {
        clearInterval(verificationPollInterval);
    }
    
    // Start polling every 10 seconds
    verificationPollInterval = setInterval(async () => {
        try {
            const token = localStorage.getItem('authToken');
            const response = await fetch('/api/user/profile', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.user.email_verified) {
                    // Email verified! Stop polling and show dashboard
                    clearInterval(verificationPollInterval);
                    showVerificationMessage('✅ Email verified! Loading your dashboard...', 'success');
                    setTimeout(() => {
                        showDashboard(data.user);
                    }, 1500);
                }
            }
        } catch (error) {
            console.error('Verification polling error:', error);
        }
    }, 10000);
}

async function resendVerification() {
    const resendBtn = document.getElementById('resendBtn');
    const originalText = resendBtn.textContent;
    
    try {
        resendBtn.disabled = true;
        resendBtn.textContent = 'Sending...';
        
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/resend-verification', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showVerificationMessage('✅ ' + data.message, 'success');
            
            // Disable resend button for 60 seconds (cooldown)
            let countdown = 60;
            const countdownInterval = setInterval(() => {
                resendBtn.textContent = `Wait ${countdown}s`;
                countdown--;
                
                if (countdown < 0) {
                    clearInterval(countdownInterval);
                    resendBtn.disabled = false;
                    resendBtn.textContent = originalText;
                }
            }, 1000);
            
        } else {
            showVerificationMessage('⚠️ ' + data.error, 'error');
            resendBtn.disabled = false;
            resendBtn.textContent = originalText;
        }
        
    } catch (error) {
        console.error('Resend verification error:', error);
        showVerificationMessage('❌ Network error. Please try again.', 'error');
        resendBtn.disabled = false;
        resendBtn.textContent = originalText;
    }
}

async function checkVerificationStatus() {
    const refreshBtn = document.getElementById('refreshBtn');
    const originalText = refreshBtn.textContent;
    
    try {
        refreshBtn.disabled = true;
        refreshBtn.textContent = '🔄 Checking...';
        
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/user/profile', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.user.email_verified) {
                showVerificationMessage('✅ Email verified! Loading your dashboard...', 'success');
                setTimeout(() => {
                    showDashboard(data.user);
                }, 1500);
            } else {
                showVerificationMessage('⏳ Email not yet verified. Please check your inbox and click the verification link.', 'info');
                refreshBtn.disabled = false;
                refreshBtn.textContent = originalText;
            }
        } else {
            showVerificationMessage('❌ Failed to check verification status.', 'error');
            refreshBtn.disabled = false;
            refreshBtn.textContent = originalText;
        }
        
    } catch (error) {
        console.error('Check verification error:', error);
        showVerificationMessage('❌ Network error. Please try again.', 'error');
        refreshBtn.disabled = false;
        refreshBtn.textContent = originalText;
    }
}

function showVerificationMessage(message, type) {
    const container = document.getElementById('verificationMessage');
    const messageDiv = document.createElement('div');
    messageDiv.className = `${type}-message`;
    messageDiv.textContent = message;
    container.innerHTML = '';
    container.appendChild(messageDiv);
}

// Stop polling when page is unloaded
window.addEventListener('beforeunload', () => {
    if (verificationPollInterval) {
        clearInterval(verificationPollInterval);
    }
});

function showNetworkError() {
    // Hide all sections
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('dashboardSidebar').classList.add('hidden');
    document.getElementById('dashboardMain').classList.add('hidden');
    if (document.getElementById('mainContent')) {
        document.getElementById('mainContent').classList.add('hidden');
    }
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('verificationSection').classList.add('hidden');
    
    const errorContainer = document.createElement('div');
    errorContainer.className = 'network-error-container';
    errorContainer.innerHTML = `
        <div class="network-error">
            <h2>⚠️ Connection Error</h2>
            <p>Unable to connect to the server. Please check your internet connection and try again.</p>
            <button onclick="retryConnection()" class="btn btn-primary">Try Again</button>
        </div>
    `;
    document.getElementById('dashboardContent').appendChild(errorContainer);
}

function retryConnection() {
    const errorContainers = document.querySelectorAll('.network-error-container');
    errorContainers.forEach(container => container.remove());
    document.getElementById('loadingState').style.display = 'flex';
    initializeDashboard();
}

// Handle login form submission
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('dashboardLoginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
});

async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    const loginButton = document.getElementById('loginButton');
    const messageContainer = document.getElementById('loginMessage');
    
    if (!email) {
        showLoginMessage('Please enter your email address', 'error');
        return;
    }
    
    if (!password) {
        showLoginMessage('Please enter your password', 'error');
        return;
    }
    
    // Show loading state
    loginButton.disabled = true;
    loginButton.textContent = 'Signing In...';
    messageContainer.innerHTML = '';
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email, password: password })
        });

        if (response.ok) {
            const data = await response.json();
            
            // Store auth token
            localStorage.setItem('authToken', data.token);
            
            // Show success message briefly
            showLoginMessage('Login successful! Loading dashboard...', 'success');
            
            // Load dashboard after short delay
            setTimeout(() => {
                showDashboard(data.user);
            }, 1000);
            
        } else {
            const errorData = await response.json();
            showLoginMessage(errorData.error || 'Login failed. Please try again.', 'error');
        }
        
    } catch (error) {
        console.error('Login error:', error);
        showLoginMessage('Network error. Please check your connection and try again.', 'error');
    } finally {
        // Reset loading state
        loginButton.disabled = false;
        loginButton.textContent = 'Sign In';
    }
}

function showLoginMessage(message, type) {
    const container = document.getElementById('loginMessage');
    const messageDiv = document.createElement('div');
    messageDiv.className = `${type}-message`;
    messageDiv.textContent = message;
    container.innerHTML = '';
    container.appendChild(messageDiv);
}

async function populateDashboard(userData) {
    // Store userData globally for access in other functions
    window.currentUserData = userData;
    
    // Update welcome section (backend returns snake_case fields)
    document.getElementById('userName').textContent = userData.first_name || 'User';
    document.getElementById('memberSince').textContent = userData.member_since ? `Member since ${new Date(userData.member_since).toLocaleDateString()}` : 'Member since —';
    
    // Update profile information
    document.getElementById('userFirstName').textContent = userData.first_name || '-';
    document.getElementById('userLastName').textContent = userData.last_name || '-';
    document.getElementById('userEmail').textContent = userData.email || '-';
    document.getElementById('userCompany').textContent = userData.company_name || '-';
    document.getElementById('memberSinceDate').textContent = userData.member_since ? new Date(userData.member_since).toLocaleDateString() : '—';
    
    // Add organization role badge
    const roleElement = document.getElementById('userRole');
    if (roleElement) {
        const isOwner = userData.role === 'owner';
        roleElement.innerHTML = isOwner ? '🔑 Organization Owner' : '👤 Organization Member';
        roleElement.className = isOwner ? 'role-badge owner' : 'role-badge member';
    }
    
    // Pre-fill edit profile form
    document.getElementById('editFirstName').value = userData.first_name || '';
    document.getElementById('editLastName').value = userData.last_name || '';
    
    // Load subscription data
    await loadSubscriptionData();
    
    // Load usage statistics
    await loadUsageStatistics();
    
    // Load recent analyses
    await loadAnalysisHistory();
}

async function loadUsageStatistics() {
    const totalAnalysesEl = document.getElementById('totalAnalyses');
    const thisMonthEl = document.getElementById('thisMonth');
    const sinceInceptionEl = document.getElementById('sinceInception');
    
    // Show loading state
    totalAnalysesEl.textContent = '...';
    thisMonthEl.textContent = '...';
    sinceInceptionEl.textContent = '...';
    
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/user/usage-stats', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                // Update usage statistics
                totalAnalysesEl.textContent = data.stats.total_analyses;
                thisMonthEl.textContent = data.stats.analyses_this_month;
                sinceInceptionEl.textContent = data.stats.total_analyses;
            }
        } else {
            console.error('Failed to load usage statistics');
            totalAnalysesEl.textContent = '0';
            thisMonthEl.textContent = '0';
            sinceInceptionEl.textContent = '0';
        }
    } catch (error) {
        console.error('Error loading usage statistics:', error);
        totalAnalysesEl.textContent = '0';
        thisMonthEl.textContent = '0';
        sinceInceptionEl.textContent = '0';
    }
}

async function loadAnalysisHistory() {
    const container = document.getElementById('recentAnalysesList');
    
    // Show loading state
    container.innerHTML = '<div class="loading-history"><p>Loading analysis history...</p></div>';
    
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/user/analysis-history', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                loadRecentAnalyses(data.analyses);
            }
        } else {
            console.error('Failed to load analysis history');
            // Show empty state on error
            container.innerHTML = '<div class="empty-state"><div>📄</div><p>No analyses yet. Ready to get started?</p><a href="/analysis" class="btn btn--secondary" target="_blank">Run Your First Analysis</a></div>';
        }
    } catch (error) {
        console.error('Error loading analysis history:', error);
        // Show empty state on error
        container.innerHTML = '<div class="empty-state"><div>📄</div><p>No analyses yet. Ready to get started?</p><a href="/analysis" class="btn btn--secondary" target="_blank">Run Your First Analysis</a></div>';
    }
}

async function loadSubscriptionData() {
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/subscription/status', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                updateSubscriptionUI(data);
            }
        } else {
            console.error('Failed to load subscription data');
            showNoSubscriptionState();
        }
    } catch (error) {
        console.error('Error loading subscription data:', error);
        showNoSubscriptionState();
    }
}

function updateSubscriptionUI(data) {
    const sub = data.subscription;
    
    // Calculate word usage
    const wordsUsed = sub.words_used || 0;
    const wordsAllowed = sub.word_allowance || 0;
    const wordsRemaining = Math.max(0, wordsAllowed - wordsUsed);
    const usagePercent = wordsAllowed > 0 ? Math.min(100, (wordsUsed / wordsAllowed) * 100) : 0;
    
    // Update overview section subscription card
    // Check if subscription period has expired
    const periodEnd = new Date(sub.current_period_end);
    const now = new Date();
    const isPeriodExpired = periodEnd < now;
    
    if (sub.status === 'trial') {
        const daysLeft = Math.ceil((new Date(sub.trial_end_date) - now) / (1000 * 60 * 60 * 24));
        document.getElementById('planName').textContent = `${sub.plan_name} (Trial)`;
        document.getElementById('planStatus').textContent = `${daysLeft} days remaining`;
        document.getElementById('planStatus').className = 'plan-status trial';
        
        const trialEnd = new Date(sub.trial_end_date).toLocaleDateString();
        document.getElementById('renewalInfo').textContent = `Trial ends ${trialEnd}`;
    } else if (sub.status === 'active' && sub.cancel_at_period_end) {
        // Subscription is active but will cancel at period end
        const daysLeft = Math.ceil((periodEnd - now) / (1000 * 60 * 60 * 24));
        document.getElementById('planName').textContent = sub.plan_name;
        document.getElementById('planStatus').textContent = `Cancelling - ${daysLeft} days left`;
        document.getElementById('planStatus').className = 'plan-status cancelling';
        
        const endsDate = periodEnd.toLocaleDateString();
        document.getElementById('renewalInfo').textContent = `Access ends ${endsDate}`;
    } else if (sub.status === 'active') {
        document.getElementById('planName').textContent = sub.plan_name;
        document.getElementById('planStatus').textContent = 'Active';
        document.getElementById('planStatus').className = 'plan-status active';
        
        const nextBilling = periodEnd.toLocaleDateString();
        document.getElementById('renewalInfo').textContent = `Next billing: ${nextBilling}`;
    } else if (sub.status === 'past_due') {
        document.getElementById('planName').textContent = sub.plan_name;
        document.getElementById('planStatus').textContent = 'Payment Failed';
        document.getElementById('planStatus').className = 'plan-status past-due';
        
        document.getElementById('renewalInfo').textContent = 'Please update payment method';
    } else if (sub.status === 'cancelled' || sub.status === 'expired') {
        // Fully cancelled or expired subscription
        document.getElementById('planName').textContent = sub.plan_name;
        if (isPeriodExpired) {
            document.getElementById('planStatus').textContent = 'Expired';
            document.getElementById('planStatus').className = 'plan-status expired';
            document.getElementById('renewalInfo').textContent = 'Subscription ended - Please resubscribe';
        } else {
            const daysLeft = Math.ceil((periodEnd - now) / (1000 * 60 * 60 * 24));
            document.getElementById('planStatus').textContent = `Cancelled - ${daysLeft} days left`;
            document.getElementById('planStatus').className = 'plan-status cancelled';
            document.getElementById('renewalInfo').textContent = `Access ends ${periodEnd.toLocaleDateString()}`;
        }
    }
    
    // Update word allowance display in overview
    const wordsRemainingEl = document.getElementById('wordsRemaining');
    if (wordsRemainingEl) {
        wordsRemainingEl.innerHTML = `<span class="number">${wordsRemaining.toLocaleString()}</span> words remaining`;
    }
    
    const wordsTotalEl = document.getElementById('wordsTotal');
    if (wordsTotalEl) {
        wordsTotalEl.textContent = `of ${wordsAllowed.toLocaleString()} total`;
    }
    
    // Update detailed subscription section
    const currentPlanBadge = document.getElementById('currentPlanBadge');
    if (currentPlanBadge) {
        if (sub.status === 'trial') {
            currentPlanBadge.textContent = `${sub.plan_name} - Free Trial`;
        } else {
            currentPlanBadge.textContent = sub.plan_name;
        }
    }
    
    const currentPlanPrice = document.getElementById('currentPlanPrice');
    if (currentPlanPrice && sub.plan_price) {
        currentPlanPrice.textContent = `$${sub.plan_price}/month`;
    }
    
    const wordsUsedStat = document.getElementById('wordsUsedStat');
    if (wordsUsedStat) {
        wordsUsedStat.textContent = `${wordsUsed.toLocaleString()} words used`;
    }
    
    const wordsAvailableStat = document.getElementById('wordsAvailableStat');
    if (wordsAvailableStat) {
        wordsAvailableStat.textContent = `${wordsRemaining.toLocaleString()} words available`;
    }
    
    // Add shared organization usage message
    const orgUsageMessage = document.getElementById('orgUsageMessage');
    if (orgUsageMessage && window.currentUserData) {
        const userEmail = window.currentUserData.email || '';
        const domain = userEmail.split('@')[1] || 'your organization';
        orgUsageMessage.innerHTML = `📊 <strong>Organization Usage:</strong> ${wordsUsed.toLocaleString()} / ${wordsAllowed.toLocaleString()} words<br><small style="color: #888;">(Shared across all @${domain} users)</small>`;
        orgUsageMessage.style.display = 'block';
    }
    
    // Update usage bar
    const usageBar = document.getElementById('usageBar');
    if (usageBar) {
        usageBar.style.width = `${usagePercent}%`;
        
        // Color code the usage bar
        if (usagePercent >= 90) {
            usageBar.className = 'usage-bar critical';
        } else if (usagePercent >= 75) {
            usageBar.className = 'usage-bar warning';
        } else {
            usageBar.className = 'usage-bar normal';
        }
    }
    
    // Update plan features in subscription section
    const featuresEl = document.getElementById('currentPlanFeatures');
    if (featuresEl) {
        let planFeatures;
        
        // Check if user is on trial - show trial-specific features
        if (sub.status === 'trial') {
            planFeatures = [
                '20,000 words (trial period)',
                'All ASC standards',
                'Standard support',
                'Full platform access'
            ];
        } else {
            // Active subscription - show plan-specific features
            const features = {
                'professional': [
                    '150,000 words/month',
                    'All ASC standards',
                    'Standard support',
                    'Rollover unused words (12 months)'
                ],
                'team': [
                    '400,000 words/month',
                    'All ASC standards',
                    'Priority support',
                    'Rollover unused words (12 months)',
                ],
                'enterprise': [
                    '1,000,000 words/month',
                    'All ASC standards',
                    'Dedicated support',
                    'Rollover unused words (12 months)',
                ]
            };
            
            planFeatures = features[sub.plan_key] || [];
        }
        
        if (planFeatures.length > 0) {
            featuresEl.innerHTML = planFeatures.map(feature => `
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    <span>${feature}</span>
                </div>
            `).join('');
        } else {
            // Fallback for unknown plan types
            featuresEl.innerHTML = `
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    <span>${sub.word_allowance ? sub.word_allowance.toLocaleString() : '0'} words/month</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    <span>All ASC standards</span>
                </div>
            `;
        }
    }
}

function showNoSubscriptionState() {
    // Show default empty state
    document.getElementById('planName').textContent = 'No Active Plan';
    document.getElementById('planStatus').textContent = 'Inactive';
    document.getElementById('planStatus').className = 'plan-status inactive';
    document.getElementById('renewalInfo').textContent = 'Subscribe to get started';
    
    const wordsRemainingEl = document.getElementById('wordsRemaining');
    if (wordsRemainingEl) {
        wordsRemainingEl.innerHTML = '<span class="number">0</span> words remaining';
    }
    
    const wordsTotalEl = document.getElementById('wordsTotal');
    if (wordsTotalEl) {
        wordsTotalEl.textContent = 'of 0 total';
    }
    
    const sinceInceptionEl = document.getElementById('sinceInception');
    if (sinceInceptionEl) {
        sinceInceptionEl.textContent = '0';
    }
    
    const currentPlanBadge = document.getElementById('currentPlanBadge');
    if (currentPlanBadge) {
        currentPlanBadge.textContent = 'No Plan';
    }
    
    const currentPlanPrice = document.getElementById('currentPlanPrice');
    if (currentPlanPrice) {
        currentPlanPrice.textContent = '$0/month';
    }
    
    const wordsUsedStat = document.getElementById('wordsUsedStat');
    if (wordsUsedStat) {
        wordsUsedStat.textContent = '0 words used';
    }
    
    const wordsAvailableStat = document.getElementById('wordsAvailableStat');
    if (wordsAvailableStat) {
        wordsAvailableStat.textContent = '0 words available';
    }
    
    const usageBar = document.getElementById('usageBar');
    if (usageBar) {
        usageBar.style.width = '0%';
    }
}

// Subscription Management Functions
async function upgradeToPlan(planKey) {
    // Check if user is organization owner
    if (window.currentUserData && window.currentUserData.role !== 'owner') {
        const ownerEmail = window.currentUserData.owner_email || 'your organization owner';
        alert(`Only organization owners can manage billing.\n\nContact ${ownerEmail} to upgrade or update payment methods.`);
        return;
    }
    
    const planNames = {
        'professional': 'Professional',
        'team': 'Team',
        'enterprise': 'Enterprise'
    };
    
    const planName = planNames[planKey] || planKey;
    
    // Handle Enterprise differently - contact sales instead of self-service checkout
    if (planKey === 'enterprise') {
        window.location.href = 'contact.html?inquiry=enterprise-sales';
        return;
    }
    
    if (!confirm(`Upgrade to ${planName} plan? Your trial will end and billing will begin immediately.`)) {
        return;
    }
    
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/subscription/upgrade', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ plan_key: planKey })
        });
        
        const data = await response.json();
        
        if (response.ok && data.checkout_url) {
            // Redirect to Stripe checkout page
            window.location.href = data.checkout_url;
        } else {
            alert(`Failed to upgrade: ${data.error || data.message || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Upgrade error:', error);
        alert('Network error. Please try again.');
    }
}

// Helper function to check owner permissions for billing actions
function checkOwnerPermission(actionLabel) {
    if (window.currentUserData && window.currentUserData.role !== 'owner') {
        const ownerEmail = window.currentUserData.owner_email || 'your organization owner';
        alert(`Only organization owners can ${actionLabel}.\n\nContact ${ownerEmail} to manage billing and subscriptions.`);
        return false;
    }
    return true;
}

// Helper function to handle backend permission errors
function handlePermissionError(data) {
    if (data.error === 'permission_denied' && data.owner_email) {
        alert(`Only organization owners can access this feature.\n\nContact ${data.owner_email} to manage billing and subscriptions.`);
        return true;
    }
    return false;
}

async function updatePaymentMethod() {
    // Check if user is organization owner
    if (!checkOwnerPermission('update payment methods')) {
        return;
    }
    
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/subscription/customer-portal', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.url) {
            // Redirect to Stripe Customer Portal
            window.location.href = data.url;
        } else {
            // Check for permission error first
            if (handlePermissionError(data)) {
                return;
            }
            
            // Show helpful error message if Customer Portal not configured
            const errorMsg = data.error || 'Unknown error';
            if (errorMsg.includes('configuration') || errorMsg.includes('Customer Portal')) {
                alert('Stripe Customer Portal is not yet configured. Please contact support at support@veritaslogic.ai');
            } else {
                alert(`Failed to access billing portal: ${errorMsg}`);
            }
        }
    } catch (error) {
        console.error('Update payment method error:', error);
        alert('Network error. Please try again.');
    }
}

async function viewInvoiceHistory() {
    // Check if user is organization owner
    if (!checkOwnerPermission('view invoice history')) {
        return;
    }
    
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/subscription/invoices', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            displayInvoiceModal(data.invoices);
        } else {
            // Check for permission error first
            if (handlePermissionError(data)) {
                return;
            }
            
            alert(`Failed to retrieve invoices: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('View invoice history error:', error);
        alert('Network error. Please try again.');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function displayInvoiceModal(invoices) {
    // Create modal overlay
    const modalHTML = `
        <div id="invoiceModal" class="modal-overlay" onclick="closeInvoiceModal(event)">
            <div class="modal-content invoice-modal" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>Invoice History</h3>
                    <button class="modal-close" onclick="closeInvoiceModal()">&times;</button>
                </div>
                <div class="modal-body">
                    ${invoices.length === 0 ? 
                        '<div class="empty-state"><p>No invoices found.</p></div>' :
                        `<table class="invoice-table">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Description</th>
                                    <th>Amount</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${invoices.map(invoice => `
                                    <tr>
                                        <td>${escapeHtml(new Date(invoice.created * 1000).toLocaleDateString())}</td>
                                        <td>${escapeHtml(invoice.description || 'Subscription')}</td>
                                        <td>$${(invoice.amount_paid || 0).toFixed(2)} ${escapeHtml(invoice.currency)}</td>
                                        <td><span class="invoice-status ${escapeHtml(invoice.status)}">${escapeHtml(invoice.status)}</span></td>
                                        <td>
                                            ${invoice.invoice_pdf ? 
                                                `<a href="${escapeHtml(invoice.invoice_pdf)}" target="_blank" class="btn btn-small">Download PDF</a>` :
                                                `<a href="${escapeHtml(invoice.hosted_invoice_url)}" target="_blank" class="btn btn-small">View Invoice</a>`
                                            }
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>`
                    }
                </div>
            </div>
        </div>
    `;
    
    // Append modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeInvoiceModal(event) {
    const modal = document.getElementById('invoiceModal');
    if (modal && (!event || event.target === modal || event.target.classList.contains('modal-close'))) {
        modal.remove();
    }
}

async function cancelSubscription() {
    // Check if user is organization owner
    if (!checkOwnerPermission('cancel subscription')) {
        return;
    }
    
    // Redirect to Stripe Customer Portal for subscription management
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/subscription/customer-portal', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.url) {
            // Redirect to Stripe Customer Portal where they can cancel
            window.location.href = data.url;
        } else {
            // Check for permission error first
            if (handlePermissionError(data)) {
                return;
            }
            
            // Show helpful error message if Customer Portal not configured
            const errorMsg = data.error || 'Unknown error';
            if (errorMsg.includes('configuration') || errorMsg.includes('Customer Portal')) {
                alert('Stripe Customer Portal is not yet configured. Please contact support at support@veritaslogic.ai');
            } else {
                alert(`Failed to access billing portal: ${errorMsg}`);
            }
        }
    } catch (error) {
        console.error('Cancel subscription error:', error);
        alert('Network error. Please try again.');
    }
}

function loadRecentAnalyses(analyses) {
    const container = document.getElementById('recentAnalysesList');
    
    if (analyses.length === 0) {
        container.innerHTML = '<div class="empty-state"><div>📄</div><p>No analyses yet. Ready to get started?</p><a href="/analysis" class="btn btn--secondary" target="_blank">Run Your First Analysis</a></div>';
        return;
    }
    
    // Create table structure
    container.innerHTML = `
        <table class="analysis-table">
            <thead>
                <tr>
                    <th>Date Completed</th>
                    <th>ASC Standard</th>
                    <th>Document Size</th>
                    <th>Files</th>
                    <th>Memo</th>
                </tr>
            </thead>
            <tbody id="analysisTableBody">
            </tbody>
        </table>
    `;
    
    const tbody = document.getElementById('analysisTableBody');
    analyses.forEach(analysis => {
        // Backend /analysis route will query DB and redirect to correct page
        const viewUrl = `/analysis?analysis_id=${analysis.analysis_id}`;
        
        const row = document.createElement('tr');
        const isReview = analysis.analysis_type === 'review';
        const standardLabel = isReview 
            ? `${analysis.asc_standard} <span class="badge-review">Review</span>` 
            : `${analysis.asc_standard} <span class="badge-analysis">Analysis</span>`;
        row.innerHTML = `
            <td>${new Date(analysis.created_at).toLocaleDateString()}</td>
            <td>${standardLabel}</td>
            <td>${analysis.words_count ? analysis.words_count.toLocaleString() + ' words' : 'N/A'}</td>
            <td>${analysis.file_count || 0}</td>
            <td><a href="${viewUrl}" target="_blank" class="btn btn-primary btn-sm">View</a></td>
        `;
        tbody.appendChild(row);
    });
}

// Sidebar navigation functions
function showSection(sectionName) {
    // Hide all sections
    const sections = document.querySelectorAll('.dashboard-section');
    sections.forEach(section => section.classList.remove('active'));
    
    // Remove active class from all nav items
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => item.classList.remove('active'));
    
    // Show selected section
    const targetSection = document.getElementById(sectionName + 'Section');
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // Add active class to corresponding nav item
    const targetNav = document.querySelector(`[onclick="showSection('${sectionName}')"]`);
    if (targetNav) {
        targetNav.classList.add('active');
    }
    
    // Load section-specific data
    if (sectionName === 'credits') {
        loadCreditPackages();
    } else if (sectionName === 'history') {
        loadAnalysisHistory();
    }
    
    // Update URL hash
    window.location.hash = sectionName;
}

// Custom amount functionality
function selectCustomAmount() {
    const customAmount = document.getElementById('customAmount').value;
    const amount = parseFloat(customAmount);
    
    if (!amount || amount < 195 || amount > 3000) {
        alert('Please enter an amount between $195 and $3,000');
        return;
    }
    
    selectPackage(amount);
}

// Update showCreditPurchase to work with new layout
function showCreditPurchase() {
    showSection('credits');
}

// Profile update functionality
async function updateProfile(firstName, lastName) {
    try {
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/user/update-profile', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                first_name: firstName,
                last_name: lastName
            })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                // Update UI with new names
                document.getElementById('userName').textContent = firstName;
                document.getElementById('userFirstName').textContent = firstName;
                document.getElementById('userLastName').textContent = lastName;
                
                showEditProfileMessage('Profile updated successfully!', 'success');
                
                // Clear form
                document.getElementById('editProfileForm').reset();
            } else {
                showEditProfileMessage(data.error || 'Failed to update profile', 'error');
            }
        } else {
            const errorData = await response.json();
            showEditProfileMessage(errorData.error || 'Failed to update profile', 'error');
        }
    } catch (error) {
        console.error('Profile update error:', error);
        showEditProfileMessage('Network error. Please try again.', 'error');
    }
}

function showEditProfileMessage(message, type) {
    const container = document.getElementById('editProfileMessage');
    if (container) {
        container.innerHTML = `<div class="${type}-message">${message}</div>`;
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Profile form submission handler
async function submitProfileUpdate(event) {
    event.preventDefault();
    
    const firstName = document.getElementById('editFirstName').value.trim();
    const lastName = document.getElementById('editLastName').value.trim();
    const button = document.getElementById('updateProfileButton');
    
    if (!firstName || !lastName) {
        showEditProfileMessage('Please enter both first and last name', 'error');
        return;
    }
    
    // Show loading state
    button.disabled = true;
    button.textContent = 'Updating...';
    
    try {
        await updateProfile(firstName, lastName);
    } finally {
        button.disabled = false;
        button.textContent = 'Update Name';
    }
}

function logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    window.location.href = 'login.html';
}

// Password strength validation function
function validatePasswordStrength(password) {
    const requirements = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };
    
    // Update visual indicators
    const lengthEl = document.getElementById('req-length');
    const uppercaseEl = document.getElementById('req-uppercase');
    const lowercaseEl = document.getElementById('req-lowercase');
    const numberEl = document.getElementById('req-number');
    const specialEl = document.getElementById('req-special');
    
    if (lengthEl) lengthEl.className = requirements.length ? 'valid' : '';
    if (uppercaseEl) uppercaseEl.className = requirements.uppercase ? 'valid' : '';
    if (lowercaseEl) lowercaseEl.className = requirements.lowercase ? 'valid' : '';
    if (numberEl) numberEl.className = requirements.number ? 'valid' : '';
    if (specialEl) specialEl.className = requirements.special ? 'valid' : '';
    
    return Object.values(requirements).every(req => req);
}

function showChangePasswordMessage(message, type) {
    const container = document.getElementById('changePasswordMessage');
    if (container) {
        container.innerHTML = `<div class="${type}-message">${message}</div>`;
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Initialize change password functionality
setTimeout(() => {
    // Real-time password validation
    const newPasswordInput = document.getElementById('newPassword');
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function(e) {
            validatePasswordStrength(e.target.value);
        });
    }
    
    // Password confirmation validation
    const confirmPasswordInput = document.getElementById('confirmNewPassword');
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function(e) {
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = e.target.value;
            const feedback = document.getElementById('password-match');
            
            if (!feedback) return;
            
            if (confirmPassword === '') {
                feedback.textContent = '';
                feedback.className = 'password-feedback';
            } else if (newPassword === confirmPassword) {
                feedback.textContent = '✓ Passwords match';
                feedback.className = 'password-feedback valid';
            } else {
                feedback.textContent = '✗ Passwords do not match';
                feedback.className = 'password-feedback invalid';
            }
        });
    }
    
    // Change password form submission
    const changePasswordForm = document.getElementById('changePasswordForm');
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const currentPassword = document.getElementById('currentPassword').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmNewPassword = document.getElementById('confirmNewPassword').value;
            const submitButton = document.getElementById('changePasswordButton');
            
            // Validate passwords match
            if (newPassword !== confirmNewPassword) {
                showChangePasswordMessage('Passwords do not match', 'error');
                return;
            }
            
            // Validate password strength
            if (!validatePasswordStrength(newPassword)) {
                showChangePasswordMessage('Password does not meet the requirements', 'error');
                return;
            }
            
            // Show loading state
            submitButton.disabled = true;
            submitButton.textContent = 'Updating Password...';
            
            try {
                const token = localStorage.getItem('authToken');
                const response = await fetch('/api/change-password', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        current_password: currentPassword,
                        new_password: newPassword
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showChangePasswordMessage('Password has been updated successfully!', 'success');
                    // Clear form
                    changePasswordForm.reset();
                    // Clear password match feedback
                    const feedback = document.getElementById('password-match');
                    if (feedback) {
                        feedback.textContent = '';
                        feedback.className = 'password-feedback';
                    }
                } else {
                    showChangePasswordMessage(result.error || 'Password change failed. Please try again.', 'error');
                }
                
            } catch (error) {
                console.error('Change password error:', error);
                showChangePasswordMessage('Network error. Please check your connection and try again.', 'error');
            } finally {
                // Reset loading state
                submitButton.disabled = false;
                submitButton.textContent = 'Update Password';
            }
        });
    }
}, 100);

// Stripe Payment Integration
let stripe = null;
let elements = null;
let cardElement = null;
let selectedAmount = 0;

async function initializeStripe() {
    try {
        const response = await fetch('/api/stripe/config');
        const { publishable_key } = await response.json();
        stripe = Stripe(publishable_key);
        
        elements = stripe.elements({
            appearance: {
                theme: 'stripe',
                variables: {
                    colorPrimary: '#667eea',
                    colorBackground: '#ffffff',
                    colorText: '#30313d',
                    colorDanger: '#df1b41',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    spacingUnit: '2px',
                    borderRadius: '8px',
                }
            }
        });
        
        cardElement = elements.create('card');
        cardElement.on('change', ({error}) => {
            const displayError = document.getElementById('card-errors');
            if (error) {
                displayError.textContent = error.message;
            } else {
                displayError.textContent = '';
            }
        });
        
    } catch (error) {
        console.error('Failed to initialize Stripe:', error);
        showPaymentMessage('Failed to initialize payment system', 'error');
    }
}



async function selectPackage(amount) {
    selectedAmount = amount;
    
    document.getElementById('selectedPackageDisplay').innerHTML = `
        <div class="selected-package-info">
            <h4>Selected Package: $${amount.toLocaleString()} Credits</h4>
            <p>You will be charged $${amount.toLocaleString()} USD.</p>
        </div>
    `;
    
    // Remove the 'hidden' class instead of trying to override with inline style
    const paymentContainer = document.getElementById('paymentFormContainer');
    paymentContainer.classList.remove('hidden');
    
    // Initialize Stripe if not already done
    if (!stripe) {
        await initializeStripe();
    }
    
    // Mount card element (track our own mounted state)
    if (cardElement && !cardElement.isCardMounted) {
        try {
            cardElement.mount('#card-element');
            cardElement.isCardMounted = true;
        } catch (error) {
            console.error('Error mounting card element:', error);
            showPaymentMessage('Failed to load payment form', 'error');
        }
    }
    
    // Scroll to payment form
    paymentContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function cancelPayment() {
    document.getElementById('paymentFormContainer').classList.add('hidden');
    selectedAmount = 0;
}

async function handlePayment(event) {
    event.preventDefault();
    
    const submitButton = document.getElementById('submit-payment');
    const buttonText = document.getElementById('button-text');
    
    submitButton.disabled = true;
    buttonText.textContent = 'Processing...';
    
    try {
        // Create payment intent
        const token = localStorage.getItem('authToken');
        const response = await fetch('/api/stripe/create-payment-intent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ amount: selectedAmount })
        });
        
        const { client_secret } = await response.json();
        
        if (!response.ok) {
            throw new Error('Failed to create payment intent');
        }
        
        // Confirm payment with Stripe
        const {error} = await stripe.confirmCardPayment(client_secret, {
            payment_method: {
                card: cardElement
            }
        });
        
        if (error) {
            showPaymentMessage(error.message, 'error');
        } else {
            showPaymentMessage('Payment successful! Updating your balance...', 'success');
            
            // Poll for balance update instead of blind reload
            pollForBalanceUpdate(selectedAmount);
        }
        
    } catch (error) {
        console.error('Payment error:', error);
        showPaymentMessage('Payment failed. Please try again.', 'error');
    } finally {
        submitButton.disabled = false;
        buttonText.textContent = 'Complete Payment';
    }
}

function showPaymentMessage(message, type) {
    const container = document.getElementById('payment-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `${type}-message`;
    messageDiv.textContent = message;
    container.innerHTML = '';
    container.appendChild(messageDiv);
    container.scrollIntoView({ behavior: 'smooth' });
}

async function pollForBalanceUpdate(expectedAmount) {
    const originalBalanceText = document.getElementById('creditsBalance').textContent;
    const originalBalance = Number(originalBalanceText.replace(/[^0-9.-]+/g, '')) || 0;
    const maxAttempts = 30; // Poll for up to 30 seconds (increased from 20)
    let attempts = 0;
    
    console.log(`[Balance Polling] Starting polling for ${expectedAmount} credit payment`);
    console.log(`[Balance Polling] Original balance text: "${originalBalanceText}", parsed: ${originalBalance}`);
    
    const checkBalance = async () => {
        attempts++;
        console.log(`[Balance Polling] Attempt ${attempts}/${maxAttempts}`);
        
        try {
            const token = localStorage.getItem('authToken');
            if (!token) {
                console.error('[Balance Polling] No auth token found');
                return;
            }
            
            const response = await fetch('/api/user/profile', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (!response.ok) {
                console.error(`[Balance Polling] API error: ${response.status} ${response.statusText}`);
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            console.log(`[Balance Polling] Current balance from API: ${data.user?.credits_balance || data.credits_balance || 'undefined'}`);
            
            // Handle both response formats (data.user.credits_balance or data.credits_balance)
            const currentBalance = data.user?.credits_balance ?? data.credits_balance ?? 0;
            
            if (currentBalance > originalBalance) {
                console.log(`[Balance Polling] Balance updated! ${originalBalance} -> ${currentBalance}`);
                // Balance updated! Show success and refresh
                showPaymentMessage(`Success! $${expectedAmount} credits added to your account!`, 'success');
                
                // Update the displayed balance immediately
                const balance = parseFloat(currentBalance);
                const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
                document.getElementById('creditsBalance').textContent = fmt.format(balance);
                
                // Hide payment form and refresh dashboard after delay
                setTimeout(() => {
                    cancelPayment();
                    window.location.reload();
                }, 2000);
                return;
            }
            
            if (attempts < maxAttempts) {
                console.log(`[Balance Polling] Balance not updated yet (${currentBalance} <= ${originalBalance}), retrying...`);
                // Continue polling
                setTimeout(checkBalance, 1000); // Check every second
            } else {
                console.log(`[Balance Polling] Timeout reached (${maxAttempts} attempts), forcing refresh`);
                // Timeout - show message but still refresh
                showPaymentMessage('Payment processed! Refreshing dashboard...', 'success');
                setTimeout(() => {
                    cancelPayment();
                    window.location.reload();
                }, 2000);
            }
        } catch (error) {
            console.error(`[Balance Polling] Error on attempt ${attempts}:`, error);
            if (attempts < maxAttempts) {
                // Retry on error
                setTimeout(checkBalance, 2000); // Wait 2 seconds after error
            } else {
                console.log(`[Balance Polling] Max attempts reached with errors, forcing refresh`);
                showPaymentMessage('Payment processed! Refreshing dashboard...', 'success');
                setTimeout(() => {
                    cancelPayment();
                    window.location.reload();
                }, 2000);
            }
        }
    };
    
    // Start polling after 1 second delay
    setTimeout(checkBalance, 1000);
}

// Platform Status Checking
async function checkPlatformStatus() {
    const analysisPlatformUrl = '/analysis'; // Check through our redirect endpoint
    const statusValue = document.getElementById('analysisPlatformValue');
    const statusDot = document.querySelector('#analysisPlatformStatus .status-dot');
    const launchBtn = document.getElementById('platformLaunchBtn');
    
    // Navigation bar elements
    const navStatusDot = document.getElementById('navStatusDot');
    const navPlatformStatus = document.getElementById('navPlatformStatus');
    const navPlatformLink = document.getElementById('navPlatformLink');
    
    try {
        // Update dashboard status
        if (statusValue) statusValue.textContent = 'Checking...';
        if (statusDot) statusDot.className = 'status-dot checking';
        
        // Update navigation status
        if (navStatusDot) navStatusDot.className = 'nav-status-dot checking';
        if (navPlatformStatus) navPlatformStatus.textContent = 'Checking...';
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch(analysisPlatformUrl, {
            method: 'HEAD',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            // Update dashboard status
            if (statusValue) statusValue.textContent = 'Online';
            if (statusDot) statusDot.className = 'status-dot online';
            if (launchBtn) {
                launchBtn.disabled = false;
                launchBtn.innerHTML = '<span class="nav-icon">auto_awesome</span> Click Here to Start Analysis';
            }
            
            // Update navigation status
            if (navStatusDot) navStatusDot.className = 'nav-status-dot online';
            if (navPlatformStatus) navPlatformStatus.textContent = 'Online';
            if (navPlatformLink) navPlatformLink.classList.remove('platform-unavailable');
            
        } else {
            throw new Error('Platform unavailable');
        }
        
    } catch (error) {
        // Update dashboard status
        if (statusValue) statusValue.textContent = 'Unavailable';
        if (statusDot) statusDot.className = 'status-dot offline';
        if (launchBtn) {
            launchBtn.disabled = true;
            launchBtn.innerHTML = '⚠️ Platform Unavailable';
        }
        
        // Update navigation status
        if (navStatusDot) navStatusDot.className = 'nav-status-dot offline';
        if (navPlatformStatus) navPlatformStatus.textContent = 'Unavailable';
        if (navPlatformLink) navPlatformLink.classList.add('platform-unavailable');
        
        console.warn('Analysis platform status check failed:', error);
        
        // Retry after 30 seconds
        setTimeout(checkPlatformStatus, 30000);
    }
}

// Initialize platform status checking
function initializePlatformStatus() {
    checkPlatformStatus();
    // Check status every 5 minutes
    setInterval(checkPlatformStatus, 300000);
}

// Call platform status check after dashboard is loaded
setTimeout(initializePlatformStatus, 2000);

// Expose functions to global scope for inline onclick handlers
window.selectCustomAmount = selectCustomAmount;
window.selectPackage = selectPackage;
window.cancelPayment = cancelPayment;
window.submitProfileUpdate = submitProfileUpdate;
window.showSection = showSection;
window.handleAuthButton = handleAuthButton;
window.logout = logout;
window.resendVerification = resendVerification;
window.checkVerificationStatus = checkVerificationStatus;
window.upgradeToPlan = upgradeToPlan;
window.updatePaymentMethod = updatePaymentMethod;
window.viewInvoiceHistory = viewInvoiceHistory;
window.cancelSubscription = cancelSubscription;

// Initialize payment form handler
setTimeout(() => {
    const paymentForm = document.getElementById('payment-form');
    if (paymentForm) {
        paymentForm.addEventListener('submit', handlePayment);
    }
}, 100);
