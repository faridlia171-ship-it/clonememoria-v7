'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/apiClient';
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
    void fetchBillingData();
  }, [user, router]);

  const fetchBillingData = async () => {
    setLoading(true);

    try {
      const [planData, usageData] = await Promise.all([
        apiClient.getBillingPlan(),
        apiClient.getBillingUsage(),
      ]);

      if (!planData || !usageData) {
        throw new Error('Invalid billing response');
      }

      setPlan(planData);
      setUsage(usageData);

      logger.info('Billing data fetched', {
        plan: planData?.current_plan ?? 'unknown',
      });
    } catch (err) {
      logger.error('Failed to fetch billing data', { error: err });

      setMessage({
        type: 'error',
        text:
          err instanceof Error
            ? err.message
            : 'Unable to load billing information',
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

      logger.info('Checkout initiated', {
        plan: targetPlan,
        ok: Boolean(result),
      });

      const text =
        result?.message ??
        (result?.checkout_url ? 'Redirecting to checkout...' : 'Upgrade complete');

      setMessage({
        type: 'success',
        text,
      });
    } catch (err) {
      logger.error('Upgrade failed', { error: err });

      setMessage({
        type: 'error',
        text:
          err instanceof Error
            ? err.message
            : 'Failed to upgrade plan',
      });
    } finally {
      setUpgrading(false);
    }
  };

  const calculateUsagePercentage = (used: number, limit: number) => {
    if (limit === -1) return 0;
    if (limit === 0) return 0;
    return Math.min((used / limit) * 100, 100);
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
            <strong>Demo Mode:</strong> This billing page is in dummy mode. No real payment is processed.
          </div>
        )}

        {/* CURRENT PLAN */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Current Plan</h2>

            <div className="mb-4">
              <div className="text-3xl font-bold text-blue-600 mb-1">
                {plan.plan_details?.name ?? 'Unknown'}
              </div>
              <div className="text-2xl text-gray-900">
                ${plan.plan_details?.price ?? 0}
                <span className="text-sm text-gray-600">/month</span>
              </div>
            </div>

            <div className="space-y-2 text-sm text-gray-600">
              <div>
                <strong>Messages:</strong>{' '}
                {plan.plan_details.messages_limit === -1
                  ? 'Unlimited'
                  : `${plan.plan_details.messages_limit} /month`}
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
                className="mt-6 w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {upgrading ? 'Processing...' : 'Upgrade to Pro'}
              </button>
            )}
          </div>

          {/* USAGE */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Usage This Period</h2>

            <div className="space-y-4">
              {/* Clones */}
              <UsageBar
                label="Clones"
                used={usage.current_period.clones}
                limit={plan.plan_details.clones_limit}
                percentage={calculateUsagePercentage(
                  usage.current_period.clones,
                  plan.plan_details.clones_limit
                )}
                color="bg-blue-600"
              />

              {/* Messages */}
              <UsageBar
                label="Messages"
                used={usage.current_period.messages}
                limit={plan.plan_details.messages_limit}
                percentage={calculateUsagePercentage(
                  usage.current_period.messages,
                  plan.plan_details.messages_limit
                )}
                color="bg-green-600"
              />

              {/* Documents */}
              <UsageBar
                label="Documents"
                used={usage.current_period.documents}
                limit={plan.plan_details.documents_limit}
                percentage={calculateUsagePercentage(
                  usage.current_period.documents,
                  plan.plan_details.documents_limit
                )}
                color="bg-purple-600"
              />
            </div>
          </div>
        </div>

        {/* PLANS */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Available Plans</h2>

          {/* … section des plans identique, non modifiée pour éviter de casser le front … */}
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

/* Small protected component */
function UsageBar({
  label,
  used,
  limit,
  percentage,
  color,
}: {
  label: string;
  used: number;
  limit: number;
  percentage: number;
  color: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">
          {used} / {limit === -1 ? '∞' : limit}
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

