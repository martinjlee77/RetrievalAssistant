"""
Reusable Streamlit widgets for subscription management and display.
"""
import streamlit as st
import requests
import os
from typing import Dict, Any, Optional

BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:3000')


def get_subscription_usage(token: str) -> Optional[Dict[str, Any]]:
    """
    Fetch current subscription usage from backend API.
    Returns None if user is not logged in or API call fails.
    """
    if not token:
        return None
    
    try:
        response = requests.get(
            f"{BACKEND_API_URL}/api/subscription/usage",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to load subscription data: {response.status_code}")
            return None
            
    except requests.RequestException as e:
        st.warning(f"Unable to load subscription data. Please check your connection.")
        return None


def display_subscription_dashboard(token: str = None):
    """
    Display subscription dashboard with usage meter, plan info, and upgrade prompt.
    Should be called at the top of pages to show user their current subscription status.
    
    Args:
        token: User authentication token. If None, will check st.session_state.
    """
    # Get token from session state if not provided
    if token is None:
        token = st.session_state.get('auth_token')
    
    # Only show for logged-in users
    if not token:
        return
    
    usage_data = get_subscription_usage(token)
    
    if not usage_data:
        return
    
    # Extract data
    plan_name = usage_data.get('plan_name', 'Unknown Plan')
    total_available = usage_data.get('total_available', 0)
    total_used = usage_data.get('total_used', 0)
    base_allowance = usage_data.get('base_allowance', 0)
    rollover_available = usage_data.get('rollover_available', 0)
    status = usage_data.get('status', 'unknown')
    trial_days_remaining = usage_data.get('trial_days_remaining')
    
    # Calculate usage percentage
    usage_percent = (total_used / total_available * 100) if total_available > 0 else 0
    remaining_words = max(0, total_available - total_used)
    
    # Determine status color and message
    if status == 'trialing':
        status_emoji = "🎁"
        status_color = "#4CAF50"
        status_text = f"Trial ({trial_days_remaining} days left)"
    elif status == 'active':
        status_emoji = "✅"
        status_color = "#2196F3"
        status_text = "Active"
    elif status == 'past_due':
        status_emoji = "⚠️"
        status_color = "#FF9800"
        status_text = "Payment Required"
    elif status == 'cancelled':
        status_emoji = "❌"
        status_color = "#F44336"
        status_text = "Cancelled"
    else:
        status_emoji = "❓"
        status_color = "#9E9E9E"
        status_text = "Unknown"
    
    # Usage bar color based on percentage
    if usage_percent < 50:
        bar_color = "#4CAF50"  # Green
    elif usage_percent < 80:
        bar_color = "#FF9800"  # Orange
    else:
        bar_color = "#F44336"  # Red
    
    # Display subscription card
    st.html(f"""
    <style>
        .subscription-card {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2a5298 100%);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .subscription-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .plan-info {{
            color: white;
        }}
        .plan-name {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .plan-status {{
            font-size: 14px;
            color: {status_color};
            font-weight: 500;
        }}
        .usage-bar-container {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            height: 32px;
            position: relative;
            margin-bottom: 12px;
            overflow: hidden;
        }}
        .usage-bar {{
            background: {bar_color};
            height: 100%;
            width: {min(usage_percent, 100)}%;
            border-radius: 8px;
            transition: width 0.3s ease;
        }}
        .usage-text {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-weight: 600;
            font-size: 14px;
            z-index: 1;
        }}
        .usage-details {{
            display: flex;
            justify-content: space-between;
            color: rgba(255, 255, 255, 0.9);
            font-size: 13px;
            margin-top: 8px;
        }}
        .detail-item {{
            display: flex;
            flex-direction: column;
        }}
        .detail-label {{
            color: rgba(255, 255, 255, 0.6);
            font-size: 11px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .detail-value {{
            font-weight: 600;
        }}
    </style>
    
    <div class="subscription-card">
        <div class="subscription-header">
            <div class="plan-info">
                <div class="plan-name">{status_emoji} {plan_name}</div>
                <div class="plan-status">{status_text}</div>
            </div>
        </div>
        
        <div class="usage-bar-container">
            <div class="usage-bar"></div>
            <div class="usage-text">{remaining_words:,} words remaining ({usage_percent:.0f}% used)</div>
        </div>
        
        <div class="usage-details">
            <div class="detail-item">
                <span class="detail-label">Base Allowance</span>
                <span class="detail-value">{base_allowance:,} words</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Rollover</span>
                <span class="detail-value">{rollover_available:,} words</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Total Available</span>
                <span class="detail-value">{total_available:,} words</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Used This Month</span>
                <span class="detail-value">{total_used:,} words</span>
            </div>
        </div>
    </div>
    """)
    
    # Show upgrade prompt if usage is high (>80%) or trial is expiring soon
    show_upgrade = False
    upgrade_message = ""
    
    if status == 'trialing' and trial_days_remaining and trial_days_remaining <= 7:
        show_upgrade = True
        upgrade_message = f"⏰ Your trial expires in {trial_days_remaining} days. Upgrade now to keep your analyses running smoothly."
    elif usage_percent > 80:
        show_upgrade = True
        upgrade_message = f"⚠️ You've used {usage_percent:.0f}% of your word allowance. Upgrade for more capacity or wait until next month's reset."
    
    if show_upgrade:
        with st.container(border=True):
            st.warning(upgrade_message)
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("⬆️ Upgrade Plan", use_container_width=True, type="primary"):
                    show_upgrade_modal(token)


def show_upgrade_modal(token: str):
    """
    Display upgrade modal with available plans and pricing.
    Uses st.dialog for modal display.
    """
    
    @st.dialog("Upgrade Your Subscription", width="large")
    def upgrade_dialog():
        st.markdown("### Choose Your Plan")
        st.markdown("Select a plan that fits your team's needs. All plans include:")
        st.markdown("- All ASC standards (606, 340-40, 842, 718, 805)")
        st.markdown("- Unlimited analyses (subject to word limits)")
        st.markdown("- Priority support")
        st.markdown("- Monthly word allowance with 12-month rollover")
        
        st.divider()
        
        # Fetch available plans
        try:
            response = requests.get(
                f"{BACKEND_API_URL}/api/subscription/plans",
                timeout=5
            )
            
            if response.status_code != 200:
                st.error("Unable to load subscription plans. Please try again later.")
                return
            
            data = response.json()
            plans = data.get('plans', [])
            
            # Display plans in columns
            cols = st.columns(3)
            
            plan_order = ['professional', 'team', 'enterprise']
            
            for idx, plan_key in enumerate(plan_order):
                plan = next((p for p in plans if p['key'] == plan_key), None)
                if not plan:
                    continue
                
                with cols[idx]:
                    with st.container(border=True):
                        st.markdown(f"### {plan['name']}")
                        st.markdown(f"**${plan['price_monthly']}/month**")
                        st.markdown(f"{plan['word_allowance']:,} words/month")
                        st.markdown(plan['description'])
                        
                        if st.button(
                            f"Select {plan['name']}",
                            key=f"select_{plan_key}",
                            use_container_width=True,
                            type="primary" if idx == 1 else "secondary"
                        ):
                            initiate_upgrade(token, plan_key)
            
        except requests.RequestException as e:
            st.error(f"Unable to load subscription plans: {e}")
    
    # Show the dialog
    upgrade_dialog()


def initiate_upgrade(token: str, plan_key: str):
    """
    Initiate Stripe checkout for subscription upgrade.
    Redirects user to Stripe checkout session.
    """
    try:
        response = requests.post(
            f"{BACKEND_API_URL}/api/subscription/upgrade",
            headers={'Authorization': f'Bearer {token}'},
            json={'plan_key': plan_key},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            checkout_url = data.get('checkout_url')
            
            if checkout_url:
                st.success(f"Redirecting to Stripe checkout...")
                st.markdown(f"[Click here if not redirected automatically]({checkout_url})")
                
                # JavaScript redirect
                st.html(f"""
                <script>
                    window.location.href = "{checkout_url}";
                </script>
                """)
            else:
                st.error("Failed to create checkout session. Please contact support.")
        
        elif response.status_code == 503:
            data = response.json()
            st.error(data.get('message', 'Stripe integration not configured'))
        
        else:
            st.error(f"Upgrade failed: {response.json().get('error', 'Unknown error')}")
    
    except requests.RequestException as e:
        st.error(f"Unable to initiate upgrade: {e}")


def display_compact_usage_badge(token: str = None):
    """
    Display a compact subscription usage badge for display in sidebar or header.
    Shows remaining words and quick upgrade link.
    
    Args:
        token: User authentication token. If None, will check st.session_state.
    """
    # Get token from session state if not provided
    if token is None:
        token = st.session_state.get('auth_token')
    
    # Only show for logged-in users
    if not token:
        return
    
    usage_data = get_subscription_usage(token)
    
    if not usage_data:
        return
    
    total_available = usage_data.get('total_available', 0)
    total_used = usage_data.get('total_used', 0)
    remaining_words = max(0, total_available - total_used)
    
    usage_percent = (total_used / total_available * 100) if total_available > 0 else 0
    
    # Color based on usage
    if usage_percent < 50:
        color = "#4CAF50"
        icon = "✅"
    elif usage_percent < 80:
        color = "#FF9800"
        icon = "⚠️"
    else:
        color = "#F44336"
        icon = "🔴"
    
    st.html(f"""
    <style>
        .usage-badge {{
            background: rgba(255, 255, 255, 0.1);
            border-left: 4px solid {color};
            border-radius: 4px;
            padding: 8px 12px;
            margin-bottom: 16px;
        }}
        .badge-text {{
            color: white;
            font-size: 13px;
            margin: 0;
        }}
        .badge-value {{
            font-weight: 600;
            color: {color};
        }}
    </style>
    
    <div class="usage-badge">
        <p class="badge-text">{icon} <span class="badge-value">{remaining_words:,} words</span> remaining</p>
    </div>
    """)
