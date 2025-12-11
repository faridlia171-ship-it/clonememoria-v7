'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { useRouter } from 'next/navigation';

export default function AccountPage() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [consents, setConsents] = useState({
    consent_data_processing: true,
    consent_voice_processing: false,
    consent_video_processing: false,
    consent_third_party_apis: false,
    consent_whatsapp_ingestion: false,
  });

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }

    setConsents({
      consent_data_processing: user.consent_data_processing ?? true,
      consent_voice_processing: user.consent_voice_processing ?? false,
      consent_video_processing: user.consent_video_processing ?? false,
      consent_third_party_apis: user.consent_third_party_apis ?? false,
      consent_whatsapp_ingestion: user.consent_whatsapp_ingestion ?? false,
    });
  }, [user, router]);

  const handleConsentChange = (key: string, value: boolean) => {
    setConsents(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveConsents = async () => {
    setLoading(true);
    setMessage(null);

    try {
      await apiClient.updateConsent(consents);
      setMessage({ type: 'success', text: 'Consent preferences updated successfully' });
      logger.info('Consents updated', { consents });
    } catch (error) {
      logger.error('Failed to update consents', { error });
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to update consents',
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
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `clonememoria-data-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setMessage({ type: 'success', text: 'Data exported successfully' });
      logger.info('User data exported');
    } catch (error) {
      logger.error('Failed to export data', { error });
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to export data',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteData = async () => {
    if (!confirm('Are you sure you want to delete all your data? This action cannot be undone.')) {
      return;
    }

    if (!confirm('This will permanently delete your account and all associated data. Are you absolutely sure?')) {
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      await apiClient.deleteUserData();
      setMessage({ type: 'success', text: 'Data deletion initiated. Logging out...' });
      logger.info('User data deleted');
      setTimeout(() => {
        logout();
        router.push('/');
      }, 2000);
    } catch (error) {
      logger.error('Failed to delete data', { error });
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to delete data',
      });
      setLoading(false);
    }
  };

  if (!user) {
    return null;
  }

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

        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Profile Information</h2>
          <div className="space-y-3">
            <div>
              <span className="text-sm text-gray-600">Email:</span>
              <p className="text-gray-900">{user.email}</p>
            </div>
            <div>
              <span className="text-sm text-gray-600">Name:</span>
              <p className="text-gray-900">{user.full_name || 'Not set'}</p>
            </div>
            <div>
              <span className="text-sm text-gray-600">Billing Plan:</span>
              <p className="text-gray-900 capitalize">{user.billing_plan || 'free'}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Privacy & Consent (GDPR)</h2>
          <p className="text-sm text-gray-600 mb-4">
            Manage your data processing preferences. These settings control how CloneMemoria processes your data.
          </p>

          <div className="space-y-4">
            <label className="flex items-start">
              <input
                type="checkbox"
                checked={consents.consent_data_processing}
                onChange={(e) => handleConsentChange('consent_data_processing', e.target.checked)}
                className="mt-1 mr-3 h-4 w-4 text-blue-600 rounded"
              />
              <div>
                <div className="font-medium text-gray-900">Data Processing</div>
                <div className="text-sm text-gray-600">
                  Allow CloneMemoria to process your data for core functionality (required for using the service)
                </div>
              </div>
            </label>

            <label className="flex items-start">
              <input
                type="checkbox"
                checked={consents.consent_voice_processing}
                onChange={(e) => handleConsentChange('consent_voice_processing', e.target.checked)}
                className="mt-1 mr-3 h-4 w-4 text-blue-600 rounded"
              />
              <div>
                <div className="font-medium text-gray-900">Voice Processing (TTS)</div>
                <div className="text-sm text-gray-600">
                  Allow text-to-speech audio generation for your clones
                </div>
              </div>
            </label>

            <label className="flex items-start">
              <input
                type="checkbox"
                checked={consents.consent_video_processing}
                onChange={(e) => handleConsentChange('consent_video_processing', e.target.checked)}
                className="mt-1 mr-3 h-4 w-4 text-blue-600 rounded"
              />
              <div>
                <div className="font-medium text-gray-900">Video Processing (Avatars)</div>
                <div className="text-sm text-gray-600">
                  Allow avatar video generation (future feature)
                </div>
              </div>
            </label>

            <label className="flex items-start">
              <input
                type="checkbox"
                checked={consents.consent_third_party_apis}
                onChange={(e) => handleConsentChange('consent_third_party_apis', e.target.checked)}
                className="mt-1 mr-3 h-4 w-4 text-blue-600 rounded"
              />
              <div>
                <div className="font-medium text-gray-900">Third-Party APIs</div>
                <div className="text-sm text-gray-600">
                  Allow use of external AI providers (OpenAI, ElevenLabs, etc.) instead of dummy providers
                </div>
              </div>
            </label>

            <label className="flex items-start">
              <input
                type="checkbox"
                checked={consents.consent_whatsapp_ingestion}
                onChange={(e) => handleConsentChange('consent_whatsapp_ingestion', e.target.checked)}
                className="mt-1 mr-3 h-4 w-4 text-blue-600 rounded"
              />
              <div>
                <div className="font-medium text-gray-900">WhatsApp Data Ingestion</div>
                <div className="text-sm text-gray-600">
                  Allow importing conversation data from WhatsApp (future feature)
                </div>
              </div>
            </label>
          </div>

          <button
            onClick={handleSaveConsents}
            disabled={loading}
            className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Saving...' : 'Save Consent Preferences'}
          </button>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Data Management</h2>
          <p className="text-sm text-gray-600 mb-4">
            Exercise your GDPR rights: export or delete your data.
          </p>

          <div className="space-y-4">
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Export Your Data</h3>
              <p className="text-sm text-gray-600 mb-3">
                Download a JSON file containing all your data including clones, memories, conversations, and documents.
              </p>
              <button
                onClick={handleExportData}
                disabled={loading}
                className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Exporting...' : 'Export Data'}
              </button>
            </div>

            <div className="pt-4 border-t border-gray-200">
              <h3 className="font-medium text-red-900 mb-2">Delete Your Data</h3>
              <p className="text-sm text-gray-600 mb-3">
                Permanently delete your account and all associated data. This action cannot be undone.
              </p>
              <button
                onClick={handleDeleteData}
                disabled={loading}
                className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Deleting...' : 'Delete All Data'}
              </button>
            </div>
          </div>
        </div>

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
