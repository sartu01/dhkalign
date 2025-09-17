// src/App.js
// Main WRAITH application - clean and focused

import React, { useState, useCallback } from 'react';
import { useTranslator } from './hooks/useTranslator';
import { useOffline } from './hooks/useOffline';
import TranslateInput from './components/TranslateInput';
import TranslateResult from './components/TranslateResult';
import { cleanupCache } from './utils/cache';

// Cleanup cache on app start
cleanupCache();

export default function App() {
  // Stripe success page: fetch and store API key
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get("session_id");
    const onSuccessPage = window.location.pathname.includes("success") && sessionId;
    if (!onSuccessPage) return;
    const stored = localStorage.getItem("dhk_api_key");
    if (stored) return;
    fetch(`https://dhkalign-edge-production.tnfy4np8pm.workers.dev/billing/key?session_id=${encodeURIComponent(sessionId)}`)
      .then(r => r.json())
      .then(j => {
        if (j.ok && j.data && j.data.api_key) {
          localStorage.setItem("dhk_api_key", j.data.api_key);
          // Optionally show a toast or alert here
        }
      });
  }, []);
  const { 
    translate, 
    provideFeedback, 
    loading, 
    error, 
    result, 
    clearError,
    clearCache,
    getStats
  } = useTranslator();
  
  const { isOnline, connectionType } = useOffline();
  const [showStats, setShowStats] = useState(false);
  const [currentStats, setCurrentStats] = useState(null);

  // Handle translation with direction support
  const handleTranslate = useCallback(async (input, direction) => {
    await translate(input, direction);
  }, [translate]);

  // Handle user feedback
  const handleFeedback = useCallback(async (query, direction, translation, isCorrect) => {
    return await provideFeedback(query, direction, translation, isCorrect);
  }, [provideFeedback]);

  // Show stats modal
  const handleShowStats = useCallback(() => {
    const stats = getStats();
    setCurrentStats(stats);
    setShowStats(true);
  }, [getStats]);

  // Clear all cache
  const handleClearCache = useCallback(() => {
    clearCache();
    // Update stats if showing
    if (showStats) {
      setCurrentStats(getStats());
    }
  }, [clearCache, getStats, showStats]);

  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <h1 style={styles.title}>DHK Align – WRAITH Translator</h1>
        <p style={styles.subtitle}>
          Advanced Banglish ↔ English Translation with AI Enhancement
        </p>
        
        {/* Status Indicators */}
        <div style={styles.statusBar}>
          <div style={{
            ...styles.statusItem,
            ...(isOnline ? styles.statusOnline : styles.statusOffline)
          }}>
            {isOnline ? '🟢' : '🔴'} {isOnline ? 'Online' : 'Offline'}
            {connectionType !== 'unknown' && isOnline && (
              <span style={styles.connectionType}>({connectionType})</span>
            )}
          </div>
          
          <button 
            onClick={handleShowStats}
            style={styles.statsButton}
            title="View statistics"
          >
            📊 Stats
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
        {/* Error Display */}
        {error && (
          <div style={styles.errorBanner}>
            <span style={styles.errorText}>{error}</span>
            <button 
              onClick={clearError}
              style={styles.errorClose}
              title="Dismiss error"
            >
              ✕
            </button>
          </div>
        )}

        {/* Offline Warning */}
        {!isOnline && (
          <div style={styles.offlineWarning}>
            ⚠️ You're offline. Translation may not work until connection is restored.
          </div>
        )}

        {/* Translation Interface */}
        <div style={styles.translationContainer}>
          <TranslateInput
            onTranslate={handleTranslate}
            loading={loading}
            disabled={!isOnline}
          />

          <TranslateResult
            result={result}
            onFeedback={handleFeedback}
            loading={loading}
          />
        </div>
      </main>

      {/* Stats Modal */}
      {showStats && currentStats && (
        <div style={styles.modalOverlay} onClick={() => setShowStats(false)}>
          <div style={styles.statsModal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.statsHeader}>
              <h3 style={styles.statsTitle}>Translation Statistics</h3>
              <button 
                onClick={() => setShowStats(false)}
                style={styles.modalClose}
              >
                ✕
              </button>
            </div>
            
            <div style={styles.statsContent}>
              {/* Request Stats */}
              <div style={styles.statSection}>
                <h4 style={styles.statSectionTitle}>Requests</h4>
                <div style={styles.statGrid}>
                  <div style={styles.statItem}>
                    <span style={styles.statLabel}>Total Requests:</span>
                    <span style={styles.statValue}>{currentStats.requests.totalRequests}</span>
                  </div>
                  <div style={styles.statItem}>
                    <span style={styles.statLabel}>Cache Hits:</span>
                    <span style={styles.statValue}>{currentStats.requests.cacheHits}</span>
                  </div>
                  <div style={styles.statItem}>
                    <span style={styles.statLabel}>Errors:</span>
                    <span style={styles.statValue}>{currentStats.requests.errors}</span>
                  </div>
                  <div style={styles.statItem}>
                    <span style={styles.statLabel}>Success Rate:</span>
                    <span style={styles.statValue}>{currentStats.successRate}%</span>
                  </div>
                </div>
              </div>

              {/* Cache Stats */}
              <div style={styles.statSection}>
                <h4 style={styles.statSectionTitle}>Cache</h4>
                <div style={styles.statGrid}>
                  <div style={styles.statItem}>
                    <span style={styles.statLabel}>Total Entries:</span>
                    <span style={styles.statValue}>{currentStats.cache.totalEntries}</span>
                  </div>
                  <div style={styles.statItem}>
                    <span style={styles.statLabel}>Valid Entries:</span>
                    <span style={styles.statValue}>{currentStats.cache.validEntries}</span>
                  </div>
                  <div style={styles.statItem}>
                    <span style={styles.statLabel}>Expired Entries:</span>
                    <span style={styles.statValue}>{currentStats.cache.expiredEntries}</span>
                  </div>
                </div>
                
                <button
                  onClick={handleClearCache}
                  style={styles.clearCacheButton}
                >
                  🗑️ Clear Cache
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer style={styles.footer}>
        <p style={styles.footerText}>
          Powered by WRAITH Translation Engine v2.0
        </p>
      </footer>
    </div>
  );
}

// Styles
const styles = {
  app: {
    minHeight: '100vh',
    backgroundColor: '#f9fafb',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    display: 'flex',
    flexDirection: 'column'
  },
  header: {
    backgroundColor: 'white',
    padding: '24px 20px',
    borderBottom: '1px solid #e5e7eb',
    textAlign: 'center'
  },
  title: {
    margin: '0 0 8px 0',
    fontSize: '28px',
    fontWeight: '700',
    color: '#111827'
  },
  subtitle: {
    margin: '0 0 16px 0',
    fontSize: '16px',
    color: '#6b7280'
  },
  statusBar: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '16px',
    flexWrap: 'wrap'
  },
  statusItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '14px',
    fontWeight: '500'
  },
  statusOnline: {
    color: '#059669'
  },
  statusOffline: {
    color: '#dc2626'
  },
  connectionType: {
    fontSize: '12px',
    color: '#6b7280',
    fontWeight: '400'
  },
  statsButton: {
    padding: '6px 12px',
    backgroundColor: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  main: {
    flex: 1,
    padding: '32px 20px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '24px'
  },
  errorBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    maxWidth: '600px',
    padding: '12px 16px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    color: '#dc2626'
  },
  errorText: {
    fontSize: '14px'
  },
  errorClose: {
    background: 'none',
    border: 'none',
    color: '#dc2626',
    cursor: 'pointer',
    fontSize: '16px',
    padding: '0 4px'
  },
  offlineWarning: {
    width: '100%',
    maxWidth: '600px',
    padding: '12px 16px',
    backgroundColor: '#fffbeb',
    border: '1px solid #fed7aa',
    borderRadius: '8px',
    color: '#92400e',
    fontSize: '14px',
    textAlign: 'center'
  },
  translationContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
    width: '100%',
    maxWidth: '600px'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px'
  },
  statsModal: {
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
    maxWidth: '500px',
    width: '100%',
    maxHeight: '80vh',
    overflow: 'auto'
  },
  statsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px 0 24px',
    borderBottom: '1px solid #e5e7eb'
  },
  statsTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: '600',
    color: '#111827'
  },
  modalClose: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    color: '#6b7280',
    cursor: 'pointer',
    padding: '4px'
  },
  statsContent: {
    padding: '24px'
  },
  statSection: {
    marginBottom: '24px'
  },
  statSectionTitle: {
    margin: '0 0 12px 0',
    fontSize: '16px',
    fontWeight: '600',
    color: '#374151'
  },
  statGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '8px'
  },
  statItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 0'
  },
  statLabel: {
    fontSize: '14px',
    color: '#6b7280'
  },
  statValue: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#111827'
  },
  clearCacheButton: {
    marginTop: '12px',
    padding: '8px 16px',
    backgroundColor: '#dc2626',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  footer: {
    backgroundColor: 'white',
    borderTop: '1px solid #e5e7eb',
    padding: '16px',
    textAlign: 'center'
  },
  footerText: {
    margin: 0,
    fontSize: '14px',
    color: '#6b7280'
  }
};