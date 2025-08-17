// src/components/TranslateInput.js
// Clean input component with validation

import React, { useState, useCallback } from 'react';

const DIRECTIONS = [
  { value: 'banglish_to_english', label: 'Banglish → English' },
  { value: 'english_to_banglish', label: 'English → Banglish' }
];

const PLACEHOLDER_TEXT = {
  'banglish_to_english': 'Enter Banglish text... (e.g., "kemon acho")',
  'english_to_banglish': 'Enter English text... (e.g., "how are you")'
};

export default function TranslateInput({ 
  onTranslate, 
  loading = false, 
  disabled = false 
}) {
  const [input, setInput] = useState('');
  const [direction, setDirection] = useState('banglish_to_english');

  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    
    if (!input.trim()) return;
    
    onTranslate(input.trim(), direction);
  }, [input, direction, onTranslate]);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }, [handleSubmit]);

  const clearInput = useCallback(() => {
    setInput('');
  }, []);

  const isValidInput = input.trim().length > 0 && input.length <= 500;

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      {/* Direction Selector */}
      <div style={styles.directionContainer}>
        <label style={styles.label}>Translation Direction:</label>
        <select
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          disabled={disabled}
          style={styles.select}
        >
          {DIRECTIONS.map(dir => (
            <option key={dir.value} value={dir.value}>
              {dir.label}
            </option>
          ))}
        </select>
      </div>

      {/* Text Input */}
      <div style={styles.inputContainer}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={PLACEHOLDER_TEXT[direction]}
          disabled={disabled}
          maxLength={500}
          rows={4}
          style={{
            ...styles.textarea,
            ...(disabled ? styles.disabled : {})
          }}
        />
        
        {/* Character Count */}
        <div style={styles.charCount}>
          <span style={input.length > 450 ? styles.charCountWarning : {}}>
            {input.length}/500
          </span>
          {input.length > 0 && (
            <button
              type="button"
              onClick={clearInput}
              disabled={disabled}
              style={styles.clearButton}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={!isValidInput || loading || disabled}
        style={{
          ...styles.submitButton,
          ...((!isValidInput || loading || disabled) ? styles.submitButtonDisabled : {})
        }}
      >
        {loading ? 'Translating...' : 'Translate'}
      </button>

      {/* Input Validation */}
      {input.length > 500 && (
        <div style={styles.error}>
          Text is too long (max 500 characters)
        </div>
      )}
    </form>
  );
}

// Styles
const styles = {
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    width: '100%',
    maxWidth: '600px'
  },
  directionContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap'
  },
  label: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#374151'
  },
  select: {
    padding: '8px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    backgroundColor: 'white',
    cursor: 'pointer'
  },
  inputContainer: {
    position: 'relative'
  },
  textarea: {
    width: '100%',
    padding: '12px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '16px',
    fontFamily: 'inherit',
    resize: 'vertical',
    minHeight: '100px',
    outline: 'none',
    transition: 'border-color 0.2s',
    boxSizing: 'border-box'
  },
  disabled: {
    backgroundColor: '#f9fafb',
    color: '#6b7280',
    cursor: 'not-allowed'
  },
  charCount: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '4px',
    fontSize: '12px',
    color: '#6b7280'
  },
  charCountWarning: {
    color: '#dc2626',
    fontWeight: '500'
  },
  clearButton: {
    background: 'none',
    border: 'none',
    color: '#6b7280',
    cursor: 'pointer',
    fontSize: '12px',
    textDecoration: 'underline'
  },
  submitButton: {
    padding: '12px 24px',
    backgroundColor: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  submitButtonDisabled: {
    backgroundColor: '#9ca3af',
    cursor: 'not-allowed'
  },
  error: {
    color: '#dc2626',
    fontSize: '14px',
    marginTop: '-8px'
  }
};