'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { useRouter } from 'next/navigation';

export default function AccountPage() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Prevent crash if user object is malformed
  const safeUser = user ?? {
    email: '',
    full_name: '',
    billing_plan: 'free',
  };

  const [consents, setConsents] = useState({
    consent_data_processing: true,
    consent_voice_processing: false,
    consent_video_processing: false,
    consent_third_party_apis: false,
    consent_whatsapp_ingestion: false,
  });

  // Protect page against undefined user + ensure SSR-safe navigation
  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }

    setConsents({
      consent_data_processing: Boolean(user.consent_data_processing ?? true),
      consent_voice_processing: Boolean(user.consent_voice_processing ?? false),
      consent_video_processing: Boolean(user.consent_video_processing ?? false),
      consent_third_party_apis: Boolean(user.consent_third_party_apis ?? false),
      consent_whatsapp_ingestion: Boolean(user.consent_whatsapp_ingestion ?? false),
    });
  }, [user, router]);

  const handleConsentChange = (key: keyof typeof consents, value: boolean) => {
    setConsents(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveConsents = async () => {
    setLoading(true);
    setMessage(null);

    try {
      await apiClient.updateConsent(consents);
      logger.info('Consent updated', consents);

      setMessage({
        type: 'success',
        text: 'Consent preferences updated successfully.',
      });

    } catch (error: any) {
      logger.error('Consent update failed', { error });

      setMessage({
        type: 'error',
        text: error?.message ?? 'Failed to update consent preferences.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleExportData = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const data = await apiClient.exportUserData();

      if (!data) throw new Error('No data returned');

      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = url;
      a.download = `clonememoria-data-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setMessage({ type: 'success', text: 'Data exported successfully.' });

    } catch (error: any) {
      logger.error('Data export failed', { error });

      setMessage({
        type: 'error',
        text: error?.message ?? 'Failed to export data.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteData = async () => {
    const confirmed1 = confirm('Are you sure you want to delete all your data?');
    if (!confirmed1) return;
    const confirmed2 = confirm('This action is irreversible. Proceed?');
    if (!confirmed2) return;

    setLoading(true);
    setMessage(null);

    try {
      await apiClient.deleteUserData();

      logger.info('User data deletion initiated');

      setMessage({
        type: 'success',
        text: 'Deletion initiated. Logging out...',
      });

      setTimeout(() => {
        logout();
        router.push('/');
      }, 1500);

    } catch (error: any) {
      logger.error('Data deletion failed', { error });

      setMessage({
        type: 'error',
        text: error?.message ?? 'Failed to delete your data.',
      });
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Account Settings</h1>

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

        {/* PROFILE SECTION */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Profile Information</h2>
          <div className="space-y-3">
            <div>
              <span className="text-sm text-gray-600">Email:</span>
              <p className="text-gray-900">{safeUser.email}</p>
            </div>

            <div>
              <span className="text-sm text-gray-600">Name:</span>
              <p className="text-gray-900">{safeUser.full_name || 'Not set'}</p>
            </div>

            <div>
              <span className="text-sm text-gray-600">Billing Plan:</span>
              <p className="text-gray-900 capitalize">{safeUser.billing_plan || 'free'}</p>
            </div>
          </div>
        </div>

        {/* CONSENT SECTION */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Privacy & Consent (GDPR)</h2>

          <div className="space-y-4">
            {Object.entries(consents).map(([key, value]) => (
              <label key={key} className="flex items-start">
                <input
                  type="checkbox"
                  checked={value}
                  onChange={(e) => handleConsentChange(key as any, e.target.checked)}
                  className="mt-1 mr-3 h-4 w-4 text-blue-600 rounded"
                />
                <div>
                  <div className="font-medium text-gray-900">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </div>
                  <div className="text-sm text-gray-600">
                    {/* Simplified descriptions */}
                    {key.includes('data') && 'Allow essential data processing'}
                    {key.includes('voice') && 'Allow voice/TTS processing'}
                    {key.includes('video') && 'Allow avatar/video generation'}
                    {key.includes('third_party') && 'Allow external AI APIs'}
                    {key.includes('whatsapp') && 'Allow WhatsApp data ingestion'}
                  </div>
                </div>
              </label>
            ))}
          </div>

          <button
            onClick={handleSaveConsents}
            disabled={loading}
            className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save Consent Preferences'}
          </button>
        </div>

        {/* DATA MANAGEMENT */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Data Management</h2>

          <div className="space-y-4">
            <button
              onClick={handleExportData}
              disabled={loading}
              className="px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              {loading ? 'Exporting...' : 'Export Data'}
            </button>

            <button
              onClick={handleDeleteData}
              disabled={loading}
              className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              {loading ? 'Deleting...' : 'Delete All Data'}
            </button>
          </div>
        </div>

        {/* BACK */}
        <div className="text-center">
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

