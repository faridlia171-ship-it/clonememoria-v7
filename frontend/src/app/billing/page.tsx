'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { useRouter } from 'next/navigation';

interface PlanDetails {
  name: string;
  price: number;
  messages_limit: number;
  clones_limit: number;
  documents_limit: number;
}

interface BillingPlan {
  current_plan: string;
  plan_details: PlanDetails;
  period_start: string | null;
  period_end: string | null;
  is_dummy_mode: boolean;
}

interface UsageStats {
  current_period: {
    clones: number;
    documents: number;
    messages: number;
  };
  today: {
    messages_count: number;
    tokens_used: number;
    tts_requests: number;
    avatar_requests: number;
  };
  timestamp: string;
}

export default function BillingPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [plan, setPlan] = useState<BillingPlan | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }

    fetchBillingData();
  }, [user, router]);

  const fetchBillingData = async () => {
    setLoading(true);
    try {
      const [planData, usageData] = await Promise.all([
        apiClient.getBillingPlan(),
        apiClient.getBillingUsage(),
      ]);
      setPlan(planData);
      setUsage(usageData);
      logger.info('Billing data fetched', { plan: planData.current_plan });
    } catch (error) {
      logger.error('Failed to fetch billing data', { error });
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to load billing data',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (targetPlan: string) => {
    setUpgrading(true);
    setMessage(null);

    try {
      const result = await apiClient.createCheckout(targetPlan);
      logger.info('Checkout initiated', { plan: targetPlan, result });

      if (result.checkout_url) {
        setMessage({
          type: 'success',
          text: `Redirecting to checkout... (Demo: ${result.message})`,
        });
      } else {
        setMessage({
          type: 'success',
          text: result.message || 'Upgrade initiated',
        });
      }
    } catch (error) {
      logger.error('Failed to upgrade', { error });
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to upgrade',
      });
    } finally {
      setUpgrading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading billing information...</div>
      </div>
    );
  }

  if (!plan || !usage) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-600">Failed to load billing data</div>
      </div>
    );
  }

  const calculateUsagePercentage = (used: number, limit: number) => {
    if (limit === -1) return 0;
    return Math.min((used / limit) * 100, 100);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Billing & Usage</h1>

        {message && (
          <div
            className={`mb-6 p-4 rounded-lg ${
              message.type === 'success'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            {message.text}
          </div>
        )}

        {plan.is_dummy_mode && (
          <div className="mb-6 p-4 bg-blue-50 text-blue-800 border border-blue-200 rounded-lg">
            <strong>Demo Mode:</strong> This is a dummy billing system for development. Real billing requires Stripe configuration.
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Current Plan</h2>
            <div className="mb-4">
              <div className="text-3xl font-bold text-blue-600 mb-1">
                {plan.plan_details.name}
              </div>
              <div className="text-2xl text-gray-900">
                ${plan.plan_details.price}
                <span className="text-sm text-gray-600">/month</span>
              </div>
            </div>

            <div className="space-y-2 text-sm text-gray-600">
              <div>
                <strong>Messages:</strong>{' '}
                {plan.plan_details.messages_limit === -1
                  ? 'Unlimited'
                  : `${plan.plan_details.messages_limit} per month`}
              </div>
              <div>
                <strong>Clones:</strong>{' '}
                {plan.plan_details.clones_limit === -1
                  ? 'Unlimited'
                  : plan.plan_details.clones_limit}
              </div>
              <div>
                <strong>Documents:</strong>{' '}
                {plan.plan_details.documents_limit === -1
                  ? 'Unlimited'
                  : plan.plan_details.documents_limit}
              </div>
            </div>

            {plan.current_plan === 'free' && (
              <button
                onClick={() => handleUpgrade('pro')}
                disabled={upgrading}
                className="mt-6 w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {upgrading ? 'Processing...' : 'Upgrade to Pro'}
              </button>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Usage This Period</h2>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Clones</span>
                  <span className="font-medium text-gray-900">
                    {usage.current_period.clones} /{' '}
                    {plan.plan_details.clones_limit === -1
                      ? '∞'
                      : plan.plan_details.clones_limit}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{
                      width: `${calculateUsagePercentage(
                        usage.current_period.clones,
                        plan.plan_details.clones_limit
                      )}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Messages</span>
                  <span className="font-medium text-gray-900">
                    {usage.current_period.messages} /{' '}
                    {plan.plan_details.messages_limit === -1
                      ? '∞'
                      : plan.plan_details.messages_limit}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all"
                    style={{
                      width: `${calculateUsagePercentage(
                        usage.current_period.messages,
                        plan.plan_details.messages_limit
                      )}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Documents</span>
                  <span className="font-medium text-gray-900">
                    {usage.current_period.documents} /{' '}
                    {plan.plan_details.documents_limit === -1
                      ? '∞'
                      : plan.plan_details.documents_limit}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full transition-all"
                    style={{
                      width: `${calculateUsagePercentage(
                        usage.current_period.documents,
                        plan.plan_details.documents_limit
                      )}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Today's Activity</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">
                {usage.today.messages_count}
              </div>
              <div className="text-sm text-gray-600">Messages</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">
                {usage.today.tokens_used}
              </div>
              <div className="text-sm text-gray-600">Tokens</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">
                {usage.today.tts_requests}
              </div>
              <div className="text-sm text-gray-600">TTS Requests</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">
                {usage.today.avatar_requests}
              </div>
              <div className="text-sm text-gray-600">Avatar Requests</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Available Plans</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Free</h3>
              <div className="text-3xl font-bold text-gray-900 mb-4">
                $0<span className="text-sm text-gray-600">/mo</span>
              </div>
              <ul className="space-y-2 text-sm text-gray-600 mb-6">
                <li>✓ 2 clones</li>
                <li>✓ 100 messages/month</li>
                <li>✓ 10 documents</li>
                <li>✓ Basic features</li>
              </ul>
              {plan.current_plan === 'free' && (
                <button disabled className="w-full px-4 py-2 bg-gray-300 text-gray-600 rounded-lg cursor-not-allowed">
                  Current Plan
                </button>
              )}
            </div>

            <div className="border-2 border-blue-600 rounded-lg p-6 relative">
              <div className="absolute top-0 right-0 bg-blue-600 text-white px-3 py-1 text-xs rounded-bl-lg rounded-tr-lg">
                Popular
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Pro</h3>
              <div className="text-3xl font-bold text-gray-900 mb-4">
                $29<span className="text-sm text-gray-600">/mo</span>
              </div>
              <ul className="space-y-2 text-sm text-gray-600 mb-6">
                <li>✓ 10 clones</li>
                <li>✓ 1,000 messages/month</li>
                <li>✓ 100 documents</li>
                <li>✓ Priority support</li>
              </ul>
              {plan.current_plan === 'pro' ? (
                <button disabled className="w-full px-4 py-2 bg-gray-300 text-gray-600 rounded-lg cursor-not-allowed">
                  Current Plan
                </button>
              ) : (
                <button
                  onClick={() => handleUpgrade('pro')}
                  disabled={upgrading}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {upgrading ? 'Processing...' : 'Upgrade'}
                </button>
              )}
            </div>

            <div className="border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Enterprise</h3>
              <div className="text-3xl font-bold text-gray-900 mb-4">
                $99<span className="text-sm text-gray-600">/mo</span>
              </div>
              <ul className="space-y-2 text-sm text-gray-600 mb-6">
                <li>✓ Unlimited clones</li>
                <li>✓ Unlimited messages</li>
                <li>✓ Unlimited documents</li>
                <li>✓ Dedicated support</li>
              </ul>
              {plan.current_plan === 'enterprise' ? (
                <button disabled className="w-full px-4 py-2 bg-gray-300 text-gray-600 rounded-lg cursor-not-allowed">
                  Current Plan
                </button>
              ) : (
                <button
                  onClick={() => handleUpgrade('enterprise')}
                  disabled={upgrading}
                  className="w-full px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
                >
                  {upgrading ? 'Processing...' : 'Upgrade'}
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={() => router.push('/dashboard')}
            className="text-blue-600 hover:text-blue-700"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
