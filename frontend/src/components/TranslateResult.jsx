// src/components/TranslateResult.js
// Clean result display with feedback options

import React, { useState, useCallback } from 'react';
import { logger } from '../utils/logger';

// Method descriptions for user understanding
const METHOD_DESCRIPTIONS = {
  'exact': 'Direct match from database',
  'fuzzy': 'Smart typo correction',
  'pattern': 'Grammar pattern recognition',
  'compound': 'Word combination analysis',
  'ngram': 'Partial text matching',
  'word_by_word': 'Individual word translation',
  'adaptive_cache': 'Previous user feedback',
  'phonetic': 'Sound-based matching'
};

// Confidence level indicators
const getConfidenceLevel = (confidence) => {
  if (confidence >= 0.9) return { level: 'high', color: '#059669', label: 'High' };
  if (confidence >= 0.7) return { level: 'medium', color: '#d97706', label: 'Medium' };
  if (confidence >= 0.5) return { level: 'low', color: '#dc2626', label: 'Low' };
  return { level: 'very-low', color: '#6b7280', label: 'Very Low' };
};

export default function TranslateResult({ 
  result, 
  onFeedback,
  loading = false 
}) {
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const handleFeedback = useCallback(async (isCorrect) => {
    if (!result || !onFeedback) return;
    
    try {
      await onFeedback(
        result.input || result.query,
        'banglish_to_english', // Default direction
        result.output || result.translation,
        isCorrect
      );
      logger.info('User feedback submitted', { isCorrect, method: result?.method, input: result?.input || result?.query });
      setFeedbackGiven(true);
    } catch (error) {
      logger.error('Feedback error', { error: error?.message || String(error) });
    }
  }, [result, onFeedback]);

  const copyToClipboard = useCallback(async () => {
    if (!result?.output && !result?.translation) return;
    
    try {
      await navigator.clipboard.writeText(result.output || result.translation);
      // Could add toast notification here
      logger.info('Copied translation to clipboard');
    } catch (error) {
      logger.error('Copy failed', { error: error?.message || String(error) });
    }
  }, [result]);

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <div style={styles.spinner} />
          <span>Translating...</span>
        </div>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  // Handle error results
  if (!result.success) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>
          <strong>Translation Failed</strong>
          <p>{result.error || result.message || 'Unknown error occurred'}</p>
        </div>
      </div>
    );
  }

  const translation = result.output || result.translation;
  const confidence = result.confidence || 0;
  const method = result.method || 'unknown';
  const confidenceInfo = getConfidenceLevel(confidence);
  
  return (
    <div style={styles.container}>
      {/* Main Result */}
      <div style={styles.resultCard}>
        <div style={styles.resultHeader}>
          <h3 style={styles.resultTitle}>Translation Result</h3>
          {result.fromCache && (
            <span style={styles.cacheIndicator}>From Cache</span>
          )}
        </div>

        <div style={styles.translationText}>
          {translation}
        </div>

        {/* Action Buttons */}
        <div style={styles.actionButtons}>
          <button 
            onClick={copyToClipboard}
            style={styles.actionButton}
            title="Copy to clipboard"
          >
            📋 Copy
          </button>
          
          <button 
            onClick={() => setShowDetails(!showDetails)}
            style={styles.actionButton}
          >
            {showDetails ? '📄 Hide Details' : '📊 Show Details'}
          </button>
        </div>

        {/* Details Section */}
        {showDetails && (
          <div style={styles.details}>
            <div style={styles.detailRow}>
              <span style={styles.detailLabel}>Method:</span>
              <span style={styles.detailValue}>
                {METHOD_DESCRIPTIONS[method] || method}
              </span>
            </div>
            
            <div style={styles.detailRow}>
              <span style={styles.detailLabel}>Confidence:</span>
              <span style={{
                ...styles.detailValue,
                color: confidenceInfo.color,
                fontWeight: '500'
              }}>
                {Math.round(confidence * 100)}% ({confidenceInfo.label})
              </span>
            </div>
            
            {result.processingTime && (
              <div style={styles.detailRow}>
                <span style={styles.detailLabel}>Processing Time:</span>
                <span style={styles.detailValue}>
                  {result.processingTime}ms
                </span>
              </div>
            )}

            {result.timestamp && (
              <div style={styles.detailRow}>
                <span style={styles.detailLabel}>Timestamp:</span>
                <span style={styles.detailValue}>
                  {new Date(result.timestamp).toLocaleTimeString()}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Feedback Section */}
      {onFeedback && !feedbackGiven && (
        <div style={styles.feedbackCard}>
          <p style={styles.feedbackQuestion}>
            Was this translation helpful?
          </p>
          <div style={styles.feedbackButtons}>
            <button
              onClick={() => handleFeedback(true)}
              style={styles.thumbsUp}
              title="Good translation"
            >
              👍 Yes
            </button>
            <button
              onClick={() => handleFeedback(false)}
              style={styles.thumbsDown}
              title="Needs improvement"
            >
              👎 No
            </button>
          </div>
        </div>
      )}

      {/* Feedback Thanks */}
      {feedbackGiven && (
        <div style={styles.feedbackThanks}>
          ✅ Thank you for your feedback! This helps improve our translations.
        </div>
      )}
    </div>
  );
}

// Styles
const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    width: '100%',
    maxWidth: '600px'
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '24px',
    backgroundColor: '#f9fafb',
    borderRadius: '8px',
    fontSize: '16px',
    color: '#374151'
  },
  spinner: {
    width: '20px',
    height: '20px',
    border: '2px solid #e5e7eb',
    borderTop: '2px solid #2563eb',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  },
  error: {
    padding: '16px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    color: '#dc2626'
  },
  resultCard: {
    padding: '20px',
    backgroundColor: 'white',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
  },
  resultHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px'
  },
  resultTitle: {
    margin: 0,
    fontSize: '18px',
    color: '#111827'
  },
  cacheIndicator: {
    fontSize: '12px',
    color: '#059669',
    backgroundColor: '#d1fae5',
    padding: '4px 8px',
    borderRadius: '4px'
  },
  translationText: {
    fontSize: '20px',
    fontWeight: '500',
    color: '#111827',
    marginBottom: '16px',
    padding: '12px',
    backgroundColor: '#f9fafb',
    borderRadius: '6px',
    border: '1px solid #e5e7eb'
  },
  actionButtons: {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px'
  },
  actionButton: {
    padding: '6px 12px',
    backgroundColor: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  details: {
    backgroundColor: '#f9fafb',
    padding: '12px',
    borderRadius: '6px',
    border: '1px solid #e5e7eb'
  },
  detailRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px'
  },
  detailLabel: {
    fontSize: '14px',
    color: '#6b7280',
    fontWeight: '500'
  },
  detailValue: {
    fontSize: '14px',
    color: '#111827'
  },
  feedbackCard: {
    padding: '16px',
    backgroundColor: '#fffbeb',
    border: '1px solid #fed7aa',
    borderRadius: '8px'
  },
  feedbackQuestion: {
    margin: '0 0 12px 0',
    fontSize: '14px',
    color: '#92400e',
    fontWeight: '500'
  },
  feedbackButtons: {
    display: 'flex',
    gap: '8px'
  },
  thumbsUp: {
    padding: '8px 16px',
    backgroundColor: '#059669',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  thumbsDown: {
    padding: '8px 16px',
    backgroundColor: '#dc2626',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  feedbackThanks: {
    padding: '12px',
    backgroundColor: '#d1fae5',
    color: '#065f46',
    borderRadius: '6px',
    fontSize: '14px',
    textAlign: 'center'
  }
};