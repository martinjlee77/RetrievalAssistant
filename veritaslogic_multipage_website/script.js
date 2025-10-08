// VeritasLogic.ai Multi-Page Website JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication state and update navigation
    checkAuthenticationState();

    // Mobile Navigation Toggle
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function() {
            navLinks.classList.toggle('mobile-open');
            this.classList.toggle('active');
        });
    }

    // Smooth Scrolling for Anchor Links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            // Skip if href is just "#" (used for buttons/filters)
            if (href === '#' || href.length <= 1) {
                return;
            }
            
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                const navbarHeight = document.querySelector('.navbar').offsetHeight;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navbarHeight - 20;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Active Navigation Link Highlighting - Only for single-page navigation
    function updateActiveNavLink() {
        // Only run on single pages with sections (not multi-page navigation)
        const isMultiPageNav = document.querySelector('.nav-links a[href$=".html"]');
        if (isMultiPageNav) {
            return; // Skip scroll-based active states for multi-page navigation
        }
        
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-links a');
        
        let currentSection = '';
        const scrollPosition = window.pageYOffset + 200;
        
        sections.forEach(section => {
            const sectionTop = section.getBoundingClientRect().top + window.pageYOffset;
            const sectionHeight = section.offsetHeight;
            
            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                currentSection = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            // Only modify active states for anchor links, not page links
            if (link.getAttribute('href').startsWith('#')) {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${currentSection}`) {
                    link.classList.add('active');
                }
            }
        });
    }

    // Update active nav link on scroll (only for single-page navigation)
    window.addEventListener('scroll', updateActiveNavLink);
    
    // Initial call to set active link
    updateActiveNavLink();

    // Navbar Background on Scroll
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // Intersection Observer for Animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // Observe elements for animations
    const animateElements = document.querySelectorAll(
        '.feature-card, .value-card, .pricing-card, .blog-card, .contact-card, .addon-card, .faq-item'
    );
    animateElements.forEach(el => observer.observe(el));

    // Form Validation and Submission
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                return false;
            }
            
            // If validation passes, handle submission
            handleFormSubmission(this, e);
        });
    });

    function validateForm(form) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                showFieldError(field, 'This field is required');
                isValid = false;
            } else {
                clearFieldError(field);
                
                // Email validation
                if (field.type === 'email' && !isValidEmail(field.value)) {
                    showFieldError(field, 'Please enter a valid email address');
                    isValid = false;
                }
            }
        });
        
        return isValid;
    }

    function showFieldError(field, message) {
        clearFieldError(field);
        field.classList.add('error');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }

    function clearFieldError(field) {
        field.classList.remove('error');
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
    }

    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    function handleFormSubmission(form, e) {
        e.preventDefault();
        
        const formId = form.id;
        const submitBtn = form.querySelector('.form-submit');
        const originalBtnText = submitBtn.textContent;
        
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
        
        // Simulate form submission (replace with actual API call)
        setTimeout(() => {
            let message = '';
            
            switch(formId) {
                case 'trial-signup-form':
                    message = 'Thank you for signing up for your free trial! We\'ll send you access credentials within 2 hours during business hours. Check your email for setup instructions.';
                    break;
                case 'demo-request-form':
                    message = 'Thank you for requesting a demo! Our team will contact you within 24 hours to schedule your personalized demonstration.';
                    break;
                case 'enterprise-contact-form':
                    message = 'Thank you for your interest in enterprise solutions! Our sales team will contact you within 24 hours to discuss your requirements.';
                    break;
                case 'academic-contact-form':
                    message = 'Thank you for your academic pricing request! We\'ll review your application and respond within 48 hours with pricing details.';
                    break;
                default:
                    message = 'Thank you for contacting us! We\'ll get back to you as soon as possible.';
            }
            
            showFormSuccess(form, message);
            form.reset();
            
            // Reset button
            submitBtn.disabled = false;
            submitBtn.textContent = originalBtnText;
            
        }, 2000);
    }

    function showFormSuccess(form, message) {
        // Create success message
        const successDiv = document.createElement('div');
        successDiv.className = 'form-success';
        successDiv.innerHTML = `
            <div class="success-icon">✓</div>
            <p>${message}</p>
        `;
        
        // Insert before form
        form.parentNode.insertBefore(successDiv, form);
        
        // Scroll to success message
        successDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Remove success message after 10 seconds
        setTimeout(() => {
            successDiv.remove();
        }, 10000);
    }

    // Demo Interactions (Features Page)
    const demoBtns = document.querySelectorAll('.demo-btn');
    demoBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            showDemoModal();
        });
    });

    function showDemoModal() {
        const modalHTML = `
            <div class="demo-modal-overlay">
                <div class="demo-modal">
                    <div class="modal-header">
                        <h3>Interactive Demo Coming Soon</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-content">
                        <p>Our interactive demo is currently in development. In the meantime, you can:</p>
                        <ul>
                            <li>Sign up for a free trial to test with real contracts</li>
                            <li>Schedule a live demonstration with our team</li>
                            <li>Contact us for a personalized walkthrough</li>
                        </ul>
                        <div class="modal-actions">
                            <a href="contact.html#trial" class="modal-cta">Start Free Trial</a>
                            <a href="contact.html#demo-form" class="modal-secondary">Schedule Demo</a>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Close modal functionality
        const overlay = document.querySelector('.demo-modal-overlay');
        const closeBtn = overlay.querySelector('.modal-close');
        
        closeBtn.addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });
        
        // ESC key to close
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && overlay) {
                overlay.remove();
            }
        });
    }

    // Progress Bar Animation (Features Page)
    const progressBar = document.querySelector('.progress-fill');
    if (progressBar) {
        const progressSection = document.querySelector('.demo-interactive');
        if (progressSection) {
            const progressObserver = new IntersectionObserver(function(entries) {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        setTimeout(() => {
                            progressBar.style.width = '100%';
                        }, 1000);
                    }
                });
            }, { threshold: 0.5 });
            
            progressObserver.observe(progressSection);
        }
    }

    // Category Filtering (Blog Page)
    const categoryLinks = document.querySelectorAll('.blog-filters [data-category]');
    if (categoryLinks.length > 0) {
        categoryLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const category = this.getAttribute('data-category');
                filterBlogPosts(category);
                
                // Update active category
                categoryLinks.forEach(l => l.classList.remove('active'));
                this.classList.add('active');
            });
        });
    }

    function filterBlogPosts(category) {
        const blogPosts = document.querySelectorAll('.blog-post, .featured-post');
        
        blogPosts.forEach(post => {
            if (category === 'all') {
                post.style.display = 'block';
            } else {
                const postCategories = post.querySelector('.post-category, .blog-category');
                if (postCategories && postCategories.textContent.toLowerCase().includes(category.replace('-', ' '))) {
                    post.style.display = 'block';
                } else {
                    post.style.display = 'none';
                }
            }
        });
    }

    // Pricing Calculator (if needed)
    const volumeSelect = document.querySelector('#volume-calculator');
    if (volumeSelect) {
        volumeSelect.addEventListener('change', function() {
            updatePricingCalculation(this.value);
        });
    }

    function updatePricingCalculation(volume) {
        const pricePerAnalysis = getPriceForVolume(volume);
        const totalPrice = pricePerAnalysis * volume;
        
        // Update display elements
        const priceDisplay = document.querySelector('#calculated-price');
        if (priceDisplay) {
            priceDisplay.textContent = `$${pricePerAnalysis} per analysis`;
        }
        
        const totalDisplay = document.querySelector('#calculated-total');
        if (totalDisplay) {
            totalDisplay.textContent = `$${totalPrice} total`;
        }
    }

    function getPriceForVolume(volume) {
        if (volume <= 10) return 49;
        if (volume <= 25) return 44;
        if (volume <= 50) return 39;
        if (volume <= 100) return 34;
        return 29; // Enterprise pricing
    }

    // Testimonial Carousel (if multiple testimonials)
    const testimonialContainer = document.querySelector('.testimonial-carousel');
    if (testimonialContainer) {
        let currentTestimonial = 0;
        const testimonials = testimonialContainer.querySelectorAll('.testimonial-card');
        
        if (testimonials.length > 1) {
            setInterval(() => {
                testimonials[currentTestimonial].classList.remove('active');
                currentTestimonial = (currentTestimonial + 1) % testimonials.length;
                testimonials[currentTestimonial].classList.add('active');
            }, 5000);
        }
    }

    // Reading Progress Indicator (Blog Pages)
    const progressIndicator = document.createElement('div');
    progressIndicator.className = 'reading-progress';
    document.body.appendChild(progressIndicator);

    function updateReadingProgress() {
        const article = document.querySelector('.featured-post, .blog-post');
        if (!article) return;
        
        const articleTop = article.getBoundingClientRect().top + window.pageYOffset;
        const articleHeight = article.offsetHeight;
        const windowHeight = window.innerHeight;
        const scrollTop = window.pageYOffset;
        
        const progress = Math.min(Math.max((scrollTop - articleTop + windowHeight) / articleHeight, 0), 1);
        progressIndicator.style.width = `${progress * 100}%`;
    }

    if (document.querySelector('.featured-post, .blog-post')) {
        window.addEventListener('scroll', updateReadingProgress);
        updateReadingProgress();
    }

    // Email Subscription (Blog Sidebar)
    const subscribeForm = document.querySelector('.subscribe-form');
    if (subscribeForm) {
        subscribeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = this.querySelector('input[type="email"]').value;
            
            if (isValidEmail(email)) {
                // Simulate subscription
                const button = this.querySelector('button');
                const originalText = button.textContent;
                
                button.textContent = 'Subscribing...';
                button.disabled = true;
                
                setTimeout(() => {
                    button.textContent = 'Subscribed!';
                    button.style.background = 'rgba(34, 197, 94, 0.3)';
                    this.reset();
                    
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                        button.style.background = '';
                    }, 3000);
                }, 1500);
            }
        });
    }

    // Copy to Clipboard Functionality
    function addCopyToClipboard() {
        const codeBlocks = document.querySelectorAll('pre, .code-block');
        codeBlocks.forEach(block => {
            const button = document.createElement('button');
            button.textContent = 'Copy';
            button.className = 'copy-btn';
            button.addEventListener('click', () => {
                navigator.clipboard.writeText(block.textContent).then(() => {
                    button.textContent = 'Copied!';
                    setTimeout(() => button.textContent = 'Copy', 2000);
                });
            });
            block.style.position = 'relative';
            block.appendChild(button);
        });
    }

    // Initialize copy functionality if code blocks exist
    if (document.querySelector('pre, .code-block')) {
        addCopyToClipboard();
    }

    // Lazy Loading for Images (if any are added later)
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                imageObserver.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));

    // Analytics Tracking (placeholder for future implementation)
    function trackEvent(eventName, properties = {}) {
        // Placeholder for analytics tracking
        console.log('Event tracked:', eventName, properties);
        
        // Example: Google Analytics 4
        // gtag('event', eventName, properties);
        
        // Example: Mixpanel
        // mixpanel.track(eventName, properties);
    }

    // Track important interactions
    document.querySelectorAll('.hero-cta, .nav-cta').forEach(btn => {
        btn.addEventListener('click', () => {
            trackEvent('cta_clicked', {
                button_text: btn.textContent,
                page: window.location.pathname
            });
        });
    });

    document.querySelectorAll('.pricing-cta').forEach(btn => {
        btn.addEventListener('click', () => {
            trackEvent('pricing_cta_clicked', {
                plan: btn.closest('.pricing-card').querySelector('h3').textContent,
                page: window.location.pathname
            });
        });
    });

    // Error Handling for Form Submissions
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        
        // Show user-friendly error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'global-error';
        errorDiv.innerHTML = `
            <p>Something went wrong. Please try again or contact support if the problem persists.</p>
            <button onclick="this.parentElement.remove()">Dismiss</button>
        `;
        document.body.appendChild(errorDiv);
        
        setTimeout(() => errorDiv.remove(), 10000);
    });

    // Performance Optimization: Debounce Scroll Events
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Apply debouncing to scroll events
    const debouncedScrollHandler = debounce(() => {
        updateActiveNavLink();
        updateReadingProgress();
    }, 16); // ~60fps

    window.addEventListener('scroll', debouncedScrollHandler);

    console.log('VeritasLogic.ai website initialized successfully');
});

// Helper function to get cookie value
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// Authentication state management
async function checkAuthenticationState() {
    // First check for token in localStorage or cookies
    let token = localStorage.getItem('authToken');
    if (!token || token === 'null' || token === 'undefined') {
        token = getCookie('vl_auth_token');
    }
    
    if (!token) {
        return; // Not logged in - keep default nav
    }
    
    // Immediately show authenticated navbar if we have a token
    // This eliminates the flashing delay while background validation runs
    showOptimisticAuthState();
    
    // Verify token is still valid and get user info in background
    try {
        const response = await fetch('/api/user/profile', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const profileData = await response.json();
            updateNavigationForLoggedInUser(profileData.user);
            
            // Store valid token in localStorage for faster future checks
            if (token !== localStorage.getItem('authToken')) {
                localStorage.setItem('authToken', token);
            }
        } else {
            // Token invalid - clear it and revert to guest nav
            localStorage.removeItem('authToken');
            revertToGuestNavigation();
        }
    } catch (error) {
        console.log('Auth check failed:', error);
        // Network error - revert to guest nav for safety
        revertToGuestNavigation();
    }
}

function showOptimisticAuthState() {
    const authButtons = document.querySelector('.nav-auth-buttons');
    if (authButtons) {
        authButtons.innerHTML = `
            <a href="/dashboard.html" class="nav-cta primary">My Account</a>
            <a href="#" onclick="logout(); return false;" class="nav-cta secondary">Sign Out</a>
        `;
        return true;
    }
    return false;
}

function updateNavigationForLoggedInUser(userData) {
    const authButtons = document.querySelector('.nav-auth-buttons');
    if (authButtons) {
        authButtons.innerHTML = `
            <a href="/dashboard.html" class="nav-cta primary">My Account</a>
            <a href="#" onclick="logout(); return false;" class="nav-cta secondary">Sign Out</a>
        `;
    }
}

function revertToGuestNavigation() {
    const authButtons = document.querySelector('.nav-auth-buttons');
    if (authButtons) {
        authButtons.innerHTML = `
            <a href="/contact.html#trial" class="nav-cta primary">Start Risk Free</a>
            <a href="/login.html" class="nav-cta secondary">Log In</a>
        `;
    }
}

function logout() {
    localStorage.removeItem('authToken');
    
    // Clear the cross-domain cookie
    document.cookie = 'vl_auth_token=; path=/; domain=.veritaslogic.ai; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    
    window.location.reload(); // Refresh to show logged-out state
}

// CSS for dynamic elements
const dynamicStyles = `
    .mobile-open {
        display: flex !important;
        flex-direction: column;
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #1A252F 0%, #212F3C 100%);
        border-top: 1px solid rgba(255,255,255,0.1);
        padding: 1rem 0;
    }

    .mobile-menu-btn.active {
        transform: rotate(90deg);
    }

    .navbar.scrolled {
        background: rgba(26, 37, 47, 0.95);
        backdrop-filter: blur(10px);
    }

    .animate-in {
        animation: fadeInUp 0.6s ease forwards;
        opacity: 0;
    }

    .field-error {
        color: #ef4444;
        font-size: 0.875rem;
        margin-top: 0.5rem;
        display: block;
    }

    .form-group input.error,
    .form-group textarea.error,
    .form-group select.error {
        border-color: #ef4444;
        background: rgba(239, 68, 68, 0.1);
    }

    .form-success {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 2rem;
        text-align: center;
        color: #ffffff;
    }

    .success-icon {
        background: rgba(34, 197, 94, 0.2);
        width: 60px;
        height: 60px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        color: #22c55e;
        margin: 0 auto 1rem auto;
    }

    .demo-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 2000;
        padding: 1rem;
    }

    .demo-modal {
        background: linear-gradient(135deg, #212F3C 0%, #2C3E50 100%);
        border-radius: 16px;
        max-width: 600px;
        width: 100%;
        border: 1px solid rgba(255,255,255,0.2);
        overflow: hidden;
    }

    .modal-header {
        padding: 2rem;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .modal-header h3 {
        color: #ffffff;
        margin: 0;
        font-size: 1.5rem;
    }

    .modal-close {
        background: none;
        border: none;
        color: rgba(255,255,255,0.7);
        font-size: 2rem;
        cursor: pointer;
        line-height: 1;
        padding: 0;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .modal-close:hover {
        color: #ffffff;
    }

    .modal-content {
        padding: 2rem;
    }

    .modal-content p {
        color: rgba(255,255,255,0.8);
        line-height: 1.6;
        margin-bottom: 1.5rem;
    }

    .modal-content ul {
        color: rgba(255,255,255,0.8);
        padding-left: 2rem;
        margin-bottom: 2rem;
    }

    .modal-content li {
        margin-bottom: 0.5rem;
    }

    .modal-actions {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .modal-cta,
    .modal-secondary {
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        transition: all 0.3s ease;
        text-align: center;
        flex: 1;
        min-width: 150px;
    }

    .modal-cta {
        background: linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%);
        color: #212F3C;
    }

    .modal-cta:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(255,255,255,0.3);
    }

    .modal-secondary {
        background: rgba(255,255,255,0.1);
        color: #ffffff;
        border: 1px solid rgba(255,255,255,0.2);
    }

    .modal-secondary:hover {
        background: rgba(255,255,255,0.15);
        border-color: rgba(255,255,255,0.4);
    }

    .reading-progress {
        position: fixed;
        top: 0;
        left: 0;
        width: 0%;
        height: 3px;
        background: linear-gradient(90deg, #22c55e, #16a34a);
        z-index: 999;
        transition: width 0.3s ease;
    }

    .copy-btn {
        position: absolute;
        top: 10px;
        right: 10px;
        background: rgba(255,255,255,0.1);
        color: #ffffff;
        border: 1px solid rgba(255,255,255,0.2);
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-size: 0.875rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .copy-btn:hover {
        background: rgba(255,255,255,0.2);
        border-color: rgba(255,255,255,0.4);
    }

    .global-error {
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(239, 68, 68, 0.9);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        z-index: 2000;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }

    .global-error button {
        background: none;
        border: none;
        color: white;
        text-decoration: underline;
        cursor: pointer;
        margin-left: 1rem;
    }

    @media (max-width: 768px) {
        .modal-actions {
            flex-direction: column;
        }
        
        .modal-cta,
        .modal-secondary {
            min-width: auto;
        }
    }
`;

// Inject dynamic styles
const styleSheet = document.createElement('style');
styleSheet.textContent = dynamicStyles;
document.head.appendChild(styleSheet);